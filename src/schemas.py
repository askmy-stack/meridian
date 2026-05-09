"""Pydantic schemas for all Meridian data models."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class GeoLocation(BaseModel):
    """Geographic coordinates."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class ConflictEvent(BaseModel):
    """Schema for conflict/violence events from ACLED, GDELT."""
    event_id: str
    timestamp: datetime
    source: str = Field(..., description="Data source: gdelt, acled")
    event_type: str = Field(..., description="Type: conflict, protest, riot, etc.")
    
    # Location
    location: GeoLocation
    country: str
    region: str
    city: Optional[str] = None
    
    # Event details
    description: str
    actors: List[str] = Field(default_factory=list)
    fatalities: int = Field(default=0, ge=0)
    
    # Metadata
    event_date: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Raw source data (for debugging)
    raw_data: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "gdelt_123456",
                "timestamp": "2024-01-15T10:30:00Z",
                "source": "gdelt",
                "event_type": "conflict",
                "location": {"latitude": 31.5, "longitude": 34.5},
                "country": "Israel",
                "region": "Middle East",
                "description": "Military activity in Gaza Strip",
                "actors": ["IDF", "Hamas"],
                "fatalities": 0,
                "event_date": "2024-01-15T10:30:00Z"
            }
        }


class VesselEvent(BaseModel):
    """Schema for AIS vessel tracking events."""
    event_id: str
    timestamp: datetime
    source: str = "aishub"
    event_type: str = Field(..., description="Type: position, port_call, deviation")
    
    # Vessel identification
    mmsi: str
    imo: Optional[str] = None
    vessel_name: Optional[str] = None
    vessel_type: Optional[str] = None
    
    # Location
    location: GeoLocation
    heading: Optional[float] = None
    speed: Optional[float] = Field(None, ge=0)
    
    # Route context
    origin_port: Optional[str] = None
    destination_port: Optional[str] = None
    eta: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    raw_data: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "ais_789012",
                "timestamp": "2024-01-15T10:30:00Z",
                "source": "aishub",
                "event_type": "position",
                "mmsi": "123456789",
                "vessel_name": "MSC OSCAR",
                "location": {"latitude": 30.0, "longitude": 32.5},
                "heading": 180.0,
                "speed": 12.5
            }
        }


class WeatherEvent(BaseModel):
    """Schema for weather/disaster events from NOAA, NASA FIRMS."""
    event_id: str
    timestamp: datetime
    source: str = Field(..., description="Data source: noaa, nasa_firms")
    event_type: str = Field(..., description="Type: storm, flood, fire, hurricane")
    
    # Location
    location: GeoLocation
    country: str
    region: str
    
    # Event details
    description: str
    severity: str = Field(..., description="low, medium, high, extreme")
    affected_area_km2: Optional[float] = None
    
    # Time bounds
    start_date: datetime
    end_date: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    raw_data: Optional[Dict[str, Any]] = None


class SanctionEvent(BaseModel):
    """Schema for sanctions data from OpenSanctions."""
    event_id: str
    timestamp: datetime
    source: str = "opensanctions"
    event_type: str = "sanction"
    
    # Entity being sanctioned
    entity_name: str
    entity_type: str = Field(..., description="person, company, vessel, aircraft")
    
    # Sanction details
    sanctioning_authority: str
    sanction_program: str
    effective_date: datetime
    
    # Scope
    countries_affected: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    raw_data: Optional[Dict[str, Any]] = None


class MeridianEvent(BaseModel):
    """Universal wrapper for all Meridian events."""
    topic: str = Field(..., description="Kafka topic: meridian.{source}.{type}")
    partition: Optional[int] = None
    offset: Optional[int] = None
    
    # The actual event payload
    payload: Dict[str, Any]
    
    # Processing metadata
    received_at: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = False
    processing_errors: List[str] = Field(default_factory=list)
