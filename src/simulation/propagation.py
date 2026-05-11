"""BFS Propagation Engine for Meridian.

Propagates disruptions through the supply chain knowledge graph using
Breadth-First Search (BFS). Calculates cascading impacts on connected entities.

Propagation follows graph relationships:
- Event -> AFFECTS -> Supplier
- Supplier -> SUPPLIES -> SKU
- Supplier -> SHIPS_VIA -> Port
- Port -> PASSES_THROUGH -> Chokepoint
- SKU -> MANUFACTURED_BY -> Supplier
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime

import structlog

from ..graph import get_neo4j_client

logger = structlog.get_logger(__name__)


@dataclass
class PropagationStep:
    """Single step in disruption propagation."""
    step_number: int
    entity_id: str
    entity_type: str
    relationship: str  # How reached (AFFECTS, SUPPLIES, etc.)
    from_entity_id: Optional[str]
    
    # Impact at this step
    impact_score: float  # 0-1
    time_delay_hours: int  # Delay from initial event
    
    # Affected SKUs/revenue
    affected_skus: List[str] = field(default_factory=list)
    revenue_impact_usd: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step": self.step_number,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "relationship": self.relationship,
            "from_entity": self.from_entity_id,
            "impact_score": round(self.impact_score, 4),
            "time_delay_hours": self.time_delay_hours,
            "affected_skus": len(self.affected_skus),
            "revenue_impact_usd": round(self.revenue_impact_usd, 2)
        }


@dataclass
class PropagationResult:
    """Result of BFS propagation."""
    source_entity_id: str
    source_entity_type: str
    initial_event_id: Optional[str]
    
    # Propagation metrics
    max_depth_reached: int
    total_entities_affected: int
    total_suppliers_affected: int
    total_skus_affected: int
    
    # Financial impact
    total_revenue_at_risk: float
    
    # Timeline
    estimated_recovery_time_days: int
    
    # Step-by-step propagation
    propagation_path: List[PropagationStep] = field(default_factory=list)
    
    # Affected entities by type
    affected_suppliers: List[str] = field(default_factory=list)
    affected_ports: List[str] = field(default_factory=list)
    affected_chokepoints: List[str] = field(default_factory=list)
    affected_skus: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": {
                "entity_id": self.source_entity_id,
                "entity_type": self.source_entity_type
            },
            "max_depth": self.max_depth_reached,
            "entities_affected": self.total_entities_affected,
            "suppliers_affected": self.total_suppliers_affected,
            "skus_affected": self.total_skus_affected,
            "revenue_at_risk": round(self.total_revenue_at_risk, 2),
            "recovery_time_days": self.estimated_recovery_time_days,
            "propagation_steps": len(self.propagation_path),
            "affected_suppliers": self.affected_suppliers[:20],  # Top 20
            "affected_skus": self.affected_skus[:50]  # Top 50
        }


class BFSPropagationEngine:
    """BFS-based disruption propagation engine.
    
    Propagates disruptions through the supply chain graph using BFS.
    Respects relationship types and applies decay/amplification rules.
    
    Usage:
        engine = BFSPropagationEngine()
        
        result = engine.propagate(
            source_entity_id="supplier-foxconn-123",
            source_entity_type="supplier",
            impact_score=0.8,
            max_depth=5
        )
        
        print(f"Suppliers affected: {result.total_suppliers_affected}")
        print(f"Revenue at risk: ${result.total_revenue_at_risk:,.0f}")
    """
    
    # Relationship propagation rules
    # Defines how impact transfers across relationship types
    PROPAGATION_RULES = {
        "AFFECTS": {"decay": 1.0, "delay_hours": 0},  # Direct impact
        "SUPPLIES": {"decay": 0.8, "delay_hours": 24},  # Supply relationship
        "SHIPS_VIA": {"decay": 0.9, "delay_hours": 48},  # Shipping
        "PASSES_THROUGH": {"decay": 0.7, "delay_hours": 72},  # Chokepoint
        "LOCATED_IN": {"decay": 0.6, "delay_hours": 12},  # Geographic
        "MANUFACTURES": {"decay": 0.85, "delay_hours": 48},  # Manufacturing
        "OPERATES_ON": {"decay": 0.75, "delay_hours": 36},  # Route operation
    }
    
    def __init__(self, max_depth: int = 5):
        """Initialize propagation engine.
        
        Args:
            max_depth: Maximum BFS depth to explore
        """
        self.max_depth = max_depth
        self.client = get_neo4j_client()
        
        self.logger = logger.bind(engine="BFSPropagationEngine")
    
    def propagate(
        self,
        source_entity_id: str,
        source_entity_type: str,
        impact_score: float = 1.0,
        initial_event_id: Optional[str] = None,
        affected_skus: Optional[List[str]] = None
    ) -> PropagationResult:
        """Propagate disruption from source entity through graph.
        
        Args:
            source_entity_id: Starting entity ID
            source_entity_type: Type of source entity
            impact_score: Initial impact severity (0-1)
            initial_event_id: Optional triggering event ID
            affected_skus: Optional list of initially affected SKUs
            
        Returns:
            PropagationResult with full impact analysis
        """
        self.logger.info(
            "starting_propagation",
            source=source_entity_id,
            impact_score=impact_score,
            max_depth=self.max_depth
        )
        
        # BFS queue: (entity_id, entity_type, depth, impact_score, delay_hours, from_entity)
        queue = deque([(
            source_entity_id,
            source_entity_type,
            0,  # depth
            impact_score,
            0,  # delay_hours
            None  # from_entity
        )])
        
        visited = set()
        propagation_steps = []
        
        affected_suppliers = set()
        affected_ports = set()
        affected_chokepoints = set()
        affected_skus = set(affected_skus or [])
        
        total_revenue = 0.0
        max_delay = 0
        
        while queue:
            entity_id, entity_type, depth, current_impact, delay, from_entity = queue.popleft()
            
            # Skip if visited or max depth reached
            if entity_id in visited or depth >= self.max_depth:
                continue
            
            # Skip if impact too low
            if current_impact < 0.1:
                continue
            
            visited.add(entity_id)
            
            # Record step
            step = PropagationStep(
                step_number=len(propagation_steps) + 1,
                entity_id=entity_id,
                entity_type=entity_type,
                relationship="AFFECTS" if depth == 0 else "PROPAGATED",
                from_entity_id=from_entity,
                impact_score=current_impact,
                time_delay_hours=delay
            )
            propagation_steps.append(step)
            
            # Track affected entities
            if entity_type == "supplier":
                affected_suppliers.add(entity_id)
                
                # Get SKUs supplied by this supplier
                skus = self._get_supplier_skus(entity_id)
                step.affected_skus = skus
                affected_skus.update(skus)
                
                # Calculate revenue impact
                revenue = self._calculate_supplier_revenue(entity_id, skus)
                step.revenue_impact_usd = revenue
                total_revenue += revenue
                
            elif entity_type == "port":
                affected_ports.add(entity_id)
            elif entity_type == "chokepoint":
                affected_chokepoints.add(entity_id)
            
            max_delay = max(max_delay, delay)
            
            # Get connected entities from Neo4j
            connections = self._get_connected_entities(entity_id, entity_type)
            
            # Add to queue
            for conn_id, conn_type, relationship in connections:
                if conn_id not in visited:
                    # Apply propagation rules
                    rule = self.PROPAGATION_RULES.get(relationship, {"decay": 0.5, "delay_hours": 48})
                    
                    new_impact = current_impact * rule["decay"]
                    new_delay = delay + rule["delay_hours"]
                    
                    queue.append((
                        conn_id,
                        conn_type,
                        depth + 1,
                        new_impact,
                        new_delay,
                        entity_id
                    ))
        
        # Calculate recovery time based on max depth and delay
        estimated_recovery = self._estimate_recovery_time(
            max_delay,
            len(affected_suppliers),
            len(affected_skus)
        )
        
        result = PropagationResult(
            source_entity_id=source_entity_id,
            source_entity_type=source_entity_type,
            initial_event_id=initial_event_id,
            max_depth_reached=max(
                [s.step_number for s in propagation_steps] + [0]
            ),
            total_entities_affected=len(visited),
            total_suppliers_affected=len(affected_suppliers),
            total_skus_affected=len(affected_skus),
            total_revenue_at_risk=total_revenue,
            estimated_recovery_time_days=estimated_recovery,
            propagation_path=propagation_steps,
            affected_suppliers=list(affected_suppliers),
            affected_ports=list(affected_ports),
            affected_chokepoints=list(affected_chokepoints),
            affected_skus=list(affected_skus)
        )
        
        self.logger.info(
            "propagation_complete",
            entities_affected=result.total_entities_affected,
            suppliers_affected=result.total_suppliers_affected,
            revenue_at_risk=result.total_revenue_at_risk
        )
        
        return result
    
    def _get_connected_entities(
        self,
        entity_id: str,
        entity_type: str
    ) -> List[Tuple[str, str, str]]:
        """Get entities connected to given entity from Neo4j.
        
        Returns:
            List of (connected_id, connected_type, relationship)
        """
        connections = []
        
        try:
            # Query depends on entity type
            if entity_type == "supplier":
                query = """
                MATCH (s:Supplier {id: $entity_id})-[r]->(connected)
                RETURN connected.id as id, labels(connected)[0] as type, type(r) as relationship
                UNION
                MATCH (connected)-[r]->(s:Supplier {id: $entity_id})
                RETURN connected.id as id, labels(connected)[0] as type, type(r) as relationship
                """
            elif entity_type == "port":
                query = """
                MATCH (p:Port {id: $entity_id})-[r]->(connected)
                RETURN connected.id as id, labels(connected)[0] as type, type(r) as relationship
                UNION
                MATCH (connected)-[r]->(p:Port {id: $entity_id})
                RETURN connected.id as id, labels(connected)[0] as type, type(r) as relationship
                """
            elif entity_type == "chokepoint":
                query = """
                MATCH (c:Chokepoint {id: $entity_id})-[r]->(connected)
                RETURN connected.id as id, labels(connected)[0] as type, type(r) as relationship
                UNION
                MATCH (connected)-[r]->(c:Chokepoint {id: $entity_id})
                RETURN connected.id as id, labels(connected)[0] as type, type(r) as relationship
                """
            else:
                return []
            
            with self.client.session() as session:
                result = session.run(query, {"entity_id": entity_id})
                
                for record in result:
                    connections.append((
                        record["id"],
                        record["type"].lower(),
                        record["relationship"]
                    ))
                    
        except Exception as e:
            self.logger.error(
                "connection_query_failed",
                entity_id=entity_id,
                error=str(e)
            )
        
        return connections
    
    def _get_supplier_skus(self, supplier_id: str) -> List[str]:
        """Get SKUs supplied by a supplier."""
        skus = []
        
        try:
            query = """
            MATCH (s:Supplier {id: $supplier_id})-[:SUPPLIES]->(sku:SKU)
            RETURN sku.id as sku_id
            """
            
            with self.client.session() as session:
                result = session.run(query, {"supplier_id": supplier_id})
                for record in result:
                    skus.append(record["sku_id"])
                    
        except Exception as e:
            self.logger.error("sku_query_failed", error=str(e))
        
        return skus
    
    def _calculate_supplier_revenue(
        self,
        supplier_id: str,
        skus: List[str]
    ) -> float:
        """Calculate revenue at risk for supplier's SKUs.
        
        In production, query actual SKU revenue data.
        For now, use synthetic model.
        """
        # Base revenue per SKU: $100K-$500K
        base_revenue_per_sku = 250000
        
        # Add variation based on number of SKUs
        # More SKUs = higher total but lower per-SKU (diversification)
        total_revenue = 0
        for i, sku in enumerate(skus):
            # Per-SKU revenue decreases with more SKUs
            sku_revenue = base_revenue_per_sku * (1 - i * 0.05)
            sku_revenue = max(50000, sku_revenue)  # Minimum $50K
            total_revenue += sku_revenue
        
        return total_revenue
    
    def _estimate_recovery_time(
        self,
        max_delay_hours: int,
        affected_suppliers: int,
        affected_skus: int
    ) -> int:
        """Estimate time to full recovery."""
        # Base recovery: max delay + buffer
        base_days = (max_delay_hours / 24) + 7
        
        # Add time per affected supplier (parallel recovery assumed)
        supplier_factor = min(affected_suppliers * 0.5, 14)
        
        # Add time per affected SKU
        sku_factor = min(affected_skus * 0.1, 21)
        
        total_days = base_days + max(supplier_factor, sku_factor)
        
        return int(total_days)
    
    def find_critical_paths(
        self,
        target_supplier_id: str,
        source_options: List[str]
    ) -> List[Dict[str, Any]]:
        """Find critical supply paths to a target supplier.
        
        Identifies chokepoints and vulnerabilities in supply chain.
        
        Args:
            target_supplier_id: Target supplier to analyze
            source_options: Potential source/entry points
            
        Returns:
            List of critical paths with risk assessment
        """
        critical_paths = []
        
        for source_id in source_options:
            # Run propagation from source
            result = self.propagate(
                source_entity_id=source_id,
                source_entity_type="chokepoint",  # Assume sources are chokepoints
                impact_score=0.5,
                max_depth=3
            )
            
            # Check if target is affected
            if target_supplier_id in result.affected_suppliers:
                # Calculate path criticality
                path_risk = self._calculate_path_risk(result, target_supplier_id)
                
                critical_paths.append({
                    "source": source_id,
                    "target": target_supplier_id,
                    "path_risk_score": path_risk,
                    "steps": [
                        s for s in result.propagation_path
                        if s.entity_id == target_supplier_id or s.from_entity_id == target_supplier_id
                    ],
                    "mitigation_priority": "HIGH" if path_risk > 0.7 else "MEDIUM"
                })
        
        # Sort by risk score
        critical_paths.sort(key=lambda x: x["path_risk_score"], reverse=True)
        
        return critical_paths
    
    def _calculate_path_risk(
        self,
        result: PropagationResult,
        target_supplier_id: str
    ) -> float:
        """Calculate risk score for a specific path."""
        # Find impact on target supplier
        target_step = None
        for step in result.propagation_path:
            if step.entity_id == target_supplier_id:
                target_step = step
                break
        
        if not target_step:
            return 0.0
        
        # Risk factors
        impact_factor = target_step.impact_score
        revenue_factor = min(target_step.revenue_impact_usd / 1000000, 1.0)
        depth_penalty = target_step.step_number * 0.05  # Deeper = slightly lower confidence
        
        risk_score = (impact_factor * 0.4 + revenue_factor * 0.5) - depth_penalty
        
        return max(0, min(1, risk_score))


# Singleton instance
_engine: Optional[BFSPropagationEngine] = None


def get_propagation_engine() -> BFSPropagationEngine:
    """Get or create singleton propagation engine."""
    global _engine
    if _engine is None:
        _engine = BFSPropagationEngine()
    return _engine


def propagate_disruption(
    source_entity_id: str,
    source_entity_type: str,
    impact_score: float = 1.0
) -> PropagationResult:
    """Convenience function for quick propagation."""
    engine = get_propagation_engine()
    return engine.propagate(source_entity_id, source_entity_type, impact_score)
