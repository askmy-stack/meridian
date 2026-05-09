"""GDELT Project data producer - no API key required."""
import csv
import gzip
from datetime import datetime, timedelta
from io import StringIO
from typing import Any, Dict, List, Optional

import requests
from dateutil import parser as date_parser

from ..schemas import ConflictEvent, GeoLocation
from .base import BaseProducer


class GDELTProducer(BaseProducer):
    """Producer for GDELT (Global Database of Events, Language, and Tone).
    
    GDELT provides real-time global news event data. No API key required.
    Documentation: https://www.gdeltproject.org/
    
    Uses the GDELT 2.0 Events API which returns CSV data.
    """
    
    GDELT_URL = "http://data.gdeltproject.org/gdeltv2/{}.export.CSV.zip"
    GDELT_LAST_UPDATE = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
    
    # CAMEO code to event type mapping (simplified)
    CONFLICT_CODES = {
        '01': 'make_statement',
        '02': 'yield',
        '03': 'disapprove',
        '04': 'reject',
        '05': 'threaten',
        '06': 'protest',
        '07': 'coerce',
        '08': 'assault',
        '09': 'fight',
        '10': 'use_force',
        '11': 'mass_violence',
        '13': 'threaten_conflict',
        '14': 'protest_violence',
        '15': 'conflict',
        '16': 'fight_conflict',
        '17': 'violence_conflict',
        '18': 'assault_conflict',
        '19': 'force_conflict',
        '20': 'mass_violence_conflict',
    }
    
    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        max_retries: int = 3
    ):
        super().__init__(
            bootstrap_servers=bootstrap_servers,
            source_name="gdelt",
            max_retries=max_retries
        )
    
    def _parse_cameo_code(self, code: str) -> str:
        """Convert CAMEO event code to human-readable type."""
        if not code:
            return "unknown"
        
        # Get first 2 digits for category
        category = code[:2]
        return self.CONFLICT_CODES.get(category, "other")
    
    def _row_to_event(self, row: Dict[str, str]) -> Optional[ConflictEvent]:
        """Convert GDELT CSV row to ConflictEvent."""
        try:
            # Extract coordinates
            lat = row.get('ActionGeo_Lat')
            lon = row.get('ActionGeo_Long')
            
            if not lat or not lon or lat == '' or lon == '':
                return None
                
            lat_f = float(lat)
            lon_f = float(lon)
            
            # Skip invalid coordinates (GDELT uses 0,0 for unknown)
            if lat_f == 0 and lon_f == 0:
                return None
            
            # Parse timestamp
            sqldate = row.get('SQLDATE', '')
            if len(sqldate) == 8:
                event_date = datetime.strptime(sqldate, '%Y%m%d')
            else:
                event_date = datetime.utcnow()
            
            # Extract actors
            actors = []
            actor1 = row.get('Actor1Name', '').strip()
            actor2 = row.get('Actor2Name', '').strip()
            if actor1:
                actors.append(actor1)
            if actor2:
                actors.append(actor2)
            
            # Extract country from country code
            country_code = row.get('ActionGeo_CountryCode', 'Unknown')
            country_map = {
                'US': 'United States',
                'CN': 'China',
                'RU': 'Russia',
                'UA': 'Ukraine',
                'IL': 'Israel',
                'PS': 'Palestine',
                'IR': 'Iran',
                'IQ': 'Iraq',
                'SY': 'Syria',
                'YE': 'Yemen',
            }
            country = country_map.get(country_code, country_code)
            
            # Build description from source text
            source_url = row.get('SOURCEURL', '')
            description = f"News event from {source_url}"
            
            # Parse Goldstein intensity for severity estimate
            goldstein = row.get('GoldsteinScale', '0')
            try:
                goldstein_score = float(goldstein)
            except (ValueError, TypeError):
                goldstein_score = 0
            
            return ConflictEvent(
                event_id=f"gdelt_{row.get('GLOBALEVENTID', 'unknown')}",
                timestamp=datetime.utcnow(),
                source="gdelt",
                event_type=self._parse_cameo_code(row.get('EventCode', '')),
                location=GeoLocation(latitude=lat_f, longitude=lon_f),
                country=country,
                region=row.get('ActionGeo_FullName', 'Unknown'),
                city=None,
                description=description,
                actors=actors,
                fatalities=0,  # GDELT doesn't provide fatality counts directly
                event_date=event_date,
                raw_data=dict(row)
            )
            
        except Exception as e:
            self.logger.warning("row_parse_error", error=str(e), row=row.get('GLOBALEVENTID'))
            return None
    
    def _download_latest(self) -> List[Dict[str, str]]:
        """Download latest GDELT data."""
        # Get the current timestamp for latest file
        now = datetime.utcnow()
        timestamp = now.strftime('%Y%m%d%H%M%S')
        
        url = self.GDELT_URL.format(timestamp[:-2] + '00')  # Round to hour
        
        self.logger.info("downloading_gdelt", url=url)
        
        try:
            response = requests.get(url, timeout=60)
            if response.status_code != 200:
                # Try 15 minutes ago
                past = now - timedelta(minutes=15)
                timestamp = past.strftime('%Y%m%d%H%M%S')
                url = self.GDELT_URL.format(timestamp[:-2] + '00')
                response = requests.get(url, timeout=60)
                
            if response.status_code != 200:
                self.logger.warning("gdelt_download_failed", status_code=response.status_code)
                return []
            
            # Decompress zip
            from io import BytesIO
            import zipfile
            
            with zipfile.ZipFile(BytesIO(response.content)) as z:
                # Find CSV file
                csv_name = [n for n in z.namelist() if n.endswith('.csv')][0]
                with z.open(csv_name) as f:
                    content = gzip.decompress(f.read()).decode('utf-8', errors='ignore')
            
            # Parse CSV
            reader = csv.DictReader(StringIO(content), delimiter='\t')
            return list(reader)
            
        except Exception as e:
            self.logger.error("gdelt_download_error", error=str(e))
            return []
    
    def fetch_and_publish(
        self,
        hours_back: int = 1,
        event_types: Optional[List[str]] = None,
        **kwargs: Any
    ) -> int:
        """Fetch latest GDELT events and publish to Kafka.
        
        Args:
            hours_back: How many hours of data to fetch
            event_types: Filter by event types (if None, all conflict events)
            
        Returns:
            Number of events published
        """
        self.connect()
        
        rows = self._download_latest()
        
        if not rows:
            self.logger.info("no_gdelt_data")
            return 0
        
        self.logger.info("gdelt_data_downloaded", row_count=len(rows))
        
        published = 0
        for row in rows:
            event = self._row_to_event(row)
            
            if not event:
                continue
            
            # Filter by event type if specified
            if event_types and event.event_type not in event_types:
                continue
            
            # Only send conflict-related events
            if event.event_type not in ['conflict', 'protest', 'fight', 'assault', 'mass_violence']:
                continue
            
            success = self.send_event(
                event=event,
                event_type=event.event_type,
                key=event.event_id
            )
            
            if success:
                published += 1
        
        self.flush()
        
        self.logger.info(
            "gdelt_publish_complete",
            total_rows=len(rows),
            published=published
        )
        
        return published
    
    def fetch_by_date(
        self,
        date: datetime,
        **kwargs: Any
    ) -> int:
        """Fetch GDELT data for a specific date (for backtesting).
        
        Args:
            date: Date to fetch data for
            
        Returns:
            Number of events published
        """
        self.connect()
        
        # Format: YYYYMMDD
        date_str = date.strftime('%Y%m%d')
        url = f"http://data.gdeltproject.org/events/{date_str}.export.CSV.zip"
        
        self.logger.info("downloading_gdelt_historical", date=date_str, url=url)
        
        try:
            response = requests.get(url, timeout=120)
            if response.status_code != 200:
                self.logger.warning("historical_download_failed", status_code=response.status_code)
                return 0
            
            from io import BytesIO
            import zipfile
            
            with zipfile.ZipFile(BytesIO(response.content)) as z:
                csv_name = [n for n in z.namelist() if n.endswith('.csv')][0]
                with z.open(csv_name) as f:
                    content = gzip.decompress(f.read()).decode('utf-8', errors='ignore')
            
            reader = csv.DictReader(StringIO(content), delimiter='\t')
            rows = list(reader)
            
            published = 0
            for row in rows:
                event = self._row_to_event(row)
                if event and event.event_type in ['conflict', 'protest', 'fight', 'assault']:
                    if self.send_event(event, event.event_type, key=event.event_id):
                        published += 1
            
            self.flush()
            
            self.logger.info(
                "historical_publish_complete",
                date=date_str,
                total_rows=len(rows),
                published=published
            )
            
            return published
            
        except Exception as e:
            self.logger.error("historical_download_error", error=str(e))
            return 0
