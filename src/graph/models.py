"""Pydantic models for knowledge graph entities.

These models define the structure of nodes in the Neo4j graph.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


def _coerce_neo4j_datetime(value: object) -> object:
    """Convert Neo4j temporal types to Python datetime for Pydantic."""
    if value is None:
        return value
    if hasattr(value, "to_native"):
        return value.to_native()
    return value


class GraphEntity(BaseModel):
    """Base model for all graph entities."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {"extra": "allow"}

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def parse_graph_datetimes(cls, value: object) -> object:
        return _coerce_neo4j_datetime(value)


class Supplier(GraphEntity):
    """Supplier node in the knowledge graph.
    
    Represents a company that supplies products or materials.
    """
    
    name: str
    country_iso: str = Field(..., min_length=2, max_length=2)
    region: Optional[str] = None
    tier: int = Field(default=1, ge=1, le=5)
    industry: Optional[str] = None
    annual_revenue_usd: Optional[float] = None
    employee_count: Optional[int] = None
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    last_scored_at: Optional[datetime] = None

    @field_validator("last_scored_at", mode="before")
    @classmethod
    def parse_last_scored_at(cls, value: object) -> object:
        return _coerce_neo4j_datetime(value)
    
    # Contact/address fields
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Risk flags
    single_source_flag: bool = False
    critical_flag: bool = False
    
    # Raw data for debugging
    raw_data: Optional[Dict[str, Any]] = None
    
    @field_validator('country_iso')
    @classmethod
    def uppercase_country(cls, v: str) -> str:
        """Ensure country code is uppercase."""
        return v.upper()


class Port(GraphEntity):
    """Port node in the knowledge graph.
    
    Represents a shipping port or logistics hub.
    """
    
    name: str
    locode: str = Field(..., min_length=5, max_length=5)
    country_iso: str = Field(..., min_length=2, max_length=2)
    latitude: float
    longitude: float
    throughput_teu_annual: Optional[int] = None
    congestion_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    @field_validator('country_iso')
    @classmethod
    def uppercase_country(cls, v: str) -> str:
        """Ensure country code is uppercase."""
        return v.upper()
    
    @field_validator('locode')
    @classmethod
    def uppercase_locode(cls, v: str) -> str:
        """Ensure UN/LOCODE is uppercase."""
        return v.upper()


class Chokepoint(GraphEntity):
    """Chokepoint node in the knowledge graph.
    
    Represents a geographic bottleneck in global shipping.
    Examples: Suez Canal, Panama Canal, Strait of Hormuz, Malacca Strait
    """
    
    name: str
    latitude: float
    longitude: float
    daily_vessel_count: Optional[int] = None
    annual_trade_value_usd: Optional[float] = None
    current_risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Geographic radius for impact calculation
    radius_km: float = Field(default=50.0, ge=0.0)


class Region(GraphEntity):
    """Region node in the knowledge graph.
    
    Represents a geographic/political region for risk aggregation.
    """
    
    name: str
    country_iso: str = Field(..., min_length=2, max_length=2)
    stability_index: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    conflict_active: bool = False
    sanctions_active: bool = False
    
    @field_validator('country_iso')
    @classmethod
    def uppercase_country(cls, v: str) -> str:
        """Ensure country code is uppercase."""
        return v.upper()


class Route(GraphEntity):
    """Route node in the knowledge graph.
    
    Represents a shipping route between regions.
    """
    
    name: str
    origin_region: str
    destination_region: str
    avg_transit_days: Optional[int] = None
    avg_cost_per_container_usd: Optional[float] = None


class Carrier(GraphEntity):
    """Carrier node in the knowledge graph.
    
    Represents a shipping carrier or logistics provider.
    """
    
    name: str
    country_iso: Optional[str] = Field(default=None, min_length=2, max_length=2)
    fleet_size: Optional[int] = None
    market_share_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    
    @field_validator('country_iso')
    @classmethod
    def uppercase_country(cls, v: Optional[str]) -> Optional[str]:
        """Ensure country code is uppercase."""
        if v:
            return v.upper()
        return v


class SKU(GraphEntity):
    """SKU (Stock Keeping Unit) node in the knowledge graph.
    
    Represents a product or material that suppliers manufacture.
    """
    
    name: str
    hs_code: Optional[str] = None
    category: Optional[str] = None
    owner_org: Optional[str] = None
    critical_flag: bool = False


# Relationship models (for type safety)

class LocatedIn(BaseModel):
    """Relationship: Supplier -[LOCATED_IN]-> Region/Port"""
    since: Optional[datetime] = None
    is_headquarters: bool = False


class ShipsVia(BaseModel):
    """Relationship: Supplier -[SHIPS_VIA]-> Port/Chokepoint"""
    primary: bool = False
    volume_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)


class OnRoute(BaseModel):
    """Relationship: Port -[ON_ROUTE]-> Route"""
    sequence: int = Field(ge=0)
    is_origin: bool = False
    is_destination: bool = False


class PassesThrough(BaseModel):
    """Relationship: Route -[PASSES_THROUGH]-> Chokepoint"""
    sequence: int = Field(ge=0)
    is_optional: bool = False


class Supplies(BaseModel):
    """Relationship: Supplier -[SUPPLIES]-> Supplier (tier relationship)"""
    tier: int = Field(ge=1, le=5)
    annual_value_usd: Optional[float] = None
    product_categories: Optional[List[str]] = None


class Manufactures(BaseModel):
    """Relationship: Supplier -[MANUFACTURES]-> SKU"""
    sku_count: Optional[int] = None
    is_primary: bool = False


class OperatesOn(BaseModel):
    """Relationship: Carrier -[OPERATES_ON]-> Route"""
    frequency_per_week: Optional[int] = None
    capacity_teus: Optional[int] = None
