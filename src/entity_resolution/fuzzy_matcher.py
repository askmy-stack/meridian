"""Fuzzy matching for entity resolution fallback.

When NER confidence is low, use fuzzy string matching against known entities.
Uses rapidfuzz for performance (MIT license, faster than fuzzywuzzy).
"""

from typing import List, Optional, Tuple

import structlog
from rapidfuzz import fuzz, process

from ..graph import get_supplier_repository
from ..graph.models import Supplier

logger = structlog.get_logger(__name__)


class FuzzyEntityMatcher:
    """Fuzzy matcher for linking text mentions to graph entities.
    
    Usage:
        matcher = FuzzyEntityMatcher()
        supplier = matcher.match_supplier("Foxconn Zhengzhou")
        # Returns: Supplier with highest fuzzy score above threshold
    """
    
    DEFAULT_THRESHOLD = 70  # Minimum fuzzy score (0-100)
    
    def __init__(
        self,
        threshold: int = DEFAULT_THRESHOLD,
        limit: int = 5,
        cache_size: int = 10_000,
    ):
        """Initialize fuzzy matcher.

        Args:
            threshold: Minimum fuzzy match score (0-100)
            limit: Maximum number of candidates to return per match
            cache_size: Maximum number of suppliers to load into the in-memory
                cache. Override with FUZZY_MATCHER_CACHE_SIZE env var for very
                large deployments.
        """
        import os
        self.threshold = threshold
        self.limit = limit
        self.cache_size = int(os.getenv("FUZZY_MATCHER_CACHE_SIZE", str(cache_size)))
        self.logger = logger.bind(matcher="FuzzyEntityMatcher")
        
        # Cache for entity names
        self._supplier_cache: List[Tuple[str, str]] = []  # [(name, id), ...]
        self._cache_valid = False
    
    def _refresh_cache(self) -> None:
        """Refresh entity name cache from Neo4j."""
        repo = get_supplier_repository()
        
        # Get suppliers up to configured cache_size (paginate later if needed)
        suppliers = repo.get_all(limit=self.cache_size)
        
        self._supplier_cache = [
            (s.name, s.id) for s in suppliers
        ]
        self._cache_valid = True
        
        self.logger.info(
            "cache_refreshed",
            supplier_count=len(self._supplier_cache)
        )
    
    def match_supplier(
        self,
        text: str,
        threshold: Optional[int] = None
    ) -> Optional[Tuple[Supplier, float]]:
        """Find best matching supplier for text mention.
        
        Args:
            text: Text to match (e.g., "Foxconn's Zhengzhou plant")
            threshold: Override default threshold
            
        Returns:
            Tuple of (matched Supplier, score 0-100) or None if no match
        """
        if not self._cache_valid:
            self._refresh_cache()
        
        if not self._supplier_cache:
            return None
        
        threshold = threshold or self.threshold
        
        # Use rapidfuzz for fast matching
        # Scorer: token_set_ratio handles word order differences well
        results = process.extract(
            text,
            [name for name, _ in self._supplier_cache],
            scorer=fuzz.token_set_ratio,
            limit=self.limit
        )
        
        if not results:
            return None
        
        # Get best match above threshold
        best_match, score, _ = results[0]
        
        if score < threshold:
            self.logger.debug(
                "fuzzy_match_below_threshold",
                text=text,
                best_match=best_match,
                score=score,
                threshold=threshold
            )
            return None
        
        # Find supplier by name
        repo = get_supplier_repository()
        suppliers = repo.get_by_name(best_match, fuzzy=False)
        
        if not suppliers:
            return None
        
        self.logger.info(
            "fuzzy_match_found",
            text=text,
            matched=best_match,
            score=score,
            supplier_id=suppliers[0].id
        )
        
        return (suppliers[0], score)
    
    def match_multiple(
        self,
        text: str,
        threshold: Optional[int] = None
    ) -> List[Tuple[Supplier, float]]:
        """Find all matching suppliers above threshold.
        
        Args:
            text: Text to match
            threshold: Override default threshold
            
        Returns:
            List of (Supplier, score) tuples
        """
        if not self._cache_valid:
            self._refresh_cache()
        
        if not self._supplier_cache:
            return []
        
        threshold = threshold or self.threshold
        
        results = process.extract(
            text,
            [name for name, _ in self._supplier_cache],
            scorer=fuzz.token_set_ratio,
            limit=self.limit
        )
        
        matches = []
        repo = get_supplier_repository()
        
        for match_name, score, _ in results:
            if score < threshold:
                continue
            
            suppliers = repo.get_by_name(match_name, fuzzy=False)
            for supplier in suppliers:
                matches.append((supplier, score))
        
        return matches
    
    def invalidate_cache(self) -> None:
        """Invalidate cache (call after bulk imports)."""
        self._cache_valid = False
        self.logger.info("cache_invalidated")


class SimpleNERExtractor:
    """Simple rule-based entity extractor (fallback until spaCy model is ready).
    
    Extracts potential entity mentions from text using patterns.
    Not as accurate as spaCy but zero dependencies.
    """
    
    # Keywords that suggest supplier entities
    SUPPLY_CHAIN_KEYWORDS = [
        "supplier", "manufacturer", "factory", "plant", "facility",
        "vendor", "contractor", "subcontractor", "producer",
        "assembly", "foundry", "mill", "refinery", "mill",
        "logistics", "warehouse", "distribution center"
    ]
    
    # Port-related keywords
    PORT_KEYWORDS = [
        "port", "harbor", "terminal", "dock", "marina",
        "anchorage", "quay", "pier", "jetty", "wharf"
    ]
    
    # Chokepoint names (major ones)
    CHOKEPOINT_NAMES = [
        "suez canal", "panama canal", "strait of hormuz",
        "bab el mandeb", "strait of malacca", "turkish straits",
        "dover strait", "kiel canal", "corinth canal",
        "cape of good hope", "cape horn", "northwest passage"
    ]
    
    def __init__(self):
        self.logger = logger.bind(extractor="SimpleNERExtractor")
    
    def extract_supplier_mentions(self, text: str) -> List[str]:
        """Extract potential supplier mentions from text.
        
        Args:
            text: News article or event description
            
        Returns:
            List of extracted mentions
        """
        mentions = []
        text_lower = text.lower()
        
        # Pattern 1: Company name followed by supply chain keyword
        # e.g., "Foxconn's Zhengzhou factory"
        for keyword in self.SUPPLY_CHAIN_KEYWORDS:
            if keyword in text_lower:
                # Extract surrounding context (simplistic)
                idx = text_lower.find(keyword)
                start = max(0, idx - 50)
                end = min(len(text), idx + len(keyword) + 50)
                context = text[start:end]
                mentions.append(context.strip())
        
        # Pattern 2: Possessive patterns
        # e.g., "TSMC's", "Samsung's"
        import re
        possessive_pattern = r'([A-Z][a-zA-Z\s]+)(?:\'s|\s+factory|\s+plant)'
        matches = re.findall(possessive_pattern, text)
        mentions.extend(matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for m in mentions:
            key = m.lower()
            if key not in seen:
                seen.add(key)
                unique.append(m)
        
        return unique
    
    def extract_port_mentions(self, text: str) -> List[str]:
        """Extract port mentions from text."""
        mentions = []
        text_lower = text.lower()
        
        for keyword in self.PORT_KEYWORDS:
            if keyword in text_lower:
                mentions.append(keyword)
        
        return mentions
    
    def extract_chokepoint_mentions(self, text: str) -> List[str]:
        """Extract chokepoint mentions from text."""
        mentions = []
        text_lower = text.lower()
        
        for chokepoint in self.CHOKEPOINT_NAMES:
            if chokepoint in text_lower:
                mentions.append(chokepoint)
        
        return mentions


# Singleton instances
_matcher: Optional[FuzzyEntityMatcher] = None
_extractor: Optional[SimpleNERExtractor] = None


def get_fuzzy_matcher() -> FuzzyEntityMatcher:
    """Get or create singleton FuzzyEntityMatcher."""
    global _matcher
    if _matcher is None:
        _matcher = FuzzyEntityMatcher()
    return _matcher


def get_ner_extractor() -> SimpleNERExtractor:
    """Get or create singleton SimpleNERExtractor."""
    global _extractor
    if _extractor is None:
        _extractor = SimpleNERExtractor()
    return _extractor
