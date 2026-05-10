"""Forecasting module for Meridian.

Provides risk forecasting capabilities:
- Temporal Graph Network (TGN) forecaster (stub)
- Fallback to LSTM-based forecasting
- 7/14/30-day risk predictions
"""

from .tgn_forecaster import (
    TGNForecast,
    TGNForecaster,
    get_tgn_forecaster,
    predict_risk_tgn,
)

__all__ = [
    "TGNForecast",
    "TGNForecaster",
    "get_tgn_forecaster",
    "predict_risk_tgn",
]
