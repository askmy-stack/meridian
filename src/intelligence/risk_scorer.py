"""XGBoost Risk Scorer with SHAP Explanations for Meridian.

Scores suppliers, routes, and chokepoints for supply chain risk.
Uses XGBoost for prediction and SHAP for explainability.

Risk Factors:
- Geographic: Conflict proximity, political stability
- Operational: Port congestion, weather events
- Financial: Supplier stability, market indicators
- Network: Dependency depth, single-source flags
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import structlog
import xgboost as xgb

from .feature_vector import FeatureVector

logger = structlog.get_logger(__name__)

# Try to import SHAP, handle gracefully if not available
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("shap_not_available", message="SHAP explanations disabled")


@dataclass
class RiskScore:
    """Risk score result with SHAP explanations."""
    entity_id: str
    entity_type: str  # "supplier", "port", "chokepoint", "route"
    risk_score: float  # 0-1
    risk_category: str  # "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    
    # Feature contributions (SHAP values)
    feature_contributions: Dict[str, float] = field(default_factory=dict)
    
    # Top contributing factors
    top_factors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Model metadata
    model_version: str = "1.0.0"
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "risk_score": round(self.risk_score, 4),
            "risk_category": self.risk_category,
            "feature_contributions": {
                k: round(v, 4) for k, v in self.feature_contributions.items()
            },
            "top_factors": self.top_factors,
            "model_version": self.model_version,
            "confidence": round(self.confidence, 4)
        }


class XGBoostRiskScorer:
    """XGBoost-based risk scorer with SHAP explainability.
    
    Usage:
        scorer = XGBoostRiskScorer()
        
        features = FeatureVector(
            conflict_proximity_score=0.8,
            single_source_flag=True,
            critical_events_count=3
        )
        
        risk = scorer.score("supplier-123", "supplier", features)
        print(risk.risk_score)  # 0.75
        print(risk.top_factors)  # SHAP explanations
    """
    
    FEATURE_NAMES = [
        "conflict_proximity_score",
        "political_stability_index",
        "port_congestion_score",
        "weather_risk_score",
        "recent_events_count_normalized",
        "critical_events_count_normalized",
        "dependency_depth_normalized",
        "single_source_flag",
        "alternative_sources_count_normalized",
        "supplier_financial_health",
        "market_volatility_index",
        "historical_disruption_count_normalized",
        "avg_resolution_time_days_normalized",
    ]
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        use_shap: bool = True
    ):
        """Initialize risk scorer.
        
        Args:
            model_path: Path to saved XGBoost model (None = train new)
            use_shap: Enable SHAP explanations
        """
        self.model_path = model_path
        self.use_shap = use_shap and SHAP_AVAILABLE
        self.model_source: str = "synthetic_default"
        
        self.logger = logger.bind(
            scorer="XGBoostRiskScorer",
            use_shap=self.use_shap
        )
        
        self._model: Optional[xgb.XGBClassifier] = None
        self._explainer = None
        
        self._load_or_train_model()
    
    def _load_or_train_model(self) -> None:
        """Load existing model or train a new one."""
        mlflow_uri = os.getenv("MLFLOW_MODEL_URI")
        if mlflow_uri:
            try:
                import mlflow.xgboost

                self._model = mlflow.xgboost.load_model(mlflow_uri)
                self.model_source = "mlflow"
                self.model_path = mlflow_uri
                self.logger.info("model_loaded", source="mlflow", uri=mlflow_uri)
            except Exception as e:
                self.logger.error("mlflow_model_load_failed", error=str(e))
                self._train_default_model()
        elif self.model_path and os.path.exists(self.model_path):
            try:
                self._model = xgb.XGBClassifier()
                self._model.load_model(self.model_path)
                self.model_source = "file"
                self.logger.info("model_loaded", path=self.model_path, source="file")
            except Exception as e:
                self.logger.error("model_load_failed", error=str(e))
                self._train_default_model()
        else:
            self._train_default_model()
        
        # Initialize SHAP explainer
        if self.use_shap and self._model:
            try:
                self._explainer = shap.TreeExplainer(self._model)
                self.logger.info("shap_explainer_initialized")
            except Exception as e:
                self.logger.error("shap_init_failed", error=str(e))
                self.use_shap = False
    
    def _train_default_model(self) -> None:
        """Train a default model with synthetic data."""
        self.model_source = "synthetic_default"
        self.logger.warning(
            "training_default_model",
            message="Using synthetic labels — SCRI is demo-calibrated only",
        )
        
        # Generate synthetic training data
        np.random.seed(42)
        n_samples = 1000
        
        X = np.random.random((n_samples, len(self.FEATURE_NAMES)))
        
        # Create target based on feature interactions
        # Higher risk when: conflict near + single source + many critical events
        y = (
            (X[:, 0] > 0.7) & (X[:, 7] > 0.5)  # conflict + single source
        ).astype(int) | (
            (X[:, 5] > 0.6)  # many critical events
        ).astype(int) | (
            (X[:, 11] > 0.8)  # many historical disruptions
        ).astype(int)
        
        # Add some noise
        y = y | (np.random.random(n_samples) < 0.1).astype(int)
        
        # Train model
        self._model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            objective='binary:logistic',
            eval_metric='logloss',
            use_label_encoder=False
        )
        
        self._model.fit(X, y)
        self.logger.info("default_model_trained", samples=n_samples)
    
    def score(
        self,
        entity_id: str,
        entity_type: str,
        features: FeatureVector
    ) -> RiskScore:
        """Calculate risk score for an entity.
        
        Args:
            entity_id: Unique identifier
            entity_type: "supplier", "port", "chokepoint", "route"
            features: Feature vector
            
        Returns:
            RiskScore with SHAP explanations
        """
        if self._model is None:
            raise RuntimeError("Model not initialized")
        
        # Convert features to array
        X = features.to_array().reshape(1, -1)
        
        # Predict risk probability
        risk_prob = float(self._model.predict_proba(X)[0, 1])
        
        # Map to category
        risk_category = self._score_to_category(risk_prob)
        
        # Calculate SHAP values
        feature_contributions = {}
        top_factors = []
        
        if self.use_shap and self._explainer:
            try:
                shap_values = self._explainer.shap_values(X)
                
                # Get contributions for this prediction
                if isinstance(shap_values, list):
                    # Binary classification returns list
                    shap_vals = shap_values[1][0]  # Class 1 (risk) SHAP values
                else:
                    shap_vals = shap_values[0]
                
                # Create feature contribution dict
                feature_contributions = {
                    name: float(val)
                    for name, val in zip(self.FEATURE_NAMES, shap_vals)
                }
                
                # Get top contributing factors
                sorted_contribs = sorted(
                    feature_contributions.items(),
                    key=lambda x: abs(x[1]),
                    reverse=True
                )
                
                top_factors = [
                    {
                        "feature": name,
                        "contribution": round(val, 4),
                        "direction": "increases" if val > 0 else "decreases",
                        "description": self._feature_description(name)
                    }
                    for name, val in sorted_contribs[:5]
                ]
                
            except Exception as e:
                self.logger.error("shap_calculation_failed", error=str(e))
        
        # Calculate confidence based on prediction certainty
        confidence = abs(risk_prob - 0.5) * 2  # 0.5 -> 0, 0/1 -> 1
        
        return RiskScore(
            entity_id=entity_id,
            entity_type=entity_type,
            risk_score=risk_prob,
            risk_category=risk_category,
            feature_contributions=feature_contributions,
            top_factors=top_factors,
            model_version="xgb-1.0.0",
            confidence=confidence
        )
    
    def batch_score(
        self,
        entities: List[Tuple[str, str, FeatureVector]]
    ) -> List[RiskScore]:
        """Score multiple entities efficiently.
        
        Args:
            entities: List of (entity_id, entity_type, features)
            
        Returns:
            List of RiskScores
        """
        results = []
        
        for entity_id, entity_type, features in entities:
            try:
                score = self.score(entity_id, entity_type, features)
                results.append(score)
            except Exception as e:
                self.logger.error(
                    "scoring_failed",
                    entity_id=entity_id,
                    error=str(e)
                )
        
        return results
    
    def _score_to_category(self, score: float) -> str:
        """Map numeric score to risk category."""
        if score < 0.2:
            return "NONE"
        elif score < 0.4:
            return "LOW"
        elif score < 0.6:
            return "MEDIUM"
        elif score < 0.8:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def _feature_description(self, feature_name: str) -> str:
        """Get human-readable description of a feature."""
        descriptions = {
            "conflict_proximity_score": "Distance to active conflict zones",
            "political_stability_index": "Country political stability",
            "port_congestion_score": "Port congestion level",
            "weather_risk_score": "Extreme weather probability",
            "recent_events_count_normalized": "Number of recent risk events",
            "critical_events_count_normalized": "Number of critical/high severity events",
            "dependency_depth_normalized": "Supply chain tier depth",
            "single_source_flag": "Single source supplier flag",
            "alternative_sources_count_normalized": "Number of alternative suppliers",
            "supplier_financial_health": "Supplier financial stability",
            "market_volatility_index": "Market volatility",
            "historical_disruption_count_normalized": "Historical disruption frequency",
            "avg_resolution_time_days_normalized": "Average disruption resolution time",
        }
        return descriptions.get(feature_name, feature_name)
    
    def save_model(self, path: str) -> None:
        """Save trained model to disk."""
        if self._model is None:
            raise RuntimeError("No model to save")
        
        self._model.save_model(path)
        self.logger.info("model_saved", path=path)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get global feature importance from model."""
        if self._model is None:
            return {}
        
        importance = self._model.feature_importances_
        return {
            name: float(imp)
            for name, imp in zip(self.FEATURE_NAMES, importance)
        }


class SimpleRiskScorer:
    """Simple rule-based risk scorer (fallback)."""
    
    def score(
        self,
        entity_id: str,
        entity_type: str,
        features: FeatureVector
    ) -> RiskScore:
        """Calculate simple risk score without ML."""
        # Simple weighted sum
        weights = {
            "conflict_proximity_score": 0.25,
            "single_source_flag": 0.20,
            "critical_events_count": 0.20,
            "historical_disruption_count": 0.15,
            "port_congestion_score": 0.10,
            "weather_risk_score": 0.10,
        }
        
        score = (
            weights["conflict_proximity_score"] * features.conflict_proximity_score +
            weights["single_source_flag"] * float(features.single_source_flag) +
            weights["critical_events_count"] * min(features.critical_events_count / 5, 1.0) +
            weights["historical_disruption_count"] * min(features.historical_disruption_count / 5, 1.0) +
            weights["port_congestion_score"] * features.port_congestion_score +
            weights["weather_risk_score"] * features.weather_risk_score
        )
        
        # Clamp to 0-1
        score = min(1.0, max(0.0, score))
        
        # Determine category
        if score < 0.2:
            category = "NONE"
        elif score < 0.4:
            category = "LOW"
        elif score < 0.6:
            category = "MEDIUM"
        elif score < 0.8:
            category = "HIGH"
        else:
            category = "CRITICAL"
        
        # Create simple explanations
        top_factors = []
        if features.conflict_proximity_score > 0.5:
            top_factors.append({
                "feature": "conflict_proximity",
                "contribution": 0.25,
                "direction": "increases",
                "description": "Near active conflict zone"
            })
        if features.single_source_flag:
            top_factors.append({
                "feature": "single_source",
                "contribution": 0.20,
                "direction": "increases",
                "description": "No alternative suppliers"
            })
        
        return RiskScore(
            entity_id=entity_id,
            entity_type=entity_type,
            risk_score=score,
            risk_category=category,
            feature_contributions=weights,
            top_factors=top_factors,
            model_version="rule-based-1.0",
            confidence=0.6
        )


# Singleton instance
_scorer: Optional[XGBoostRiskScorer] = None


def get_risk_scorer() -> XGBoostRiskScorer:
    """Get or create singleton risk scorer."""
    global _scorer
    if _scorer is None:
        model_path = os.getenv("RISK_MODEL_PATH")
        if not model_path:
            default = Path(__file__).resolve().parents[2] / "models" / "risk_scorer.xgb"
            if default.exists():
                model_path = str(default)
        _scorer = XGBoostRiskScorer(model_path=model_path)
    return _scorer


def score_supplier(
    supplier_id: str,
    conflict_nearby: bool = False,
    single_source: bool = False,
    critical_events: int = 0
) -> RiskScore:
    """Convenience function to score a supplier."""
    scorer = get_risk_scorer()
    
    features = FeatureVector(
        conflict_proximity_score=0.8 if conflict_nearby else 0.1,
        single_source_flag=single_source,
        critical_events_count=critical_events
    )
    
    return scorer.score(supplier_id, "supplier", features)
