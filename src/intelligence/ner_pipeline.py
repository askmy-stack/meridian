"""spaCy NER Pipeline for Meridian.

Extracts supply chain entities from news text:
- SUPPLIER: Companies, manufacturers, factories
- PORT: Shipping ports, harbors, terminals
- CHOKEPOINT: Shipping chokepoints (Suez, Panama, etc.)
- LOCATION: Countries, regions, cities
- EVENT: Conflict events, protests, disasters

Uses spaCy transformer or large model for accuracy.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import structlog

logger = structlog.get_logger(__name__)

# Try to import spaCy, handle gracefully
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spacy_not_available", message="NER pipeline using fallback")


@dataclass
class Entity:
    """Named entity extracted from text."""
    text: str
    label: str  # SUPPLIER, PORT, CHOKEPOINT, LOCATION, EVENT
    start: int  # Character offset
    end: int
    confidence: float = 1.0
    
    # Optional: normalized/canonical form
    canonical: Optional[str] = None
    
    # Optional: linked entity ID from graph
    linked_entity_id: Optional[str] = None
    
    # Optional: fuzzy match score
    match_score: Optional[float] = None


@dataclass
class NERResult:
    """Result from NER extraction."""
    text: str
    entities: List[Entity] = field(default_factory=list)
    
    def get_by_label(self, label: str) -> List[Entity]:
        """Get all entities of a specific label."""
        return [e for e in self.entities if e.label == label]
    
    def get_suppliers(self) -> List[Entity]:
        """Get supplier entities."""
        return self.get_by_label("SUPPLIER")
    
    def get_ports(self) -> List[Entity]:
        """Get port entities."""
        return self.get_by_label("PORT")
    
    def get_chokepoints(self) -> List[Entity]:
        """Get chokepoint entities."""
        return self.get_by_label("CHOKEPOINT")


class SpacyNERPipeline:
    """spaCy-based Named Entity Recognition pipeline.
    
    Extracts supply chain entities from news text.
    Uses en_core_web_trf or en_core_web_lg model.
    
    Usage:
        ner = SpacyNERPipeline()
        result = ner.extract("Foxconn factory in Shanghai closed due to protests")
        
        for entity in result.entities:
            print(f"{entity.text}: {entity.label}")
    """
    
    # Default model to use
    DEFAULT_MODEL = "en_core_web_lg"  # Can use "en_core_web_trf" for better accuracy
    
    # Entity type mappings from spaCy to our schema
    SPACY_TO_CUSTOM = {
        "ORG": "SUPPLIER",      # Organizations -> Suppliers
        "GPE": "LOCATION",      # Geopolitical entities
        "LOC": "LOCATION",       # Locations
        "FAC": "PORT",          # Facilities (potential ports)
    }
    
    # Known supply chain keywords to enhance detection
    SUPPLIER_INDICATORS = [
        "supplier", "manufacturer", "factory", "plant", "facility",
        "vendor", "contractor", "subcontractor", "producer",
        "foundry", "mill", "refinery", "assembler"
    ]
    
    PORT_INDICATORS = [
        "port", "harbor", "terminal", "dock", "marina",
        "anchorage", "quay", "pier", "jetty", "wharf", "seaport"
    ]
    
    # Default chokepoint names (15). Override at runtime by passing
    # chokepoint_names= to the constructor or by setting MERIDIAN_CHOKEPOINTS_FILE
    # to a path containing one chokepoint name per line.
    CHOKEPOINT_NAMES = [
        "suez canal", "panama canal", "strait of hormuz",
        "bab el mandeb", "strait of malacca", "turkish straits",
        "dover strait", "kiel canal", "corinth canal",
        "cape of good hope", "cape horn", "northwest passage",
        "taiwan strait", "korea strait", "english channel",
    ]

    @classmethod
    def _load_chokepoints_from_env(cls) -> Optional[List[str]]:
        """Optionally load chokepoints from a newline-delimited file."""
        import os
        path = os.getenv("MERIDIAN_CHOKEPOINTS_FILE")
        if not path:
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return [
                    line.strip().lower()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]
        except OSError:
            return None
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        use_gpu: bool = False,
        chokepoint_names: Optional[List[str]] = None,
    ):
        """Initialize NER pipeline.

        Args:
            model_name: spaCy model name (None = default)
            use_gpu: Use GPU for inference
            chokepoint_names: Override chokepoint vocabulary. If None,
                checks MERIDIAN_CHOKEPOINTS_FILE then falls back to class default.
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.use_gpu = use_gpu and SPACY_AVAILABLE

        # Resolve chokepoint vocabulary (instance-level so callers can override)
        if chokepoint_names is not None:
            self.chokepoint_names = [c.lower() for c in chokepoint_names]
        else:
            from_env = self._load_chokepoints_from_env()
            self.chokepoint_names = from_env if from_env else list(self.CHOKEPOINT_NAMES)

        self.logger = logger.bind(
            ner="SpacyNERPipeline",
            model=self.model_name,
            chokepoint_count=len(self.chokepoint_names),
        )

        self._nlp = None
        self._load_model()
    
    def _load_model(self) -> None:
        """Load spaCy model."""
        if not SPACY_AVAILABLE:
            self.logger.error("spacy_not_installed")
            return
        
        try:
            # Try to load the specified model
            self._nlp = spacy.load(self.model_name)
            self.logger.info("spacy_model_loaded", model=self.model_name)
            
        except OSError:
            # Model not downloaded, try smaller fallback
            self.logger.warning(
                "model_not_found",
                model=self.model_name,
                fallback="en_core_web_sm"
            )
            try:
                self._nlp = spacy.load("en_core_web_sm")
                self.model_name = "en_core_web_sm"
            except OSError:
                self.logger.error("no_spacy_model_available")
                self._nlp = None
    
    def extract(self, text: str) -> NERResult:
        """Extract entities from text.
        
        Args:
            text: Input text (news article, event description)
            
        Returns:
            NERResult with extracted entities
        """
        if not self._nlp or not text:
            # Fallback to rule-based extraction
            return self._rule_based_extract(text)
        
        # Process with spaCy
        doc = self._nlp(text)
        
        entities = []
        seen_spans = set()  # Track to avoid duplicates
        
        # Extract spaCy entities
        for ent in doc.ents:
            # Map spaCy label to our label
            custom_label = self.SPACY_TO_CUSTOM.get(ent.label_, None)
            
            if custom_label:
                # Refine ORG -> SUPPLIER based on context
                if custom_label == "SUPPLIER":
                    custom_label = self._refine_supplier_label(ent.text, text)
                
                entity = Entity(
                    text=ent.text,
                    label=custom_label,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=0.8
                )
                
                entities.append(entity)
                seen_spans.add((ent.start_char, ent.end_char))
        
        # Add rule-based chokepoint detection (more accurate than spaCy for these)
        chokepoints = self._extract_chokepoints(text)
        for cp in chokepoints:
            if (cp.start, cp.end) not in seen_spans:
                entities.append(cp)
        
        # Enhance with port detection
        ports = self._extract_ports(text)
        for port in ports:
            # Check if not already covered by spaCy
            overlap = False
            for e in entities:
                if not (port.end <= e.start or port.start >= e.end):
                    overlap = True
                    break
            if not overlap:
                entities.append(port)
        
        # Sort by position
        entities.sort(key=lambda e: e.start)
        
        return NERResult(text=text, entities=entities)
    
    def extract_batch(self, texts: List[str]) -> List[NERResult]:
        """Extract entities from multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of NERResults
        """
        if not self._nlp:
            return [self._rule_based_extract(t) for t in texts]
        
        results = []
        for doc in self._nlp.pipe(texts, batch_size=20):
            entities = []
            for ent in doc.ents:
                custom_label = self.SPACY_TO_CUSTOM.get(ent.label_)
                if custom_label:
                    entities.append(Entity(
                        text=ent.text,
                        label=custom_label,
                        start=ent.start_char,
                        end=ent.end_char,
                        confidence=0.8
                    ))
            
            # Add rule-based entities
            text = doc.text
            chokepoints = self._extract_chokepoints(text)
            entities.extend(chokepoints)
            
            results.append(NERResult(text=text, entities=entities))
        
        return results
    
    def _refine_supplier_label(self, text: str, context: str) -> str:
        """Determine if ORG is a SUPPLIER or something else."""
        text_lower = text.lower()
        context_lower = context.lower()
        
        # Check for supply chain indicators in context
        for indicator in self.SUPPLIER_INDICATORS:
            if indicator in context_lower:
                # Check proximity (within 50 chars)
                org_idx = context_lower.find(text_lower)
                ind_idx = context_lower.find(indicator)
                
                if org_idx >= 0 and ind_idx >= 0:
                    if abs(org_idx - ind_idx) < 100:
                        return "SUPPLIER"
        
        return "SUPPLIER"  # Default for ORG in supply chain context
    
    def _extract_chokepoints(self, text: str) -> List[Entity]:
        """Extract chokepoint mentions using pattern matching."""
        entities = []
        text_lower = text.lower()  # noqa: F841 — kept for downstream patterning

        for chokepoint in self.chokepoint_names:
            pattern = re.compile(r'\b' + re.escape(chokepoint) + r'\b', re.IGNORECASE)
            
            for match in pattern.finditer(text):
                entity = Entity(
                    text=match.group(),
                    label="CHOKEPOINT",
                    start=match.start(),
                    end=match.end(),
                    confidence=0.95,
                    canonical=chokepoint
                )
                entities.append(entity)
        
        return entities
    
    def _extract_ports(self, text: str) -> List[Entity]:
        """Extract port mentions using pattern matching."""
        entities = []
        text_lower = text.lower()
        
        # Pattern: [Name] + Port/Terminal/Harbor
        # e.g., "Port of Shanghai", "Shanghai Port", "Shanghai Terminal"
        
        patterns = [
            r'Port of ([A-Z][a-zA-Z\s]+?)(?:\s|,|\.|;|$)',
            r'([A-Z][a-zA-Z\s]+?)(?:\s)(?:Port|Harbor|Terminal|Marina)',
            r'([A-Z][a-zA-Z\s]+?)(?:\s)(?:seaport|shipping terminal)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                port_name = match.group(1).strip()
                entity = Entity(
                    text=match.group(),
                    label="PORT",
                    start=match.start(),
                    end=match.end(),
                    confidence=0.7
                )
                entities.append(entity)
        
        # Also check for port indicators
        for indicator in self.PORT_INDICATORS:
            for match in re.finditer(r'\b' + indicator + r'\b', text, re.IGNORECASE):
                # Check if context suggests this is a port
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end]
                
                if re.search(r'[A-Z][a-z]+', context):  # Has a proper noun nearby
                    entity = Entity(
                        text=match.group(),
                        label="PORT",
                        start=match.start(),
                        end=match.end(),
                        confidence=0.6
                    )
                    entities.append(entity)
        
        return entities
    
    def _rule_based_extract(self, text: str) -> NERResult:
        """Fallback rule-based extraction when spaCy unavailable."""
        entities = []
        
        # Extract chokepoints
        chokepoints = self._extract_chokepoints(text)
        entities.extend(chokepoints)
        
        # Extract ports
        ports = self._extract_ports(text)
        entities.extend(ports)
        
        # Simple supplier extraction: proper nouns near supply chain words
        text_lower = text.lower()
        for indicator in self.SUPPLIER_INDICATORS:
            idx = text_lower.find(indicator)
            if idx >= 0:
                # Get context window
                start = max(0, idx - 100)
                end = min(len(text), idx + 100)
                context = text[start:end]
                
                # Look for company names (simplistic: capitalized words)
                for match in re.finditer(r'[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*', context):
                    entity = Entity(
                        text=match.group(),
                        label="SUPPLIER",
                        start=start + match.start(),
                        end=start + match.end(),
                        confidence=0.5
                    )
                    entities.append(entity)
        
        # Remove overlapping entities
        entities = self._remove_overlapping(entities)
        
        return NERResult(text=text, entities=entities)
    
    def _remove_overlapping(self, entities: List[Entity]) -> List[Entity]:
        """Remove overlapping entity spans, keeping highest confidence."""
        if not entities:
            return entities
        
        # Sort by confidence descending
        sorted_entities = sorted(entities, key=lambda e: e.confidence, reverse=True)
        
        kept = []
        used_spans: Set[Tuple[int, int]] = set()
        
        for entity in sorted_entities:
            span = (entity.start, entity.end)
            
            # Check for overlap with kept entities
            overlap = False
            for used_start, used_end in used_spans:
                if not (entity.end <= used_start or entity.start >= used_end):
                    overlap = True
                    break
            
            if not overlap:
                kept.append(entity)
                used_spans.add(span)
        
        # Sort back by position
        kept.sort(key=lambda e: e.start)
        
        return kept


class EntityLinker:
    """Links extracted NER entities to graph entities."""
    
    def __init__(self):
        self.logger = logger.bind(linker="EntityLinker")
    
    def link_to_suppliers(
        self,
        entities: List[Entity],
        fuzzy_threshold: float = 70.0
    ) -> List[Entity]:
        """Link supplier entities to graph suppliers using fuzzy matching.
        
        Args:
            entities: NER-extracted entities
            fuzzy_threshold: Minimum fuzzy match score
            
        Returns:
            Entities with linked_entity_id populated
        """
        from ..entity_resolution import get_fuzzy_matcher
        
        matcher = get_fuzzy_matcher()
        linked = []
        
        for entity in entities:
            if entity.label != "SUPPLIER":
                linked.append(entity)
                continue
            
            # Try fuzzy match
            match = matcher.match_supplier(
                entity.text,
                threshold=int(fuzzy_threshold)
            )
            
            if match:
                supplier, score = match
                entity.linked_entity_id = supplier.id
                entity.match_score = score
                entity.canonical = supplier.name
            
            linked.append(entity)
        
        return linked


# Singleton instances
_ner_pipeline: Optional[SpacyNERPipeline] = None
_entity_linker: Optional[EntityLinker] = None


def get_ner_pipeline() -> SpacyNERPipeline:
    """Get or create singleton NER pipeline."""
    global _ner_pipeline
    if _ner_pipeline is None:
        _ner_pipeline = SpacyNERPipeline()
    return _ner_pipeline


def get_entity_linker() -> EntityLinker:
    """Get or create singleton entity linker."""
    global _entity_linker
    if _entity_linker is None:
        _entity_linker = EntityLinker()
    return _entity_linker


def extract_entities(text: str, link_to_graph: bool = True) -> NERResult:
    """Convenience function for end-to-end entity extraction.
    
    Args:
        text: Input text
        link_to_graph: Link entities to graph nodes
        
    Returns:
        NERResult with extracted and optionally linked entities
    """
    # Extract
    ner = get_ner_pipeline()
    result = ner.extract(text)
    
    # Link
    if link_to_graph:
        linker = get_entity_linker()
        result.entities = linker.link_to_suppliers(result.entities)
    
    return result
