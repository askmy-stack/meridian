"""Intelligence Engine module for Meridian.

Provides ML-powered analysis:
- Event Classification (BERT)
- Risk Scoring (XGBoost + SHAP)
- Named Entity Recognition (spaCy)
- Weak Signal Detection (Isolation Forest + LSTM)
"""

from .classifier import (
    BERTEventClassifier,
    ClassificationResult,
    RuleBasedClassifier,
    classify_event,
    get_classifier,
)
from .ner_pipeline import (
    Entity,
    EntityLinker,
    NERResult,
    SpacyNERPipeline,
    extract_entities,
    get_ner_pipeline,
    get_entity_linker,
)
from .risk_scorer import (
    FeatureVector,
    RiskScore,
    SimpleRiskScorer,
    XGBoostRiskScorer,
    get_risk_scorer,
    score_supplier,
)
from .service import (
    IntelligenceResult,
    IntelligenceService,
    analyze_event,
    get_intelligence_service,
    get_supplier_risk,
)
from .weak_signal_detector import (
    IsolationForestAnomalyDetector,
    LSTMTrendForecaster,
    TrendForecast,
    WeakSignal,
    WeakSignalDetector,
    get_weak_signal_detector,
)

__all__ = [
    # Classifier
    "BERTEventClassifier",
    "ClassificationResult",
    "RuleBasedClassifier",
    "classify_event",
    "get_classifier",
    
    # NER
    "Entity",
    "EntityLinker",
    "NERResult",
    "SpacyNERPipeline",
    "extract_entities",
    "get_ner_pipeline",
    "get_entity_linker",
    
    # Risk Scorer
    "FeatureVector",
    "RiskScore",
    "SimpleRiskScorer",
    "XGBoostRiskScorer",
    "get_risk_scorer",
    "score_supplier",
    
    # Weak Signals
    "IsolationForestAnomalyDetector",
    "LSTMTrendForecaster",
    "TrendForecast",
    "WeakSignal",
    "WeakSignalDetector",
    "get_weak_signal_detector",
    
    # Service
    "IntelligenceResult",
    "IntelligenceService",
    "analyze_event",
    "get_intelligence_service",
    "get_supplier_risk",
]
