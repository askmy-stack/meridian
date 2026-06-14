"""Weak Signal Detection for Meridian.

Detects early warning signals in event streams using:
1. Isolation Forest: Anomaly detection in event patterns
2. LSTM: Time series forecasting of risk trends

Weak signals are precursors to major disruptions:
- Unusual spike in minor conflicts
- Pattern of supplier visits to unstable regions
- Gradual degradation in port throughput
- Anomalous vessel routing patterns
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import structlog
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = structlog.get_logger(__name__)

# Try to import TensorFlow/Keras for LSTM
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    logger.warning("tensorflow_not_available", message="LSTM forecasting disabled")


@dataclass
class WeakSignal:
    """Detected weak signal anomaly."""
    signal_type: str  # "anomaly", "trend", "pattern"
    entity_id: Optional[str]
    entity_type: Optional[str]  # supplier, port, region
    
    # Signal characteristics
    anomaly_score: float  # 0-1, higher = more anomalous
    confidence: float  # 0-1
    
    # Temporal
    detection_timestamp: str
    lookback_days: int
    
    # Details
    description: str
    contributing_factors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Recommended actions
    suggested_monitoring: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "signal_type": self.signal_type,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "anomaly_score": round(self.anomaly_score, 4),
            "confidence": round(self.confidence, 4),
            "detection_timestamp": self.detection_timestamp,
            "lookback_days": self.lookback_days,
            "description": self.description,
            "contributing_factors": self.contributing_factors,
            "suggested_monitoring": self.suggested_monitoring
        }


@dataclass
class TrendForecast:
    """LSTM-based trend forecast."""
    entity_id: str
    entity_type: str
    
    # Current state
    current_risk_score: float
    
    # Forecast
    forecast_horizon_days: int
    forecasted_scores: List[float]  # Risk scores for future days
    
    # Trend analysis
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_strength: float  # 0-1
    
    # Confidence intervals
    confidence_lower: List[float]
    confidence_upper: List[float]
    
    # Critical date (if any)
    projected_critical_date: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "current_risk_score": round(self.current_risk_score, 4),
            "forecast_horizon_days": self.forecast_horizon_days,
            "forecasted_scores": [round(s, 4) for s in self.forecasted_scores],
            "trend_direction": self.trend_direction,
            "trend_strength": round(self.trend_strength, 4),
            "confidence_lower": [round(s, 4) for s in self.confidence_lower],
            "confidence_upper": [round(s, 4) for s in self.confidence_upper],
            "projected_critical_date": self.projected_critical_date
        }


class IsolationForestAnomalyDetector:
    """Anomaly detection using Isolation Forest.
    
    Detects unusual patterns in event time series:
    - Spike in conflict events
    - Unusual port congestion patterns
    - Anomalous supplier activity
    
    Usage:
        detector = IsolationForestAnomalyDetector()
        
        # Daily event counts for a supplier
        data = np.array([[0, 1, 0, 2, 5, 12, 15]])  # 7 days
        is_anomaly = detector.detect(data)
        
        if is_anomaly:
            print("Weak signal detected: unusual activity spike")
    """
    
    def __init__(
        self,
        contamination: float = 0.1,
        n_estimators: int = 100,
        random_state: int = 42
    ):
        """Initialize anomaly detector.
        
        Args:
            contamination: Expected proportion of anomalies (0-0.5)
            n_estimators: Number of trees in forest
            random_state: Random seed for reproducibility
        """
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        
        self.logger = logger.bind(detector="IsolationForestAnomalyDetector")
        
        self._model: Optional[IsolationForest] = None
        self._scaler = StandardScaler()
        self._is_fitted = False
        
        self._init_model()
    
    def _init_model(self) -> None:
        """Initialize Isolation Forest model."""
        self._model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1  # Use all cores
        )
        self.logger.info("isolation_forest_initialized")
    
    def fit(self, X: np.ndarray) -> None:
        """Fit detector on historical data.
        
        Args:
            X: Training data (n_samples, n_features)
        """
        # Scale features
        X_scaled = self._scaler.fit_transform(X)
        
        # Fit model
        self._model.fit(X_scaled)
        self._is_fitted = True
        
        self.logger.info("detector_fitted", samples=X.shape[0], features=X.shape[1])
    
    def detect(self, X: np.ndarray) -> Tuple[bool, float, List[WeakSignal]]:
        """Detect anomalies in data.
        
        Args:
            X: Data to check (1, n_features) or (n_samples, n_features)
            
        Returns:
            Tuple of (is_anomaly, anomaly_score, list of WeakSignals)
        """
        if not self._is_fitted:
            # Auto-fit on provided data
            self.fit(X)
        
        # Scale
        X_scaled = self._scaler.transform(X)
        
        # Predict
        predictions = self._model.predict(X_scaled)  # -1 for anomaly, 1 for normal
        scores = self._model.score_samples(X_scaled)  # Anomaly score (negative = more anomalous)
        
        # Check if anomaly (any sample is anomalous)
        is_anomaly = np.any(predictions == -1)
        
        # Get max anomaly score (most anomalous sample)
        max_score = float(np.min(scores))  # Lower score = more anomalous
        
        # Normalize to 0-1
        normalized_score = min(1.0, max(0.0, -max_score))
        
        # Generate weak signals for anomalous points
        signals = []
        
        if is_anomaly:
            for i, (pred, score) in enumerate(zip(predictions, scores)):
                if pred == -1:
                    signal = WeakSignal(
                        signal_type="anomaly",
                        entity_id=None,
                        entity_type=None,
                        anomaly_score=min(1.0, max(0.0, -float(score))),
                        confidence=0.7,
                        detection_timestamp="now",  # Should be actual timestamp
                        lookback_days=7,
                        description=f"Anomalous pattern detected at index {i}",
                        contributing_factors=[
                            {"factor": "statistical_deviation", "contribution": 0.8}
                        ],
                        suggested_monitoring=[
                            "Increase monitoring frequency",
                            "Check for related events in region"
                        ]
                    )
                    signals.append(signal)
        
        return is_anomaly, normalized_score, signals
    
    def detect_event_series(
        self,
        entity_id: str,
        entity_type: str,
        daily_event_counts: List[int],
        window_size: int = 7
    ) -> List[WeakSignal]:
        """Detect anomalies in time series of event counts.
        
        Args:
            entity_id: Entity being monitored
            entity_type: Type of entity
            daily_event_counts: List of daily event counts
            window_size: Size of sliding window for detection
            
        Returns:
            List of WeakSignals detected
        """
        if len(daily_event_counts) < window_size:
            return []
        
        # Create sliding windows
        X = []
        for i in range(len(daily_event_counts) - window_size + 1):
            window = daily_event_counts[i:i + window_size]
            # Features: mean, std, max, trend (slope)
            features = [
                np.mean(window),
                np.std(window),
                max(window),
                self._calculate_trend(window)
            ]
            X.append(features)
        
        X = np.array(X)
        
        # Detect
        is_anomaly, score, signals = self.detect(X)
        
        # Enrich signals with entity info
        for signal in signals:
            signal.entity_id = entity_id
            signal.entity_type = entity_type
        
        return signals
    
    def _calculate_trend(self, window: List[float]) -> float:
        """Calculate linear trend (slope) in window."""
        if len(window) < 2:
            return 0.0
        
        x = np.arange(len(window))
        y = np.array(window)
        
        # Linear regression
        A = np.vstack([x, np.ones(len(x))]).T
        slope, _ = np.linalg.lstsq(A, y, rcond=None)[0]
        
        return float(slope)


class LSTMTrendForecaster:
    """LSTM-based trend forecasting for risk scores.
    
    Forecasts future risk trends based on historical patterns.
    Predicts when risk might reach critical thresholds.
    
    Usage:
        forecaster = LSTMTrendForecaster()
        
        # Historical daily risk scores
        history = [0.2, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45]
        
        forecast = forecaster.forecast("supplier-123", "supplier", history, days=7)
        print(forecast.trend_direction)  # "increasing"
    """
    
    def __init__(
        self,
        sequence_length: int = 14,
        forecast_horizon: int = 7,
        hidden_units: int = 50,
        epochs: int = 50
    ):
        """Initialize LSTM forecaster.
        
        Args:
            sequence_length: Days of history to use
            forecast_horizon: Days to forecast ahead
            hidden_units: LSTM hidden layer size
            epochs: Training epochs
        """
        self.sequence_length = sequence_length
        self.forecast_horizon = forecast_horizon
        self.hidden_units = hidden_units
        self.epochs = epochs
        
        self.logger = logger.bind(forecaster="LSTMTrendForecaster")
        
        self._model = None
        self._scaler = StandardScaler()
        
        if TF_AVAILABLE:
            self._build_model()
    
    def _build_model(self) -> None:
        """Build LSTM model architecture."""
        if not TF_AVAILABLE:
            return
        
        model = Sequential([
            LSTM(self.hidden_units, activation='relu', input_shape=(self.sequence_length, 1)),
            Dropout(0.2),
            Dense(32, activation='relu'),
            Dense(self.forecast_horizon)
        ])
        
        model.compile(
            optimizer='adam',
            loss='mse',
            metrics=['mae']
        )
        
        self._model = model
        self.logger.info("lstm_model_built")
    
    def _prepare_data(
        self,
        historical_scores: List[float]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare time series data for LSTM.
        
        Creates sequences of (sequence_length) -> (forecast_horizon)
        """
        # Scale data
        scores_array = np.array(historical_scores).reshape(-1, 1)
        scaled = self._scaler.fit_transform(scores_array).flatten()
        
        X, y = [], []
        
        for i in range(len(scaled) - self.sequence_length - self.forecast_horizon + 1):
            X.append(scaled[i:i + self.sequence_length])
            y.append(scaled[i + self.sequence_length:i + self.sequence_length + self.forecast_horizon])
        
        X = np.array(X).reshape(-1, self.sequence_length, 1)
        y = np.array(y)
        
        return X, y
    
    def fit(self, historical_scores: List[float]) -> None:
        """Train LSTM on historical data.
        
        Args:
            historical_scores: List of daily risk scores
        """
        if not TF_AVAILABLE or len(historical_scores) < self.sequence_length + self.forecast_horizon:
            self.logger.warning(
                "insufficient_data_for_training",
                samples=len(historical_scores),
                required=self.sequence_length + self.forecast_horizon
            )
            return
        
        X, y = self._prepare_data(historical_scores)
        
        if len(X) == 0:
            return
        
        # Train
        self._model.fit(
            X, y,
            epochs=self.epochs,
            batch_size=4,
            verbose=0,
            validation_split=0.2
        )
        
        self.logger.info("lstm_model_trained", sequences=len(X))
    
    def forecast(
        self,
        entity_id: str,
        entity_type: str,
        historical_scores: List[float],
        days: int = 7,
        critical_threshold: float = 0.8
    ) -> TrendForecast:
        """Forecast future risk trend.
        
        Args:
            entity_id: Entity ID
            entity_type: Type of entity
            historical_scores: Historical daily risk scores
            days: Days to forecast
            critical_threshold: Risk level considered critical
            
        Returns:
            TrendForecast with predictions and trend analysis
        """
        min_lstm_samples = self.sequence_length + self.forecast_horizon
        if not TF_AVAILABLE or len(historical_scores) < min_lstm_samples:
            # Need sequence_length + forecast_horizon to train; CSV/graph fallbacks often
            # provide exactly sequence_length points — use linear extrapolation instead.
            return self._simple_forecast(
                entity_id, entity_type, historical_scores, days, critical_threshold
            )

        self.fit(historical_scores)

        # Prepare last sequence (scaler fitted in fit() / _prepare_data)
        last_sequence = np.array(historical_scores[-self.sequence_length:])
        scaled_sequence = self._scaler.transform(last_sequence.reshape(-1, 1)).flatten()
        X = scaled_sequence.reshape(1, self.sequence_length, 1)
        
        # Predict
        prediction_scaled = self._model.predict(X, verbose=0)
        prediction = self._scaler.inverse_transform(prediction_scaled)[0]
        
        # Calculate confidence intervals (simplified: +/- 10%)
        confidence_margin = 0.1
        lower = [max(0, p - confidence_margin) for p in prediction]
        upper = [min(1, p + confidence_margin) for p in prediction]
        
        # Determine trend
        current = historical_scores[-1] if historical_scores else 0
        avg_future = np.mean(prediction)
        
        if avg_future > current * 1.2:
            trend_dir = "increasing"
            trend_strength = min(1.0, (avg_future - current) / 0.5)
        elif avg_future < current * 0.8:
            trend_dir = "decreasing"
            trend_strength = min(1.0, (current - avg_future) / 0.5)
        else:
            trend_dir = "stable"
            trend_strength = 0.1
        
        # Find projected critical date
        critical_date = None
        for i, score in enumerate(prediction):
            if score >= critical_threshold:
                critical_date = f"+{i+1} days"
                break
        
        return TrendForecast(
            entity_id=entity_id,
            entity_type=entity_type,
            current_risk_score=current,
            forecast_horizon_days=days,
            forecasted_scores=prediction[:days].tolist(),
            trend_direction=trend_dir,
            trend_strength=trend_strength,
            confidence_lower=lower[:days],
            confidence_upper=upper[:days],
            projected_critical_date=critical_date
        )
    
    def _simple_forecast(
        self,
        entity_id: str,
        entity_type: str,
        historical_scores: List[float],
        days: int,
        critical_threshold: float
    ) -> TrendForecast:
        """Simple linear trend fallback when LSTM unavailable."""
        if len(historical_scores) < 2:
            # No trend, stable forecast
            current = historical_scores[0] if historical_scores else 0.5
            return TrendForecast(
                entity_id=entity_id,
                entity_type=entity_type,
                current_risk_score=current,
                forecast_horizon_days=days,
                forecasted_scores=[current] * days,
                trend_direction="stable",
                trend_strength=0.0,
                confidence_lower=[max(0, current - 0.1)] * days,
                confidence_upper=[min(1, current + 0.1)] * days
            )
        
        # Calculate linear trend
        x = np.arange(len(historical_scores))
        y = np.array(historical_scores)
        
        A = np.vstack([x, np.ones(len(x))]).T
        slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
        
        # Forecast
        current = historical_scores[-1]
        forecasted = []
        
        for i in range(1, days + 1):
            score = intercept + slope * (len(historical_scores) + i - 1)
            score = max(0, min(1, score))  # Clamp to 0-1
            forecasted.append(score)
        
        # Determine trend
        if slope > 0.01:
            trend_dir = "increasing"
            trend_strength = min(1.0, slope * 10)
        elif slope < -0.01:
            trend_dir = "decreasing"
            trend_strength = min(1.0, -slope * 10)
        else:
            trend_dir = "stable"
            trend_strength = 0.1
        
        # Find critical date
        critical_date = None
        for i, score in enumerate(forecasted):
            if score >= critical_threshold:
                critical_date = f"+{i+1} days"
                break
        
        return TrendForecast(
            entity_id=entity_id,
            entity_type=entity_type,
            current_risk_score=current,
            forecast_horizon_days=days,
            forecasted_scores=forecasted,
            trend_direction=trend_dir,
            trend_strength=trend_strength,
            confidence_lower=[max(0, s - 0.15) for s in forecasted],
            confidence_upper=[min(1, s + 0.15) for s in forecasted],
            projected_critical_date=critical_date
        )


class WeakSignalDetector:
    """Combined weak signal detection pipeline.
    
    Integrates Isolation Forest anomaly detection with LSTM trend forecasting.
    
    Usage:
        detector = WeakSignalDetector()
        
        # Monitor supplier
        signals = detector.monitor_supplier(
            "supplier-123",
            daily_event_counts=[0, 0, 1, 0, 2, 5, 12],
            historical_scores=[0.2, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5]
        )
    """
    
    def __init__(self):
        """Initialize weak signal detector."""
        self.logger = logger.bind(detector="WeakSignalDetector")
        
        self.anomaly_detector = IsolationForestAnomalyDetector()
        self.trend_forecaster = LSTMTrendForecaster()
    
    def monitor_supplier(
        self,
        supplier_id: str,
        daily_event_counts: List[int],
        historical_scores: List[float]
    ) -> Tuple[List[WeakSignal], Optional[TrendForecast]]:
        """Monitor a supplier for weak signals.
        
        Args:
            supplier_id: Supplier entity ID
            daily_event_counts: Recent daily event counts (last 7-30 days)
            historical_scores: Historical risk scores (last 14+ days)
            
        Returns:
            Tuple of (weak_signals, trend_forecast)
        """
        # Detect anomalies
        weak_signals = self.anomaly_detector.detect_event_series(
            supplier_id,
            "supplier",
            daily_event_counts
        )
        
        # Forecast trend
        forecast = None
        if len(historical_scores) >= 7:
            forecast = self.trend_forecaster.forecast(
                supplier_id,
                "supplier",
                historical_scores
            )
            
            # Generate weak signal from trend if increasing
            if forecast.trend_direction == "increasing" and forecast.trend_strength > 0.5:
                trend_signal = WeakSignal(
                    signal_type="trend",
                    entity_id=supplier_id,
                    entity_type="supplier",
                    anomaly_score=forecast.trend_strength,
                    confidence=0.6,
                    detection_timestamp="now",
                    lookback_days=len(historical_scores),
                    description=f"Risk trend increasing: {forecast.trend_strength:.0%} strength",
                    contributing_factors=[
                        {"factor": "historical_trend", "contribution": 0.7},
                        {"factor": "event_acceleration", "contribution": 0.3}
                    ],
                    suggested_monitoring=[
                        "Review supplier contingency plans",
                        "Identify alternative suppliers",
                        f"Projected critical date: {forecast.projected_critical_date or 'none'}"
                    ]
                )
                weak_signals.append(trend_signal)
        
        self.logger.info(
            "supplier_monitoring_complete",
            supplier_id=supplier_id,
            signals_found=len(weak_signals),
            has_forecast=forecast is not None
        )
        
        return weak_signals, forecast
    
    def monitor_port(
        self,
        port_id: str,
        daily_vessel_counts: List[int],
        congestion_scores: List[float]
    ) -> Tuple[List[WeakSignal], Optional[TrendForecast]]:
        """Monitor a port for weak signals."""
        # Similar to supplier monitoring
        weak_signals = self.anomaly_detector.detect_event_series(
            port_id,
            "port",
            daily_vessel_counts
        )
        
        forecast = None
        if len(congestion_scores) >= 7:
            forecast = self.trend_forecaster.forecast(
                port_id,
                "port",
                congestion_scores
            )
        
        return weak_signals, forecast
    
    def scan_all_entities(
        self,
        entity_snapshots: List[Dict[str, Any]]
    ) -> Dict[str, List[WeakSignal]]:
        """Scan multiple entities for weak signals.
        
        Args:
            entity_snapshots: List of entity data dicts with:
                - id, type, event_counts, risk_scores
                
        Returns:
            Dict mapping entity_id -> list of weak signals
        """
        all_signals = {}
        
        for snapshot in entity_snapshots:
            entity_id = snapshot["id"]
            entity_type = snapshot["type"]
            
            if entity_type == "supplier":
                signals, _ = self.monitor_supplier(
                    entity_id,
                    snapshot.get("event_counts", []),
                    snapshot.get("risk_scores", [])
                )
            elif entity_type == "port":
                signals, _ = self.monitor_port(
                    entity_id,
                    snapshot.get("vessel_counts", []),
                    snapshot.get("congestion_scores", [])
                )
            else:
                continue
            
            if signals:
                all_signals[entity_id] = signals
        
        return all_signals


# Singleton instance
_detector: Optional[WeakSignalDetector] = None


def get_weak_signal_detector() -> WeakSignalDetector:
    """Get or create singleton detector."""
    global _detector
    if _detector is None:
        _detector = WeakSignalDetector()
    return _detector
