"""Knowledge graph module for Meridian.

Provides Neo4j client, models, and repositories for supply chain entities.
"""

from .client import Neo4jClient, get_neo4j_client
from .models import (
    Carrier,
    Chokepoint,
    GraphEntity,
    LocatedIn,
    Manufactures,
    OnRoute,
    OperatesOn,
    PassesThrough,
    Port,
    Region,
    Route,
    SKU,
    ShipsVia,
    Supplier,
    Supplies,
)
from .repositories.supplier_repository import (
    SupplierRepository,
    get_supplier_repository,
)

__all__ = [
    "Neo4jClient",
    "get_neo4j_client",
    "GraphEntity",
    "Supplier",
    "Port",
    "Chokepoint",
    "Region",
    "Route",
    "Carrier",
    "SKU",
    "LocatedIn",
    "ShipsVia",
    "OnRoute",
    "PassesThrough",
    "Supplies",
    "Manufactures",
    "OperatesOn",
    "SupplierRepository",
    "get_supplier_repository",
]
