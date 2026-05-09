"""Tests for Pydantic schemas."""
import pytest
from datetime import datetime

from src.schemas import (
    GeoLocation,
    ConflictEvent,
    VesselEvent,
    WeatherEvent,
    SanctionEvent,
)


class TestGeoLocation:
    """Tests for GeoLocation schema."""
    
    def test_valid_coordinates(self):
        """Test valid latitude and longitude."""
        loc = GeoLocation(latitude=31.5, longitude=34.5)
        assert loc.latitude == 31.5
        assert loc.longitude == 34.5
    
    def test_invalid_latitude(self):
        """Test latitude out of range."""
        with pytest.raises(ValueError):
            GeoLocation(latitude=95, longitude=0)
    
    def test_invalid_longitude(self):
        """Test longitude out of range."""
        with pytest.raises(ValueError):
            GeoLocation(latitude=0, longitude=200)


class TestConflictEvent:
    """Tests for ConflictEvent schema."""
    
    def test_valid_conflict_event(self):
        """Test creating a valid conflict event."""
        event = ConflictEvent(
            event_id="gdelt_123",
            timestamp=datetime.utcnow(),
            source="gdelt",
            event_type="conflict",
            location=GeoLocation(latitude=31.5, longitude=34.5),
            country="Israel",
            region="Middle East",
            description="Test conflict event",
            actors=["Actor1", "Actor2"],
            fatalities=10,
            event_date=datetime.utcnow()
        )
        assert event.event_id == "gdelt_123"
        assert event.fatalities == 10
        assert len(event.actors) == 2
    
    def test_default_fatalities(self):
        """Test that fatalities defaults to 0."""
        event = ConflictEvent(
            event_id="test_1",
            timestamp=datetime.utcnow(),
            source="test",
            event_type="conflict",
            location=GeoLocation(latitude=0, longitude=0),
            country="Test",
            region="Test",
            description="Test",
            event_date=datetime.utcnow()
        )
        assert event.fatalities == 0
    
    def test_negative_fatalities_rejected(self):
        """Test that negative fatalities are rejected."""
        with pytest.raises(ValueError):
            ConflictEvent(
                event_id="test_1",
                timestamp=datetime.utcnow(),
                source="test",
                event_type="conflict",
                location=GeoLocation(latitude=0, longitude=0),
                country="Test",
                region="Test",
                description="Test",
                fatalities=-5,
                event_date=datetime.utcnow()
            )


class TestVesselEvent:
    """Tests for VesselEvent schema."""
    
    def test_valid_vessel_event(self):
        """Test creating a valid vessel event."""
        event = VesselEvent(
            event_id="ais_123",
            timestamp=datetime.utcnow(),
            source="aishub",
            event_type="position",
            mmsi="123456789",
            imo="9876543",
            vessel_name="MSC OSCAR",
            vessel_type="Container",
            location=GeoLocation(latitude=30.0, longitude=32.5),
            heading=180.0,
            speed=12.5
        )
        assert event.mmsi == "123456789"
        assert event.speed == 12.5
    
    def test_speed_non_negative(self):
        """Test that negative speed is rejected."""
        with pytest.raises(ValueError):
            VesselEvent(
                event_id="ais_123",
                timestamp=datetime.utcnow(),
                source="aishub",
                event_type="position",
                mmsi="123456789",
                location=GeoLocation(latitude=0, longitude=0),
                speed=-5
            )


class TestWeatherEvent:
    """Tests for WeatherEvent schema."""
    
    def test_valid_weather_event(self):
        """Test creating a valid weather event."""
        event = WeatherEvent(
            event_id="noaa_123",
            timestamp=datetime.utcnow(),
            source="noaa",
            event_type="hurricane",
            location=GeoLocation(latitude=25.0, longitude=-80.0),
            country="United States",
            region="Florida",
            description="Hurricane approaching coast",
            severity="extreme",
            start_date=datetime.utcnow()
        )
        assert event.severity == "extreme"
        assert event.event_type == "hurricane"


class TestSanctionEvent:
    """Tests for SanctionEvent schema."""
    
    def test_valid_sanction_event(self):
        """Test creating a valid sanction event."""
        event = SanctionEvent(
            event_id="sanction_123",
            timestamp=datetime.utcnow(),
            entity_name="Example Corp",
            entity_type="company",
            sanctioning_authority="US Treasury",
            sanction_program="SDN",
            effective_date=datetime.utcnow(),
            countries_affected=["Russia", "China"]
        )
        assert event.entity_type == "company"
        assert len(event.countries_affected) == 2
