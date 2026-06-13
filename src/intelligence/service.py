"""Intelligence Service for Meridian.

Unified service that orchestrates all ML components:
- Event classification (BERT)
- Risk scoring (XGBoost + SHAP)
- Entity extraction (spaCy NER)
- Weak signal detection (Isolation Forest + LSTM)

Provides single API for the intelligence engine layer.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

import structlog

from .classifier import (
    BERTEventClassifier,
    ClassificationResult,
    get_classifier,
)
from .ner_pipeline import (
    NERResult,
    extract_entities,
    get_ner_pipeline,
)
from .risk_scorer import (
    FeatureVector,
    RiskScore,
    XGBoostRiskScorer,
    get_risk_scorer,
)
from .weak_signal_detector import (
    TrendForecast,
    WeakSignal,
    get_weak_signal_detector,
)

logger = structlog.get_logger(__name__)


@dataclass
class IntelligenceResult:
    """Complete intelligence analysis result."""
    
    # Input
    event_id: Optional[str]
    text: str
    entity_id: Optional[str]
    
    # Classification
    event_category: str
    classification_confidence: float
    
    # Risk scoring
    risk_score: float
    risk_category: str
    risk_explanations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Entities
    extracted_entities: List[Dict[str, Any]] = field(default_factory=list)
    
    # Weak signals
    weak_signals: List[Dict[str, Any]] = field(default_factory=list)
    trend_forecast: Optional[Dict[str, Any]] = None
    
    # Metadata
    processing_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    model_versions: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "text": self.text,
            "entity_id": self.entity_id,
            "event_category": self.event_category,
            "classification_confidence": self.classification_confidence,
            "risk_score": self.risk_score,
            "risk_category": self.risk_category,
            "risk_explanations": self.risk_explanations,
            "extracted_entities": self.extracted_entities,
            "weak_signals": self.weak_signals,
            "trend_forecast": self.trend_forecast,
            "processing_timestamp": self.processing_timestamp,
            "model_versions": self.model_versions
        }


class IntelligenceService:
    """Unified intelligence service.
    
    Orchestrates all ML components for end-to-end analysis:
    1. Classify event type and severity
    2. Extract entities (suppliers, ports, chokepoints)
    3. Score risk for affected entities
    4. Detect weak signals and forecast trends
    
    Usage:
        service = IntelligenceService()
        
        result = service.analyze_event(
            text="Protests at Foxconn factory in Zhengzhou",
            event_id="gdelt_12345"
        )
        
        print(f"Risk: {result.risk_category}")
        print(f"Top factors: {result.risk_explanations}")
    """
    
    def __init__(
        self,
        use_classifier: bool = True,
        use_ner: bool = True,
        use_risk_scorer: bool = True,
        use_weak_signals: bool = True
    ):
        """Initialize intelligence service.
        
        Args:
            use_classifier: Enable BERT classification
            use_ner: Enable NER extraction
            use_risk_scorer: Enable XGBoost risk scoring
            use_weak_signals: Enable weak signal detection
        """
        self.use_classifier = use_classifier
        self.use_ner = use_ner
        self.use_risk_scorer = use_risk_scorer
        self.use_weak_signals = use_weak_signals
        
        self.logger = logger.bind(service="IntelligenceService")
        
        # Component instances
        self._classifier: Optional[BERTEventClassifier] = None
        self._risk_scorer: Optional[XGBoostRiskScorer] = None
        self._weak_detector = None
        
        self._init_components()
    
    def _init_components(self) -> None:
        """Initialize ML components."""
        if self.use_classifier:
            try:
                self._classifier = get_classifier()
                self.logger.info("classifier_initialized")
            except Exception as e:
                self.logger.error("classifier_init_failed", error=str(e))
                self.use_classifier = False
        
        if self.use_risk_scorer:
            try:
                self._risk_scorer = get_risk_scorer()
                self.logger.info("risk_scorer_initialized")
            except Exception as e:
                self.logger.error("risk_scorer_init_failed", error=str(e))
                self.use_risk_scorer = False
        
        if self.use_weak_signals:
            try:
                self._weak_detector = get_weak_signal_detector()
                self.logger.info("weak_signal_detector_initialized")
            except Exception as e:
                self.logger.error("weak_detector_init_failed", error=str(e))
                self.use_weak_signals = False
    
    def analyze_event(
        self,
        text: str,
        event_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        location: Optional[str] = None
    ) -> IntelligenceResult:
        """Analyze a single event comprehensively.
        
        Args:
            text: Event description or news text
            event_id: Optional event identifier
            entity_id: Optional entity to score (if known)
            entity_type: Type of entity (supplier, port, etc.)
            location: Geographic location
            
        Returns:
            IntelligenceResult with complete analysis
        """
        self.logger.info(
            "analyzing_event",
            event_id=event_id,
            text_len=len(text)
        )
        
        # Step 1: Classify event
        classification = self._classify(text)
        
        # Step 2: Extract entities
        ner_result = self._extract_entities(text)
        
        # Step 3: Score risk
        risk_result = self._score_risk(
            entity_id=entity_id,
            entity_type=entity_type,
            classification=classification,
            location=location
        )
        
        # Step 4: Detect weak signals (if historical data available)
        weak_signals = []
        forecast = None
        
        if entity_id and self.use_weak_signals:
            # Get historical data from graph (simplified for now)
            weak_signals, forecast = self._check_weak_signals(
                entity_id,
                entity_type or "supplier"
            )
        
        # Compile result
        model_versions = {}
        if self._classifier:
            model_versions["classifier"] = "bert-1.0"
        if self._risk_scorer:
            model_versions["risk_scorer"] = "xgb-1.0.0"
        
        result = IntelligenceResult(
            event_id=event_id,
            text=text,
            entity_id=entity_id,
            event_category=classification.label if classification else "UNKNOWN",
            classification_confidence=classification.confidence if classification else 0.0,
            risk_score=risk_result.risk_score if risk_result else 0.0,
            risk_category=risk_result.risk_category if risk_result else "MEDIUM",
            risk_explanations=risk_result.top_factors if risk_result else [],
            extracted_entities=[
                {
                    "text": e.text,
                    "label": e.label,
                    "confidence": e.confidence,
                    "linked_id": e.linked_entity_id
                }
                for e in (ner_result.entities if ner_result else [])
            ],
            weak_signals=[s.to_dict() for s in weak_signals],
            trend_forecast=forecast.to_dict() if forecast else None,
            model_versions=model_versions
        )
        
        self.logger.info(
            "event_analysis_complete",
            event_id=event_id,
            risk_category=result.risk_category,
            entities_found=len(result.extracted_entities)
        )
        
        return result
    
    def _classify(self, text: str) -> Optional[ClassificationResult]:
        """Classify event text."""
        if not self.use_classifier or not self._classifier:
            return None
        
        try:
            return self._classifier.classify(text)
        except Exception as e:
            self.logger.error("classification_failed", error=str(e))
            return None
    
    def _extract_entities(self, text: str) -> Optional[NERResult]:
        """Extract entities from text."""
        if not self.use_ner:
            return None
        
        try:
            return extract_entities(text, link_to_graph=True)
        except Exception as e:
            self.logger.error("ner_failed", error=str(e))
            return None
    
    def _score_risk(
        self,
        entity_id: Optional[str],
        entity_type: Optional[str],
        classification: Optional[ClassificationResult],
        location: Optional[str]
    ) -> Optional[RiskScore]:
        """Score risk for entity."""
        if not self.use_risk_scorer or not self._risk_scorer:
            return None
        
        if not entity_id or not entity_type:
            # Can't score without entity
            return None
        
        try:
            # Build feature vector from classification and context
            features = self._build_features(classification, location)
            
            return self._risk_scorer.score(entity_id, entity_type, features)
            
        except Exception as e:
            self.logger.error("risk_scoring_failed", error=str(e))
            return None
    
    def _build_features(
        self,
        classification: Optional[ClassificationResult],
        location: Optional[str]
    ) -> FeatureVector:
        """Build feature vector from event data."""
        features = FeatureVector()
        
        if classification:
            # Map classification to features
            label_scores = {
                "NONE": 0.0,
                "LOW": 0.25,
                "MEDIUM": 0.5,
                "HIGH": 0.75,
                "CRITICAL": 1.0
            }
            
            event_severity = label_scores.get(classification.label, 0.5)
            
            # Adjust features based on classification
            if classification.label in ["CRITICAL", "HIGH"]:
                features.critical_events_count = 1
                features.conflict_proximity_score = 0.7
            
            features.political_stability_index = 1.0 - event_severity
        
        # Location-based adjustments would go here
        # e.g., check if location is near conflict zone
        
        return features
    
    def _check_weak_signals(
        self,
        entity_id: str,
        entity_type: str
    ) -> Tuple[List[WeakSignal], Optional[TrendForecast]]:
        """Check for weak signals and forecast trends."""
        if not self.use_weak_signals or not self._weak_detector:
            return [], None
        
        try:
            # Get historical data from graph/database
            # For now, use synthetic/mock data
            # In production, query Neo4j for historical event counts and scores
            
            if entity_type == "supplier":
                # Query graph for supplier history
                from ..graph import get_neo4j_client
                
                client = get_neo4j_client()
                
                # Get recent events affecting this supplier
                query = """
                MATCH (e:Event)-[:AFFECTS]->(s:Supplier {id: $supplier_id})
                WHERE e.resolved_at > datetime() - duration('P30D')
                RETURN count(e) as event_count
                """
                
                try:
                    result = client.execute_query(query, {"supplier_id": entity_id})
                    recent_events = result[0]["event_count"] if result else 0
                    
                    # Create synthetic time series based on actual events
                    daily_counts = [0] * 21 + [recent_events // 7] * 7
                    risk_scores = [0.2 + (recent_events * 0.05)] * 14
                    
                    return self._weak_detector.monitor_supplier(
                        entity_id,
                        daily_counts,
                        risk_scores
                    )
                    
                except Exception:
                    # Fallback to empty
                    return [], None
            
            return [], None
            
        except Exception as e:
            self.logger.error("weak_signal_check_failed", error=str(e))
            return [], None
    
    def batch_analyze(
        self,
        events: List[Dict[str, Any]]
    ) -> List[IntelligenceResult]:
        """Analyze multiple events in batch.
        
        Args:
            events: List of event dicts with text, event_id, etc.
            
        Returns:
            List of IntelligenceResults
        """
        results = []
        
        for event in events:
            try:
                result = self.analyze_event(
                    text=event["text"],
                    event_id=event.get("event_id"),
                    entity_id=event.get("entity_id"),
                    entity_type=event.get("entity_type"),
                    location=event.get("location")
                )
                results.append(result)
            except Exception as e:
                self.logger.error(
                    "batch_analysis_failed",
                    event_id=event.get("event_id"),
                    error=str(e)
                )
        
        return results
    
    def get_supplier_risk_summary(self, supplier_id: str) -> Dict[str, Any]:
        """Get comprehensive risk summary for a supplier.
        
        Args:
            supplier_id: Supplier entity ID
            
        Returns:
            Risk summary with scores, signals, and forecast
        """
        # Get supplier from graph
        from ..graph import get_supplier_repository
        
        repo = get_supplier_repository()
        supplier = repo.get_by_id(supplier_id)
        
        if not supplier:
            return {"error": "Supplier not found"}
        
        # Score current risk
        from ..graph import get_neo4j_client
        from .feature_builder import build_supplier_features

        client = get_neo4j_client()
        features = build_supplier_features(
            supplier_id,
            single_source_flag=supplier.single_source_flag or False,
            critical_flag=getattr(supplier, "critical_flag", False) or False,
            country_iso=supplier.country_iso,
            neo4j_client=client,
        )
        
        risk = None
        if self._risk_scorer:
            risk = self._risk_scorer.score(supplier_id, "supplier", features)
        
        # Check weak signals
        weak_signals = []
        forecast = None
        
        if self._weak_detector:
            # Get historical data
            from ..graph import get_neo4j_client
            client = get_neo4j_client()
            
            query = """
            MATCH (e:Event)-[:AFFECTS]->(s:Supplier {id: $supplier_id})
            WHERE e.resolved_at > datetime() - duration('P30D')
            RETURN count(e) as events
            """
            
            try:
                result = client.execute_query(query, {"supplier_id": supplier_id})
                recent_events = result[0]["events"] if result else 0
                
                # Build time series
                daily_counts = [0] * 21 + [max(1, recent_events // 7)] * 7
                risk_scores = [0.3] * 14
                
                weak_signals, forecast = self._weak_detector.monitor_supplier(
                    supplier_id,
                    daily_counts,
                    risk_scores
                )
            except Exception as e:
                self.logger.error("risk_summary_failed", error=str(e))
        
        return {
            "supplier": {
                "id": supplier.id,
                "name": supplier.name,
                "country": supplier.country_iso
            },
            "current_risk": risk.to_dict() if risk else None,
            "weak_signals": [s.to_dict() for s in weak_signals],
            "trend_forecast": forecast.to_dict() if forecast else None,
            "model_versions": {
                "classifier": "bert-1.0",
                "risk_scorer": "xgb-1.0.0"
            }
        }
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of all ML components.
        
        Returns:
            Dict of component -> health status
        """
        return {
            "classifier": self._classifier is not None,
            "risk_scorer": self._risk_scorer is not None,
            "ner_pipeline": True,  # Always available (has fallback)
            "weak_signals": self._weak_detector is not None
        }


# Singleton instance
_service: Optional[IntelligenceService] = None


def get_intelligence_service() -> IntelligenceService:
    """Get or create singleton intelligence service."""
    global _service
    if _service is None:
        _service = IntelligenceService()
    return _service


def analyze_event(
    text: str,
    event_id: Optional[str] = None
) -> IntelligenceResult:
    """Convenience function for event analysis."""
    service = get_intelligence_service()
    return service.analyze_event(text, event_id)


def get_supplier_risk(supplier_id: str) -> Dict[str, Any]:
    """Convenience function for supplier risk summary."""
    service = get_intelligence_service()
    return service.get_supplier_risk_summary(supplier_id)
