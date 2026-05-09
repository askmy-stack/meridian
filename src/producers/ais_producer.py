"""AIS vessel tracking data producer - AISHub free tier."""
import os
import socket
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from ..schemas import GeoLocation, VesselEvent
from .base import BaseProducer


class AISProducer(BaseProducer):
    """Producer for AIS (Automatic Identification System) vessel tracking.
    
    AISHub free tier provides real-time vessel positions via TCP socket stream
    or REST API. Requires free account: https://www.aishub.net/
    
    Supports:
    - REST API polling for vessel positions
    - TCP socket streaming (NMEA sentences)
    - Port arrival/departure detection
    """
    
    AISHUB_API = "https://data.aishub.net/ws.php"
    AISHUB_TCP_HOST = "data.aishub.net"
    AISHUB_TCP_PORT = 4001  # Free tier port
    
    # Major shipping chokepoints for filtering
    CHOKEPOINTS = {
        'suez_canal': {'lat': 30.0, 'lon': 32.5, 'radius_nm': 50},
        'panama_canal': {'lat': 9.0, 'lon': -79.5, 'radius_nm': 30},
        'strait_of_hormuz': {'lat': 26.5, 'lon': 56.5, 'radius_nm': 50},
        'strait_of_malacca': {'lat': 1.5, 'lon': 103.0, 'radius_nm': 60},
        'bab_el_mandeb': {'lat': 12.5, 'lon': 43.5, 'radius_nm': 40},
        'turkish_straits': {'lat': 41.2, 'lon': 29.0, 'radius_nm': 30},
        'english_channel': {'lat': 50.5, 'lon': -1.0, 'radius_nm': 40},
    }
    
    # Vessel types relevant to supply chain
    SUPPLY_CHAIN_VESSELS = {
        'Cargo',
        'Tanker',
        'Container',
        'Bulk Carrier',
        'General Cargo',
        'Passenger',
        'Ferry',
    }
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        bootstrap_servers: Optional[str] = None,
        use_tcp_stream: bool = False,
        max_retries: int = 3
    ):
        super().__init__(
            bootstrap_servers=bootstrap_servers,
            source_name="aishub",
            max_retries=max_retries
        )
        
        self.username = username or os.getenv("AISHUB_USERNAME")
        self.password = password or os.getenv("AISHUB_PASSWORD")
        self.use_tcp_stream = use_tcp_stream
        
        self._tcp_socket: Optional[socket.socket] = None
        
        if not self.username or not self.password:
            self.logger.warning(
                "aishub_credentials_missing",
                has_username=bool(self.username),
                has_password=bool(self.password)
            )
    
    def _parse_nmea(self, sentence: str) -> Optional[Dict[str, Any]]:
        """Parse NMEA 0183 AIS sentence."""
        # Basic parsing for AIVDM/AIVDO messages
        if not sentence.startswith('!AIVDM') and not sentence.startswith('!AIVDO'):
            return None
        
        try:
            parts = sentence.split(',')
            if len(parts) < 7:
                return None
            
            # Extract message type and payload
            # This is a simplified parser - full AIS decoding requires bit manipulation
            msg_type = int(parts[1])  # Fragment count
            payload = parts[5]  # Encoded AIS payload
            
            # For full decoding, we'd need libais or similar
            # This is a placeholder for the structure
            return {
                'raw_sentence': sentence,
                'fragment_count': msg_type,
                'payload': payload,
                'parsed': False
            }
            
        except Exception as e:
            self.logger.debug("nmea_parse_error", error=str(e), sentence=sentence[:50])
            return None
    
    def _api_response_to_event(self, vessel: Dict[str, Any]) -> Optional[VesselEvent]:
        """Convert AISHub API response to VesselEvent."""
        try:
            # Extract position
            lat = vessel.get('LATITUDE')
            lon = vessel.get('LONGITUDE')
            
            if lat is None or lon is None:
                return None
            
            try:
                lat_f = float(lat)
                lon_f = float(lon)
            except (ValueError, TypeError):
                return None
            
            # Parse timestamp
            timestamp_str = vessel.get('TIME', '')
            if timestamp_str:
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    timestamp = datetime.utcnow()
            else:
                timestamp = datetime.utcnow()
            
            # Get vessel details
            mmsi = str(vessel.get('MMSI', ''))
            if not mmsi:
                return None
            
            vessel_name = vessel.get('SHIPNAME', '').strip() or None
            vessel_type = vessel.get('TYPE_NAME', '').strip() or None
            imo = vessel.get('IMO', '').strip() or None
            
            # Speed and heading
            try:
                speed = float(vessel.get('SOG', 0)) if vessel.get('SOG') else None
            except (ValueError, TypeError):
                speed = None
            
            try:
                heading = float(vessel.get('HEADING', 0)) if vessel.get('HEADING') else None
            except (ValueError, TypeError):
                heading = None
            
            # Destination
            destination = vessel.get('DESTINATION', '').strip() or None
            eta = vessel.get('ETA', '').strip() or None
            
            # Determine event type based on context
            event_type = 'position'
            if speed is not None and speed < 1:
                event_type = 'port_call'  # Likely at anchor
            
            # Check if in chokepoint
            in_chokepoint = None
            for name, coords in self.CHOKEPOINTS.items():
                distance = self._haversine_distance(
                    lat_f, lon_f, coords['lat'], coords['lon']
                )
                if distance <= coords['radius_nm']:
                    in_chokepoint = name
                    event_type = 'chokepoint_transit'
                    break
            
            return VesselEvent(
                event_id=f"ais_{mmsi}_{int(timestamp.timestamp())}",
                timestamp=timestamp,
                source="aishub",
                event_type=event_type,
                mmsi=mmsi,
                imo=imo,
                vessel_name=vessel_name,
                vessel_type=vessel_type,
                location=GeoLocation(latitude=lat_f, longitude=lon_f),
                heading=heading,
                speed=speed,
                origin_port=None,  # Not always available
                destination_port=destination,
                eta=eta,
                raw_data={
                    **vessel,
                    'in_chokepoint': in_chokepoint
                }
            )
            
        except Exception as e:
            self.logger.warning(
                "ais_parse_error",
                error=str(e),
                vessel=vessel.get('MMSI')
            )
            return None
    
    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """Calculate distance between two points in nautical miles."""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 3440.065  # Earth radius in nautical miles
        
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)
        
        a = sin(delta_lat / 2) ** 2 + \
            cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c
    
    def _fetch_api_data(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Fetch vessel data from AISHub REST API."""
        if not self.username:
            self.logger.error("aishub_username_not_configured")
            return []
        
        params = {
            'username': self.username,
            'format': 'json',
            'output': 'vessels',
            'compress': '0',
        }
        
        if bbox:
            # min_lat, min_lon, max_lat, max_lon
            params['latmin'] = bbox[0]
            params['lonmin'] = bbox[1]
            params['latmax'] = bbox[2]
            params['lonmax'] = bbox[3]
        
        try:
            response = requests.get(
                self.AISHUB_API,
                params=params,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            
            # AISHub returns list of vessel objects
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'vessels' in data:
                return data['vessels']
            else:
                return []
                
        except requests.exceptions.RequestException as e:
            self.logger.error("aishub_api_error", error=str(e))
            return []
        except Exception as e:
            self.logger.error("aishub_parse_error", error=str(e))
            return []
    
    def fetch_and_publish(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        filter_chokepoints: bool = True,
        vessel_types: Optional[List[str]] = None,
        **kwargs: Any
    ) -> int:
        """Fetch AIS data and publish to Kafka.
        
        Args:
            bbox: (min_lat, min_lon, max_lat, max_lon) bounding box
            filter_chokepoints: Only publish vessels near major chokepoints
            vessel_types: Filter by vessel type
            
        Returns:
            Number of events published
        """
        self.connect()
        
        # If filtering by chokepoints, build bbox around them
        if filter_chokepoints and not bbox:
            # Rough bbox for all major chokepoints
            bbox = (-10, -85, 45, 120)  # Covers Panama to Malacca
        
        vessels = self._fetch_api_data(bbox=bbox)
        
        if not vessels:
            self.logger.info("no_ais_data")
            return 0
        
        self.logger.info("aishub_data_downloaded", vessel_count=len(vessels))
        
        published = 0
        for vessel in vessels:
            # Filter by vessel type if specified
            if vessel_types:
                vessel_type = vessel.get('TYPE_NAME', '')
                if not any(vt in vessel_type for vt in vessel_types):
                    continue
            
            # If filtering chokepoints, check if vessel is near one
            if filter_chokepoints:
                lat = vessel.get('LATITUDE')
                lon = vessel.get('LONGITUDE')
                if lat is None or lon is None:
                    continue
                
                in_chokepoint = False
                for name, coords in self.CHOKEPOINTS.items():
                    distance = self._haversine_distance(
                        float(lat), float(lon), coords['lat'], coords['lon']
                    )
                    if distance <= coords['radius_nm']:
                        in_chokepoint = True
                        break
                
                if not in_chokepoint:
                    continue
            
            event = self._api_response_to_event(vessel)
            
            if not event:
                continue
            
            success = self.send_event(
                event=event,
                event_type=event.event_type,
                key=event.mmsi
            )
            
            if success:
                published += 1
        
        self.flush()
        
        self.logger.info(
            "ais_publish_complete",
            total_vessels=len(vessels),
            published=published
        )
        
        return published
    
    def stream_tcp(
        self,
        duration_seconds: int = 60,
        **kwargs: Any
    ) -> int:
        """Stream NMEA data from AISHub TCP socket.
        
        Note: This is a simplified implementation. Production would use
        a separate async process with proper NMEA decoding.
        
        Args:
            duration_seconds: How long to stream for
            
        Returns:
            Number of raw messages received (not all are published)
        """
        if not self.username or not self.password:
            self.logger.error("tcp_credentials_required")
            return 0
        
        self.connect()
        
        self.logger.info(
            "starting_tcp_stream",
            host=self.AISHUB_TCP_HOST,
            port=self.AISHUB_TCP_PORT,
            duration=duration_seconds
        )
        
        messages_received = 0
        
        try:
            self._tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._tcp_socket.settimeout(10)
            self._tcp_socket.connect((self.AISHUB_TCP_HOST, self.AISHUB_TCP_PORT))
            
            # Send authentication
            auth = f"{self.username}:{self.password}\r\n"
            self._tcp_socket.send(auth.encode())
            
            # Set streaming duration
            self._tcp_socket.settimeout(duration_seconds + 5)
            
            start_time = datetime.utcnow()
            
            while (datetime.utcnow() - start_time).seconds < duration_seconds:
                try:
                    data = self._tcp_socket.recv(1024).decode('utf-8', errors='ignore')
                    if not data:
                        break
                    
                    for line in data.strip().split('\r\n'):
                        messages_received += 1
                        parsed = self._parse_nmea(line)
                        # For now, just count - full parsing requires libais
                        
                except socket.timeout:
                    break
            
            self.logger.info(
                "tcp_stream_complete",
                messages_received=messages_received
            )
            
        except Exception as e:
            self.logger.error("tcp_stream_error", error=str(e))
        
        finally:
            if self._tcp_socket:
                self._tcp_socket.close()
                self._tcp_socket = None
        
        return messages_received
