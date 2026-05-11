"""Entity resolution module for Meridian.

Extracts and links supply chain entities from news/conflict events.
"""

from .fuzzy_matcher import (
    FuzzyEntityMatcher,
    SimpleNERExtractor,
    get_fuzzy_matcher,
    get_ner_extractor,
)

__all__ = [
    "FuzzyEntityMatcher",
    "SimpleNERExtractor",
    "get_fuzzy_matcher",
    "get_ner_extractor",
]
