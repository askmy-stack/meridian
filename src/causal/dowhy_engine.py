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
    correlation_ci_lower: Optional[float] = None
    correlation_ci_upper: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "causal_claim_allowed": self.causal_claim_allowed,
            "method": self.method,
            "effect_size": self.effect_size,
            "refutation_passed": self.refutation_passed,
            "disclaimer": self.disclaimer,
            "sample_count": self.sample_count,
        }
        if self.correlation_ci_lower is not None:
            payload["correlation_ci_lower"] = self.correlation_ci_lower
        if self.correlation_ci_upper is not None:
            payload["correlation_ci_upper"] = self.correlation_ci_upper
        return payload


def bootstrap_correlation_ci(
    x: List[float],
    y: List[float],
    *,
    n_bootstrap: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Bootstrap Pearson correlation with percentile confidence interval."""
    n = min(len(x), len(y))
    if n < 2:
        return 0.0, 0.0, 0.0

    xs = np.asarray(x[:n], dtype=float)
    ys = np.asarray(y[:n], dtype=float)
    point = float(np.corrcoef(xs, ys)[0, 1])
    rng = np.random.default_rng(seed)
    samples: List[float] = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        if np.std(xs[idx]) == 0 or np.std(ys[idx]) == 0:
            continue
        samples.append(float(np.corrcoef(xs[idx], ys[idx])[0, 1]))

    if not samples:
        return point, point, point

    alpha = (1.0 - ci) / 2.0
    lower = float(np.quantile(samples, alpha))
    upper = float(np.quantile(samples, 1.0 - alpha))
    return point, lower, upper


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
        corr, ci_lo, ci_hi = bootstrap_correlation_ci(
            event_severities[:n],
            supplier_risk_deltas[:n],
        )
        disclaimer = (
            "Correlation observed — not a verified causal claim (D-005). "
            "Install DoWhy and accumulate ≥30 paired samples for causal estimation."
        )
        if n < min_samples:
            disclaimer += (
                f" Bootstrap {int(0.95 * 100)}% CI on correlation: "
                f"[{round(ci_lo, 3)}, {round(ci_hi, 3)}] (n={n})."
            )
        return CausalAssessment(
            causal_claim_allowed=False,
            method="association_only",
            effect_size=round(corr, 4),
            refutation_passed=False,
            disclaimer=disclaimer,
            sample_count=n,
            correlation_ci_lower=round(ci_lo, 4),
            correlation_ci_upper=round(ci_hi, 4),
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
