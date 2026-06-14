"""DoWhy causal inference wrapper for Meridian alerts (D-005)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

try:
    from dowhy import CausalModel

    DOWHY_AVAILABLE = True
except ImportError:
    DOWHY_AVAILABLE = False
    CausalModel = None  # type: ignore


@dataclass
class CausalAssessment:
    """Result of causal effect estimation for an alert."""

    causal_claim_allowed: bool
    method: str
    effect_size: Optional[float]
    refutation_passed: bool
    disclaimer: str
    sample_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "causal_claim_allowed": self.causal_claim_allowed,
            "method": self.method,
            "effect_size": self.effect_size,
            "refutation_passed": self.refutation_passed,
            "disclaimer": self.disclaimer,
            "sample_count": self.sample_count,
        }


def assess_event_supplier_link(
    event_severities: List[float],
    supplier_risk_deltas: List[float],
    *,
    min_samples: int = 30,
) -> CausalAssessment:
    """Estimate whether event severity plausibly causes supplier risk increases."""
    n = min(len(event_severities), len(supplier_risk_deltas))
    if n < 5:
        return CausalAssessment(
            causal_claim_allowed=False,
            method="insufficient_data",
            effect_size=None,
            refutation_passed=False,
            disclaimer="Not enough paired observations for causal or correlational inference.",
            sample_count=n,
        )

    if not DOWHY_AVAILABLE or n < min_samples:
        corr = float(np.corrcoef(event_severities[:n], supplier_risk_deltas[:n])[0, 1])
        return CausalAssessment(
            causal_claim_allowed=False,
            method="association_only",
            effect_size=round(corr, 4),
            refutation_passed=False,
            disclaimer=(
                "Correlation observed — not a verified causal claim (D-005). "
                "Install DoWhy and accumulate ≥30 paired samples for causal estimation."
            ),
            sample_count=n,
        )

    import pandas as pd

    df = pd.DataFrame(
        {
            "event_severity": event_severities[:n],
            "risk_delta": supplier_risk_deltas[:n],
            "seasonality": np.arange(n) % 7,
        }
    )

    try:
        model = CausalModel(
            data=df,
            treatment="event_severity",
            outcome="risk_delta",
            common_causes=["seasonality"],
        )
        identified = model.identify_effect(proceed_when_unidentifiable=True)
        estimate = model.estimate_effect(
            identified,
            method_name="backdoor.linear_regression",
        )
        refute = model.refute_estimate(
            identified,
            estimate,
            method_name="random_common_cause",
        )

        effect = float(getattr(estimate, "value", 0.0))
        refutation_passed = bool(getattr(refute, "refutation_result", effect != 0))

        return CausalAssessment(
            causal_claim_allowed=refutation_passed and abs(effect) > 0.05,
            method="dowhy_backdoor",
            effect_size=round(effect, 4),
            refutation_passed=refutation_passed,
            disclaimer=(
                "Causal estimate via DoWhy backdoor adjustment with random common cause refutation."
            ),
            sample_count=n,
        )
    except Exception as exc:
        logger.warning("dowhy_assessment_failed", error=str(exc))
        return CausalAssessment(
            causal_claim_allowed=False,
            method="dowhy_error",
            effect_size=None,
            refutation_passed=False,
            disclaimer=f"Causal pipeline error: {exc}",
            sample_count=n,
        )
