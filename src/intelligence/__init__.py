"""Intelligence Engine module for Meridian.

Heavy optional deps (torch, transformers, xgboost, spacy) are lazy-loaded so API
routes and feature_builder work without the full ML stack installed.
"""

from __future__ import annotations

from typing import Any, Tuple

_LAZY: dict[str, Tuple[str, str]] = {
    "FeatureVector": (".feature_vector", "FeatureVector"),
    "RiskScore": (".risk_scorer", "RiskScore"),
    "SimpleRiskScorer": (".risk_scorer", "SimpleRiskScorer"),
    "XGBoostRiskScorer": (".risk_scorer", "XGBoostRiskScorer"),
    "get_risk_scorer": (".risk_scorer", "get_risk_scorer"),
    "score_supplier": (".risk_scorer", "score_supplier"),
    "BERTEventClassifier": (".classifier", "BERTEventClassifier"),
    "ClassificationResult": (".classifier", "ClassificationResult"),
    "RuleBasedClassifier": (".classifier", "RuleBasedClassifier"),
    "classify_event": (".classifier", "classify_event"),
    "get_classifier": (".classifier", "get_classifier"),
    "Entity": (".ner_pipeline", "Entity"),
    "EntityLinker": (".ner_pipeline", "EntityLinker"),
    "NERResult": (".ner_pipeline", "NERResult"),
    "SpacyNERPipeline": (".ner_pipeline", "SpacyNERPipeline"),
    "extract_entities": (".ner_pipeline", "extract_entities"),
    "get_ner_pipeline": (".ner_pipeline", "get_ner_pipeline"),
    "get_entity_linker": (".ner_pipeline", "get_entity_linker"),
    "IsolationForestAnomalyDetector": (".weak_signal_detector", "IsolationForestAnomalyDetector"),
    "LSTMTrendForecaster": (".weak_signal_detector", "LSTMTrendForecaster"),
    "TrendForecast": (".weak_signal_detector", "TrendForecast"),
    "WeakSignal": (".weak_signal_detector", "WeakSignal"),
    "WeakSignalDetector": (".weak_signal_detector", "WeakSignalDetector"),
    "get_weak_signal_detector": (".weak_signal_detector", "get_weak_signal_detector"),
    "IntelligenceResult": (".service", "IntelligenceResult"),
    "IntelligenceService": (".service", "IntelligenceService"),
    "analyze_event": (".service", "analyze_event"),
    "get_intelligence_service": (".service", "get_intelligence_service"),
    "get_supplier_risk": (".service", "get_supplier_risk"),
}

__all__ = list(_LAZY.keys())


def __getattr__(name: str) -> Any:
    if name not in _LAZY:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, attr = _LAZY[name]
    import importlib

    mod = importlib.import_module(module_path, __name__)
    return getattr(mod, attr)
