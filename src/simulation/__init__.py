"""Simulation module for Meridian.

Provides disruption simulation and propagation analysis:
- Monte Carlo disruption simulator
- BFS propagation engine
- Sensitivity analysis
"""

from .monte_carlo import (
    DisruptionScenario,
    MonteCarloSimulator,
    SensitivityAnalyzer,
    SimulationResult,
    get_simulator,
    simulate_disruption,
)
from .propagation import (
    BFSPropagationEngine,
    PropagationResult,
    PropagationStep,
    get_propagation_engine,
    propagate_disruption,
)

__all__ = [
    # Monte Carlo
    "DisruptionScenario",
    "MonteCarloSimulator",
    "SensitivityAnalyzer",
    "SimulationResult",
    "get_simulator",
    "simulate_disruption",
    
    # Propagation
    "BFSPropagationEngine",
    "PropagationResult",
    "PropagationStep",
    "get_propagation_engine",
    "propagate_disruption",
]
