"""Supplier repository for Neo4j graph operations.

Provides CRUD operations for Supplier nodes in the knowledge graph.
"""

from typing import Any, Dict, List, Optional

import structlog
from neo4j import Session

from ..client import Neo4jClient, get_neo4j_client
from ..models import Supplier

logger = structlog.get_logger(__name__)


class SupplierRepository:
    """Repository for Supplier CRUD operations in Neo4j.
    
    Usage:
        repo = SupplierRepository()
        supplier = repo.create(Supplier(name="Foxconn", country_iso="TW", ...))
        found = repo.get_by_id(supplier.id)
    """
    
    def __init__(self, client: Optional[Neo4jClient] = None):
        """Initialize repository.
        
        Args:
            client: Neo4jClient instance (uses singleton if None)
        """
        self.client = client or get_neo4j_client()
        self.logger = logger.bind(repository="SupplierRepository")
    
    def create(self, supplier: Supplier) -> Supplier:
        """Create a Supplier node in the graph.
        
        Args:
            supplier: Supplier model to create
            
        Returns:
            Created Supplier with any DB-generated fields
        """
        query = """
        CREATE (s:Supplier {
            id: $id,
            name: $name,
            country_iso: $country_iso,
            region: $region,
            tier: $tier,
            industry: $industry,
            annual_revenue_usd: $annual_revenue_usd,
            employee_count: $employee_count,
            risk_score: $risk_score,
            last_scored_at: $last_scored_at,
            city: $city,
            latitude: $latitude,
            longitude: $longitude,
            single_source_flag: $single_source_flag,
            critical_flag: $critical_flag,
            created_at: datetime(),
            updated_at: datetime(),
            raw_data: $raw_data
        })
        RETURN s
        """
        
        params = supplier.model_dump()
        
        with self.client.session() as session:
            result = session.run(query, params)
            record = result.single()
            
            if record:
                self.logger.info("supplier_created", supplier_id=supplier.id, name=supplier.name)
                return Supplier(**record["s"])
            
            raise ValueError("Failed to create supplier")
    
    def create_many(self, suppliers: List[Supplier]) -> List[Supplier]:
        """Create multiple Supplier nodes in a single transaction.
        
        Args:
            suppliers: List of Supplier models to create
            
        Returns:
            List of created Suppliers
        """
        if not suppliers:
            return []
        
        query = """
        UNWIND $suppliers AS supplier
        CREATE (s:Supplier)
        SET s = supplier
        SET s.created_at = datetime()
        SET s.updated_at = datetime()
        RETURN s
        """
        
        params = {
            "suppliers": [s.model_dump() for s in suppliers]
        }
        
        def _tx_func(tx, query: str, params: Dict):
            result = tx.run(query, params)
            return [record["s"] for record in result]
        
        with self.client.session() as session:
            records = session.execute_write(_tx_func, query, params)
            created = [Supplier(**record) for record in records]
            
            self.logger.info(
                "suppliers_created_batch",
                count=len(created),
                names=[s.name for s in created[:5]]
            )
            return created
    
    def get_by_id(self, supplier_id: str) -> Optional[Supplier]:
        """Get a Supplier by ID.
        
        Args:
            supplier_id: Supplier UUID
            
        Returns:
            Supplier if found, None otherwise
        """
        query = """
        MATCH (s:Supplier {id: $supplier_id})
        RETURN s
        """
        
        with self.client.session() as session:
            result = session.run(query, {"supplier_id": supplier_id})
            record = result.single()
            
            if record:
                return Supplier(**record["s"])
            return None
    
    def get_by_name(self, name: str, fuzzy: bool = False) -> List[Supplier]:
        """Get Suppliers by name (exact or fuzzy match).
        
        Args:
            name: Supplier name to search
            fuzzy: If True, use CONTAINS instead of exact match
            
        Returns:
            List of matching Suppliers
        """
        if fuzzy:
            query = """
            MATCH (s:Supplier)
            WHERE s.name CONTAINS $name
            RETURN s
            LIMIT 100
            """
        else:
            query = """
            MATCH (s:Supplier {name: $name})
            RETURN s
            """
        
        with self.client.session() as session:
            result = session.run(query, {"name": name})
            return [Supplier(**record["s"]) for record in result]
    
    def get_by_country(self, country_iso: str, limit: int = 100) -> List[Supplier]:
        """Get Suppliers by country.
        
        Args:
            country_iso: Two-letter country code
            limit: Maximum results
            
        Returns:
            List of Suppliers in that country
        """
        query = """
        MATCH (s:Supplier {country_iso: $country_iso})
        RETURN s
        LIMIT $limit
        """
        
        with self.client.session() as session:
            result = session.run(query, {
                "country_iso": country_iso.upper(),
                "limit": limit
            })
            return [Supplier(**record["s"]) for record in result]
    
    def get_all(self, limit: int = 1000, offset: int = 0) -> List[Supplier]:
        """Get all Suppliers with pagination.
        
        Args:
            limit: Maximum results
            offset: Skip N results
            
        Returns:
            List of Suppliers
        """
        query = """
        MATCH (s:Supplier)
        RETURN s
        ORDER BY s.name
        SKIP $offset
        LIMIT $limit
        """
        
        with self.client.session() as session:
            result = session.run(query, {"limit": limit, "offset": offset})
            return [Supplier(**record["s"]) for record in result]
    
    def update(self, supplier_id: str, updates: Dict[str, Any]) -> Optional[Supplier]:
        """Update a Supplier.
        
        Args:
            supplier_id: Supplier UUID
            updates: Dict of fields to update
            
        Returns:
            Updated Supplier if found, None otherwise
        """
        # Remove id and created_at from updates
        updates.pop("id", None)
        updates.pop("created_at", None)
        
        # Build dynamic SET clause
        set_clauses = []
        params = {"supplier_id": supplier_id}
        
        for key, value in updates.items():
            if value is not None:
                set_clauses.append(f"s.{key} = ${key}")
                params[key] = value
        
        if not set_clauses:
            return self.get_by_id(supplier_id)
        
        set_clauses.append("s.updated_at = datetime()")
        
        query = f"""
        MATCH (s:Supplier {{id: $supplier_id}})
        SET {', '.join(set_clauses)}
        RETURN s
        """
        
        with self.client.session() as session:
            result = session.run(query, params)
            record = result.single()
            
            if record:
                self.logger.info("supplier_updated", supplier_id=supplier_id)
                return Supplier(**record["s"])
            return None
    
    def delete(self, supplier_id: str) -> bool:
        """Delete a Supplier.
        
        Args:
            supplier_id: Supplier UUID
            
        Returns:
            True if deleted, False if not found
        """
        query = """
        MATCH (s:Supplier {id: $supplier_id})
        DETACH DELETE s
        RETURN count(s) as deleted
        """
        
        with self.client.session() as session:
            result = session.run(query, {"supplier_id": supplier_id})
            record = result.single()
            deleted_count = record["deleted"] if record else 0
            
            if deleted_count > 0:
                self.logger.info("supplier_deleted", supplier_id=supplier_id)
                return True
            return False
    
    def count(self) -> int:
        """Count total Suppliers.
        
        Returns:
            Total count
        """
        query = """
        MATCH (s:Supplier)
        RETURN count(s) as total
        """
        
        with self.client.session() as session:
            result = session.run(query)
            record = result.single()
            return record["total"] if record else 0
    
    def link_to_region(
        self,
        supplier_id: str,
        region_id: str,
        is_headquarters: bool = False
        ) -> bool:
        """Create LOCATED_IN relationship between Supplier and Region.
        
        Args:
            supplier_id: Supplier UUID
            region_id: Region UUID
            is_headquarters: Whether this is HQ location
            
        Returns:
            True if relationship created
        """
        query = """
        MATCH (s:Supplier {id: $supplier_id})
        MATCH (r:Region {id: $region_id})
        MERGE (s)-[rel:LOCATED_IN]->(r)
        ON CREATE SET rel.since = datetime(), rel.is_headquarters = $is_hq
        RETURN count(rel) as created
        """
        
        with self.client.session() as session:
            result = session.run(query, {
                "supplier_id": supplier_id,
                "region_id": region_id,
                "is_hq": is_headquarters
            })
            record = result.single()
            return record["created"] > 0 if record else False
    
    def link_to_port(
        self,
        supplier_id: str,
        port_id: str,
        primary: bool = False,
        volume_pct: Optional[float] = None
        ) -> bool:
        """Create SHIPS_VIA relationship between Supplier and Port.
        
        Args:
            supplier_id: Supplier UUID
            port_id: Port UUID
            primary: Whether this is primary port
            volume_pct: Percentage of volume through this port
            
        Returns:
            True if relationship created
        """
        query = """
        MATCH (s:Supplier {id: $supplier_id})
        MATCH (p:Port {id: $port_id})
        MERGE (s)-[rel:SHIPS_VIA]->(p)
        ON CREATE SET rel.primary = $primary, rel.volume_pct = $volume_pct
        RETURN count(rel) as created
        """
        
        with self.client.session() as session:
            result = session.run(query, {
                "supplier_id": supplier_id,
                "port_id": port_id,
                "primary": primary,
                "volume_pct": volume_pct
            })
            record = result.single()
            return record["created"] > 0 if record else False


# Singleton instance
_repository: Optional[SupplierRepository] = None


def get_supplier_repository() -> SupplierRepository:
    """Get or create singleton SupplierRepository.
    
    Returns:
        SupplierRepository singleton
    """
    global _repository
    if _repository is None:
        _repository = SupplierRepository()
    return _repository
