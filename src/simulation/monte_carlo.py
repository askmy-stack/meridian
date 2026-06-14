"""Monte Carlo Disruption Simulator for Meridian.

Simulates supply chain disruptions using Monte Carlo methods:
- Random sampling of event probabilities
- Propagation through supply chain network
- Impact quantification on suppliers, routes, SKUs

Runs minimum 1000 iterations as per AGENTS.md requirements.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime
from collections import defaultdict

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DisruptionScenario:
    """A single disruption scenario for simulation."""
    event_type: str  # "conflict", "weather", "port_closure", "cyber", etc.
    affected_entity_id: str
    entity_type: str  # "supplier", "port", "chokepoint", "route"
    severity: float  # 0-1
    probability: float  # 0-1, likelihood of occurring
    duration_days: int
    
    # Optional: affected SKUs, regions
    affected_skus: List[str] = field(default_factory=list)
    affected_regions: List[str] = field(default_factory=list)


@dataclass
class SimulationResult:
    """Result from Monte Carlo simulation."""
    scenario: DisruptionScenario
    iterations: int
    
    # Impact metrics
    affected_supplier_count: int
    affected_sku_count: int
    total_revenue_at_risk: float
    
    # Probabilistic outcomes
    disruption_probability: float  # 0-1
    expected_duration_days: float
    p10_delay_days: float = 0.0
    p50_delay_days: float = 0.0
    p90_delay_days: float = 0.0
    p10_revenue_at_risk: float = 0.0
    p50_revenue_at_risk: float = 0.0
    p90_revenue_at_risk: float = 0.0
    
    # Distribution of outcomes
    impact_distribution: Dict[str, List[float]] = field(default_factory=dict)
    
    # Timeline of propagation
    propagation_steps: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scenario": {
                "event_type": self.scenario.event_type,
                "affected_entity_id": self.scenario.affected_entity_id,
                "entity_type": self.scenario.entity_type,
                "severity": self.scenario.severity,
            },
            "iterations": self.iterations,
            "affected_supplier_count": self.affected_supplier_count,
            "affected_sku_count": self.affected_sku_count,
            "total_revenue_at_risk": round(self.total_revenue_at_risk, 2),
            "disruption_probability": round(self.disruption_probability, 4),
            "expected_duration_days": round(self.expected_duration_days, 1),
            "p10_delay_days": round(self.p10_delay_days, 1),
            "p50_delay_days": round(self.p50_delay_days, 1),
            "p90_delay_days": round(self.p90_delay_days, 1),
            "p10_revenue_at_risk": round(self.p10_revenue_at_risk, 2),
            "p50_revenue_at_risk": round(self.p50_revenue_at_risk, 2),
            "p90_revenue_at_risk": round(self.p90_revenue_at_risk, 2),
            "propagation_steps": len(self.propagation_steps)
        }


class MonteCarloSimulator:
    """Monte Carlo disruption simulator.
    
    Simulates supply chain disruptions with probabilistic outcomes.
    Minimum 1000 iterations as per AGENTS.md.
    
    Usage:
        simulator = MonteCarloSimulator(iterations=1000)
        
        scenario = DisruptionScenario(
            event_type="port_closure",
            affected_entity_id="port-Shanghai",
            entity_type="port",
            severity=0.8,
            probability=0.3,
            duration_days=14
        )
        
        result = simulator.simulate(scenario)
        print(f"Disruption probability: {result.disruption_probability:.1%}")
        print(f"Suppliers affected: {result.affected_supplier_count}")
    """
    
    DEFAULT_ITERATIONS = 1000
    
    def __init__(
        self,
        iterations: int = DEFAULT_ITERATIONS,
        seed: Optional[int] = None
    ):
        """Initialize simulator.
        
        Args:
            iterations: Number of Monte Carlo iterations (min 1000)
            seed: Random seed for reproducibility
        """
        self.iterations = max(iterations, self.DEFAULT_ITERATIONS)
        self.seed = seed
        
        if seed:
            random.seed(seed)
            np.random.seed(seed)
        
        self.logger = logger.bind(
            simulator="MonteCarloSimulator",
            iterations=self.iterations
        )
        
        self._propagation_engine = None

    def _get_bfs_engine(self):
        """Lazy-load Neo4j BFS propagation engine."""
        if self._propagation_engine is None:
            try:
                from .propagation import BFSPropagationEngine

                self._propagation_engine = BFSPropagationEngine()
            except Exception as exc:
                self.logger.warning("bfs_engine_unavailable", error=str(exc))
                self._propagation_engine = False
        return self._propagation_engine if self._propagation_engine is not False else None
    
    def simulate(
        self,
        scenario: DisruptionScenario,
        supplier_ids: Optional[List[str]] = None
    ) -> SimulationResult:
        """Run Monte Carlo simulation for a scenario.
        
        Args:
            scenario: Disruption scenario to simulate
            supplier_ids: Optional list of suppliers to analyze
            
        Returns:
            SimulationResult with probabilistic outcomes
        """
        self.logger.info(
            "starting_simulation",
            event_type=scenario.event_type,
            entity_id=scenario.affected_entity_id,
            severity=scenario.severity
        )
        
        # Track outcomes across iterations
        disruption_count = 0
        total_duration = 0
        affected_suppliers_per_run = []
        affected_skus_per_run = []
        revenue_at_risk_per_run = []
        delay_days_per_run: List[float] = []
        
        propagation_paths = []
        
        for i in range(self.iterations):
            # Run single iteration
            outcome = self._run_iteration(scenario, supplier_ids)
            
            if outcome["disrupted"]:
                disruption_count += 1
                total_duration += outcome["duration"]
                delay_days_per_run.append(float(outcome["duration"]))
                affected_suppliers_per_run.append(outcome["affected_suppliers"])
                affected_skus_per_run.append(outcome["affected_skus"])
                revenue_at_risk_per_run.append(outcome["revenue_at_risk"])
                propagation_paths.append(outcome["propagation_path"])
        
        # Calculate statistics
        disruption_probability = disruption_count / self.iterations
        expected_duration = (
            total_duration / disruption_count if disruption_count > 0 else 0
        )
        
        # Aggregate unique affected entities
        all_affected_suppliers = set()
        all_affected_skus = set()
        for path in propagation_paths:
            all_affected_suppliers.update(path.get("suppliers", []))
            all_affected_skus.update(path.get("skus", []))
        
        # Total revenue at risk (expected value)
        expected_revenue_at_risk = (
            np.mean(revenue_at_risk_per_run) if revenue_at_risk_per_run else 0
        )

        p10_delay = float(np.percentile(delay_days_per_run, 10)) if delay_days_per_run else 0.0
        p50_delay = float(np.percentile(delay_days_per_run, 50)) if delay_days_per_run else 0.0
        p90_delay = float(np.percentile(delay_days_per_run, 90)) if delay_days_per_run else 0.0
        p10_rev = float(np.percentile(revenue_at_risk_per_run, 10)) if revenue_at_risk_per_run else 0.0
        p50_rev = float(np.percentile(revenue_at_risk_per_run, 50)) if revenue_at_risk_per_run else 0.0
        p90_rev = float(np.percentile(revenue_at_risk_per_run, 90)) if revenue_at_risk_per_run else 0.0
        
        # Build propagation steps (aggregate from all runs)
        propagation_steps = self._aggregate_propagation_paths(propagation_paths)
        
        result = SimulationResult(
            scenario=scenario,
            iterations=self.iterations,
            affected_supplier_count=len(all_affected_suppliers),
            affected_sku_count=len(all_affected_skus),
            total_revenue_at_risk=expected_revenue_at_risk,
            disruption_probability=disruption_probability,
            expected_duration_days=expected_duration,
            p10_delay_days=p10_delay,
            p50_delay_days=p50_delay,
            p90_delay_days=p90_delay,
            p10_revenue_at_risk=p10_rev,
            p50_revenue_at_risk=p50_rev,
            p90_revenue_at_risk=p90_rev,
            impact_distribution={
                "suppliers": affected_suppliers_per_run,
                "skus": affected_skus_per_run,
                "revenue": revenue_at_risk_per_run
            },
            propagation_steps=propagation_steps
        )
        
        self.logger.info(
            "simulation_complete",
            disruption_probability=disruption_probability,
            affected_suppliers=len(all_affected_suppliers),
            expected_duration=expected_duration
        )
        
        return result
    
    def _run_iteration(
        self,
        scenario: DisruptionScenario,
        supplier_ids: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Run single Monte Carlo iteration.
        
        Returns:
            Dict with disruption outcome
        """
        outcome = {
            "disrupted": False,
            "duration": 0,
            "affected_suppliers": 0,
            "affected_skus": 0,
            "revenue_at_risk": 0.0,
            "propagation_path": {"suppliers": [], "skus": []}
        }
        
        # Check if event occurs
        if random.random() > scenario.probability:
            return outcome
        
        # Event occurs - determine actual severity
        # Add noise: actual severity varies around scenario severity
        actual_severity = np.random.normal(
            scenario.severity,
            0.1  # Standard deviation
        )
        actual_severity = max(0, min(1, actual_severity))
        
        # Determine if disruption propagates
        if actual_severity < 0.3:
            # Low severity - contained
            outcome["disrupted"] = True
            outcome["duration"] = max(1, int(scenario.duration_days * 0.5))
            return outcome
        
        # Propagate through network
        propagation = self._propagate_disruption(
            scenario,
            actual_severity,
            supplier_ids
        )
        
        outcome["disrupted"] = True
        outcome["duration"] = self._calculate_duration(scenario, propagation)
        outcome["affected_suppliers"] = len(propagation["suppliers"])
        outcome["affected_skus"] = len(propagation["skus"])
        outcome["revenue_at_risk"] = self._calculate_revenue_impact(propagation)
        outcome["propagation_path"] = propagation
        
        return outcome
    
    def _propagate_disruption(
        self,
        scenario: DisruptionScenario,
        severity: float,
        supplier_ids: Optional[List[str]],
    ) -> Dict[str, List[str]]:
        """Propagate disruption through supply chain network."""
        engine = self._get_bfs_engine()
        if engine is not None:
            try:
                result = engine.propagate(
                    source_entity_id=scenario.affected_entity_id,
                    source_entity_type=scenario.entity_type,
                    impact_score=severity,
                    affected_skus=scenario.affected_skus,
                )
                return {
                    "suppliers": list(result.affected_suppliers),
                    "skus": list(result.affected_skus),
                    "routes": [],
                }
            except Exception as exc:
                self.logger.warning("bfs_propagation_failed", error=str(exc))

        affected = {
            "suppliers": set(),
            "skus": set(),
            "routes": set(),
        }
        
        # Add initial affected entity
        affected["suppliers"].add(scenario.affected_entity_id)
        
        # Propagation probability based on severity
        # Higher severity = more likely to propagate
        propagation_prob = severity * 0.8  # Cap at 80%
        
        # Simulate propagation through graph
        # In production, this queries Neo4j for actual relationships
        # For now, simulate based on network topology assumptions
        
        if supplier_ids:
            # Simulate connected suppliers
            for supplier_id in supplier_ids:
                if supplier_id != scenario.affected_entity_id:
                    # Check if connected (simplified model)
                    # In reality, check SUPPLIES, SHIPS_VIA relationships
                    if random.random() < propagation_prob * 0.3:
                        affected["suppliers"].add(supplier_id)
        
        # Add scenario-specific SKUs
        affected["skus"].update(scenario.affected_skus)
        
        # Simulate SKU impact from suppliers
        # Each affected supplier impacts 1-10 SKUs on average
        for _ in affected["suppliers"]:
            num_skus = random.randint(1, 10)
            for i in range(num_skus):
                affected["skus"].add(f"sku-{random.randint(1000, 9999)}")
        
        return {
            "suppliers": list(affected["suppliers"]),
            "skus": list(affected["skus"]),
            "routes": list(affected["routes"])
        }
    
    def _calculate_duration(
        self,
        scenario: DisruptionScenario,
        propagation: Dict[str, List[str]]
    ) -> int:
        """Calculate expected disruption duration."""
        base_duration = scenario.duration_days
        
        # Longer if more suppliers affected
        supplier_multiplier = 1 + (len(propagation["suppliers"]) * 0.1)
        
        # Add random variation
        variation = np.random.normal(1.0, 0.2)
        
        duration = int(base_duration * supplier_multiplier * variation)
        return max(1, duration)
    
    def _calculate_revenue_impact(
        self,
        propagation: Dict[str, List[str]]
    ) -> float:
        """Calculate revenue at risk from propagation."""
        # Simplified model: $100K-$1M per SKU per day
        # In production, query actual SKU revenue data
        
        total_revenue = 0
        for sku in propagation["skus"]:
            # Random revenue between $100K and $1M
            revenue = random.uniform(100000, 1000000)
            total_revenue += revenue
        
        return total_revenue
    
    def _aggregate_propagation_paths(
        self,
        paths: List[Dict[str, List[str]]]
    ) -> List[Dict[str, Any]]:
        """Aggregate propagation paths from multiple iterations."""
        if not paths:
            return []
        
        # Count occurrences of each supplier/SKU
        supplier_counts = defaultdict(int)
        sku_counts = defaultdict(int)
        
        for path in paths:
            for supplier in path.get("suppliers", []):
                supplier_counts[supplier] += 1
            for sku in path.get("skus", []):
                sku_counts[sku] += 1
        
        # Build propagation steps
        steps = []
        
        # Step 1: Initial impact
        steps.append({
            "step": 1,
            "description": "Initial disruption",
            "affected_entities": list(set().union(*[p.get("suppliers", []) for p in paths[:1]]))
        })
        
        # Step 2: Propagation
        propagated_suppliers = [
            s for s, count in supplier_counts.items()
            if count > len(paths) * 0.1  # Appears in >10% of runs
        ]
        
        if propagated_suppliers:
            steps.append({
                "step": 2,
                "description": "Propagation to connected suppliers",
                "affected_entities": propagated_suppliers[:10]  # Top 10
            })
        
        # Step 3: SKU impact
        affected_skus = [
            s for s, count in sku_counts.items()
            if count > len(paths) * 0.05
        ]
        
        if affected_skus:
            steps.append({
                "step": 3,
                "description": "SKU availability impact",
                "affected_skus": affected_skus[:20]  # Top 20
            })
        
        return steps
    
    def run_batch_simulations(
        self,
        scenarios: List[DisruptionScenario]
    ) -> List[SimulationResult]:
        """Run simulations for multiple scenarios.
        
        Args:
            scenarios: List of disruption scenarios
            
        Returns:
            List of SimulationResults
        """
        results = []
        
        for scenario in scenarios:
            result = self.simulate(scenario)
            results.append(result)
        
        return results
    
    def get_risk_ranking(
        self,
        results: List[SimulationResult]
    ) -> List[Tuple[DisruptionScenario, float]]:
        """Rank scenarios by risk impact.
        
        Returns:
            List of (scenario, risk_score) sorted by risk (highest first)
        """
        ranked = []
        
        for result in results:
            # Composite risk score
            # Combines disruption probability, impact magnitude, and duration
            impact_score = (
                result.affected_supplier_count * 0.3 +
                result.affected_sku_count * 0.1 +
                (result.total_revenue_at_risk / 1000000) * 0.4
            )
            
            risk_score = (
                result.disruption_probability * 0.4 +
                min(impact_score, 1.0) * 0.4 +
                min(result.expected_duration_days / 30, 1.0) * 0.2
            )
            
            ranked.append((result.scenario, risk_score))
        
        # Sort by risk score descending
        ranked.sort(key=lambda x: x[1], reverse=True)
        
        return ranked


class SensitivityAnalyzer:
    """Sensitivity analysis for disruption scenarios.
    
    Analyzes how changes in parameters affect outcomes.
    """
    
    def __init__(self, simulator: MonteCarloSimulator):
        """Initialize with simulator instance."""
        self.simulator = simulator
        self.logger = logger.bind(analyzer="SensitivityAnalyzer")
    
    def analyze_parameter_sensitivity(
        self,
        base_scenario: DisruptionScenario,
        parameter: str,  # "severity", "probability", "duration_days"
        values: List[float]
    ) -> Dict[str, List[float]]:
        """Analyze sensitivity to a parameter.
        
        Args:
            base_scenario: Base scenario to modify
            parameter: Parameter to vary
            values: Values to test
            
        Returns:
            Dict mapping outcome metrics to lists of values
        """
        results = {
            "disruption_probability": [],
            "affected_suppliers": [],
            "revenue_at_risk": []
        }
        
        for value in values:
            # Create modified scenario
            modified = DisruptionScenario(
                event_type=base_scenario.event_type,
                affected_entity_id=base_scenario.affected_entity_id,
                entity_type=base_scenario.entity_type,
                severity=value if parameter == "severity" else base_scenario.severity,
                probability=value if parameter == "probability" else base_scenario.probability,
                duration_days=int(value) if parameter == "duration_days" else base_scenario.duration_days,
                affected_skus=base_scenario.affected_skus,
                affected_regions=base_scenario.affected_regions
            )
            
            # Run simulation
            result = self.simulator.simulate(modified)
            
            results["disruption_probability"].append(result.disruption_probability)
            results["affected_suppliers"].append(result.affected_supplier_count)
            results["revenue_at_risk"].append(result.total_revenue_at_risk)
        
        return results


# Singleton instance
_simulator: Optional[MonteCarloSimulator] = None


def get_simulator(iterations: int = 1000) -> MonteCarloSimulator:
    """Get or create singleton simulator."""
    global _simulator
    if _simulator is None:
        _simulator = MonteCarloSimulator(iterations=iterations)
    return _simulator


def simulate_disruption(
    event_type: str,
    entity_id: str,
    entity_type: str,
    severity: float,
    probability: float,
    duration_days: int
) -> SimulationResult:
    """Convenience function for quick simulation."""
    simulator = get_simulator()
    
    scenario = DisruptionScenario(
        event_type=event_type,
        affected_entity_id=entity_id,
        entity_type=entity_type,
        severity=severity,
        probability=probability,
        duration_days=duration_days
    )
    
    return simulator.simulate(scenario)
