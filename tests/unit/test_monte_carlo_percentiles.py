"""Unit tests for Monte Carlo percentile outputs."""

from __future__ import annotations

from src.simulation.monte_carlo import DisruptionScenario, MonteCarloSimulator


def test_monte_carlo_returns_delay_percentiles() -> None:
    simulator = MonteCarloSimulator(iterations=1000, seed=42)
    scenario = DisruptionScenario(
        event_type="port_closure",
        affected_entity_id="port-test",
        entity_type="port",
        severity=0.75,
        probability=0.6,
        duration_days=14,
    )
    result = simulator.simulate(scenario)
    payload = result.to_dict()

    assert "p10_delay_days" in payload
    assert "p50_delay_days" in payload
    assert "p90_delay_days" in payload
    assert payload["p10_delay_days"] <= payload["p50_delay_days"] <= payload["p90_delay_days"]
    assert "p10_revenue_at_risk" in payload
