"""Feature vector datatypes for SCRI — no XGBoost dependency."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np


@dataclass
class FeatureVector:
    """Feature vector for risk scoring."""

    conflict_proximity_score: float = 0.0
    political_stability_index: float = 0.5
    port_congestion_score: float = 0.0
    weather_risk_score: float = 0.0
    recent_events_count: int = 0
    critical_events_count: int = 0
    dependency_depth: int = 1
    single_source_flag: bool = False
    alternative_sources_count: int = 0
    supplier_financial_health: float = 0.5
    market_volatility_index: float = 0.0
    historical_disruption_count: int = 0
    avg_resolution_time_days: float = 0.0

    def to_array(self) -> np.ndarray:
        """Convert to numpy array for model input."""
        return np.array(
            [
                self.conflict_proximity_score,
                self.political_stability_index,
                self.port_congestion_score,
                self.weather_risk_score,
                min(self.recent_events_count / 10, 1.0),
                min(self.critical_events_count / 5, 1.0),
                min(self.dependency_depth / 5, 1.0),
                float(self.single_source_flag),
                min(self.alternative_sources_count / 5, 1.0),
                self.supplier_financial_health,
                self.market_volatility_index,
                min(self.historical_disruption_count / 5, 1.0),
                min(self.avg_resolution_time_days / 30, 1.0),
            ]
        )

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "conflict_proximity_score": self.conflict_proximity_score,
            "political_stability_index": self.political_stability_index,
            "port_congestion_score": self.port_congestion_score,
            "weather_risk_score": self.weather_risk_score,
            "recent_events_count_normalized": min(self.recent_events_count / 10, 1.0),
            "critical_events_count_normalized": min(self.critical_events_count / 5, 1.0),
            "dependency_depth_normalized": min(self.dependency_depth / 5, 1.0),
            "single_source_flag": float(self.single_source_flag),
            "alternative_sources_count_normalized": min(self.alternative_sources_count / 5, 1.0),
            "supplier_financial_health": self.supplier_financial_health,
            "market_volatility_index": self.market_volatility_index,
            "historical_disruption_count_normalized": min(
                self.historical_disruption_count / 5, 1.0
            ),
            "avg_resolution_time_days_normalized": min(self.avg_resolution_time_days / 30, 1.0),
        }
