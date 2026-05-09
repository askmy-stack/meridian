"""ACLED data producer - requires free API key."""
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from ..schemas import ConflictEvent, GeoLocation
from .base import BaseProducer


class ACLEDProducer(BaseProducer):
    """Producer for ACLED (Armed Conflict Location & Event Data).
    
    ACLED provides curated conflict event data with precise locations and fatalities.
    Requires free API key from: https://acleddata.com/
    
    API Documentation: https://acleddata.com/acleddatanew/wp-content/uploads/dlm_uploads/2022/11/ACLED-API-User-Guide_11.22.pdf
    """
    
    ACLED_API = "https://api.acleddata.com/acled/read"
    
    # Event type mapping from ACLED to Meridian taxonomy
    EVENT_TYPE_MAP = {
        'Battles': 'conflict',
        'Violence against civilians': 'violence',
        'Protests': 'protest',
        'Riots': 'riot',
        'Strategic developments': 'strategic',
        'Explosions/Remote violence': 'explosions',
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
        bootstrap_servers: Optional[str] = None,
        max_retries: int = 3
    ):
        super().__init__(
            bootstrap_servers=bootstrap_servers,
            source_name="acled",
            max_retries=max_retries
        )
        
        self.api_key = api_key or os.getenv("ACLED_API_KEY")
        self.email = email or os.getenv("ACLED_EMAIL")
        
        if not self.api_key or not self.email:
            self.logger.warning(
                "acled_credentials_missing",
                has_key=bool(self.api_key),
                has_email=bool(self.email)
            )
    
    def _event_to_schema(self, event: Dict[str, Any]) -> Optional[ConflictEvent]:
        """Convert ACLED event JSON to ConflictEvent."""
        try:
            # Parse coordinates
            lat = event.get('latitude')
            lon = event.get('longitude')
            
            if lat is None or lon is None:
                return None
            
            lat_f = float(lat)
            lon_f = float(lon)
            
            # Parse date
            event_date_str = event.get('event_date', '')
            if event_date_str:
                try:
                    event_date = datetime.strptime(event_date_str, '%Y-%m-%d')
                except ValueError:
                    event_date = datetime.utcnow()
            else:
                event_date = datetime.utcnow()
            
            # Get actors
            actors = []
            actor1 = event.get('actor1', '').strip()
            actor2 = event.get('actor2', '').strip()
            assoc_actor_1 = event.get('assoc_actor_1', '').strip()
            assoc_actor_2 = event.get('assoc_actor_2', '').strip()
            
            if actor1:
                actors.append(actor1)
            if actor2:
                actors.append(actor2)
            if assoc_actor_1:
                actors.append(assoc_actor_1)
            if assoc_actor_2:
                actors.append(assoc_actor_2)
            
            # Clean up actors list
            actors = list(set([a for a in actors if a]))
            
            # Parse fatalities
            fatalities = event.get('fatalities', 0)
            try:
                fatalities = int(fatalities)
            except (ValueError, TypeError):
                fatalities = 0
            
            # Map event type
            acled_type = event.get('event_type', 'Unknown')
            event_type = self.EVENT_TYPE_MAP.get(acled_type, 'other')
            
            # Build description
            notes = event.get('notes', '')
            sub_event_type = event.get('sub_event_type', '')
            description = f"{acled_type}: {sub_event_type}. {notes}"
            
            return ConflictEvent(
                event_id=f"acled_{event.get('event_id', 'unknown')}",
                timestamp=datetime.utcnow(),
                source="acled",
                event_type=event_type,
                location=GeoLocation(latitude=lat_f, longitude=lon_f),
                country=event.get('country', 'Unknown'),
                region=event.get('region', 'Unknown'),
                city=event.get('location', None),
                description=description[:500],  # Truncate long descriptions
                actors=actors,
                fatalities=fatalities,
                event_date=event_date,
                raw_data=event
            )
            
        except Exception as e:
            self.logger.warning(
                "acled_parse_error",
                error=str(e),
                event_id=event.get('event_id')
            )
            return None
    
    def _fetch_page(
        self,
        start_date: str,
        end_date: str,
        page: int = 1,
        countries: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Fetch a single page of ACLED data."""
        if not self.api_key or not self.email:
            self.logger.error("acled_credentials_not_configured")
            return []
        
        params = {
            'key': self.api_key,
            'email': self.email,
            'event_date': f"{start_date}|{end_date}",
            'event_date_where': 'BETWEEN',
            'page': page,
            'format': 'json'
        }
        
        if countries:
            # ACLED uses ISO3 or country names
            params['country'] = ','.join(countries)
        
        try:
            response = requests.get(
                self.ACLED_API,
                params=params,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', [])
            
        except requests.exceptions.RequestException as e:
            self.logger.error("acled_api_error", error=str(e), page=page)
            return []
        except Exception as e:
            self.logger.error("acled_parse_error", error=str(e), page=page)
            return []
    
    def fetch_and_publish(
        self,
        days_back: int = 7,
        countries: Optional[List[str]] = None,
        batch_size: int = 500,
        **kwargs: Any
    ) -> int:
        """Fetch ACLED data and publish to Kafka.
        
        Args:
            days_back: Number of days of historical data to fetch
            countries: Filter by country names (ACLED format)
            batch_size: Events per API page
            
        Returns:
            Number of events published
        """
        self.connect()
        
        if not self.api_key or not self.email:
            self.logger.error("cannot_fetch_acled_credentials_missing")
            return 0
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        self.logger.info(
            "fetching_acled",
            start_date=start_str,
            end_date=end_str,
            countries=countries
        )
        
        total_published = 0
        page = 1
        max_pages = 100  # Safety limit
        
        while page <= max_pages:
            events = self._fetch_page(start_str, end_str, page, countries)
            
            if not events:
                break
            
            page_published = 0
            for event in events:
                schema_event = self._event_to_schema(event)
                
                if not schema_event:
                    continue
                
                success = self.send_event(
                    event=schema_event,
                    event_type=schema_event.event_type,
                    key=schema_event.event_id
                )
                
                if success:
                    page_published += 1
            
            total_published += page_published
            
            self.logger.info(
                "acled_page_processed",
                page=page,
                events_in_page=len(events),
                published=page_published,
                total_published=total_published
            )
            
            # If we got fewer events than expected, we've reached the end
            if len(events) < batch_size:
                break
            
            page += 1
        
        self.flush()
        
        self.logger.info(
            "acled_fetch_complete",
            total_published=total_published,
            pages_processed=page
        )
        
        return total_published
    
    def fetch_live_events(
        self,
        countries: Optional[List[str]] = None,
        **kwargs: Any
    ) -> int:
        """Fetch recent events (last 24 hours) for live monitoring.
        
        Returns:
            Number of events published
        """
        return self.fetch_and_publish(days_back=1, countries=countries, **kwargs)
