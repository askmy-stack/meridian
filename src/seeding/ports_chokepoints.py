"""Seeding script for ports and chokepoints.

Loads major global ports (UN/LOCODE) and shipping chokepoints into Neo4j.
This provides the canonical entities that events can be linked to.
"""

import os
from typing import List

import structlog

from ..graph import get_neo4j_client
from ..graph.models import Chokepoint, Port

logger = structlog.get_logger(__name__)


# Major global shipping chokepoints
CHOKEPOINTS = [
    {
        "name": "Suez Canal",
        "latitude": 30.0454,
        "longitude": 32.2654,
        "daily_vessel_count": 50,
        "annual_trade_value_usd": 1_000_000_000_000,  # ~$1T
        "radius_km": 100
    },
    {
        "name": "Panama Canal",
        "latitude": 9.0846,
        "longitude": -79.6821,
        "daily_vessel_count": 35,
        "annual_trade_value_usd": 270_000_000_000,  # ~$270B
        "radius_km": 80
    },
    {
        "name": "Strait of Hormuz",
        "latitude": 26.6500,
        "longitude": 56.2500,
        "daily_vessel_count": 30,
        "annual_trade_value_usd": 1_200_000_000_000,  # ~$1.2T (oil)
        "radius_km": 150
    },
    {
        "name": "Strait of Malacca",
        "latitude": 2.8000,
        "longitude": 101.4000,
        "daily_vessel_count": 200,
        "annual_trade_value_usd": 500_000_000_000,
        "radius_km": 200
    },
    {
        "name": "Bab-el-Mandeb",
        "latitude": 12.6000,
        "longitude": 43.4000,
        "daily_vessel_count": 40,
        "annual_trade_value_usd": 600_000_000_000,
        "radius_km": 100
    },
    {
        "name": "Turkish Straits",
        "latitude": 41.2000,
        "longitude": 29.1000,
        "daily_vessel_count": 150,
        "annual_trade_value_usd": 150_000_000_000,
        "radius_km": 150
    },
    {
        "name": "Dover Strait",
        "latitude": 51.0000,
        "longitude": 1.4000,
        "daily_vessel_count": 400,
        "annual_trade_value_usd": 200_000_000_000,
        "radius_km": 50
    },
    {
        "name": "Cape of Good Hope",
        "latitude": -34.3500,
        "longitude": 18.4700,
        "daily_vessel_count": 25,
        "annual_trade_value_usd": 80_000_000_000,
        "radius_km": 300
    },
    {
        "name": "Cape Horn",
        "latitude": -55.9833,
        "longitude": -67.2667,
        "daily_vessel_count": 15,
        "annual_trade_value_usd": 40_000_000_000,
        "radius_km": 300
    },
    {
        "name": "Taiwan Strait",
        "latitude": 24.0000,
        "longitude": 119.0000,
        "daily_vessel_count": 250,
        "annual_trade_value_usd": 800_000_000_000,
        "radius_km": 180
    },
    {
        "name": "Korea Strait",
        "latitude": 34.5000,
        "longitude": 129.0000,
        "daily_vessel_count": 180,
        "annual_trade_value_usd": 300_000_000_000,
        "radius_km": 150
    },
    {
        "name": "English Channel",
        "latitude": 50.5000,
        "longitude": -1.5000,
        "daily_vessel_count": 500,
        "annual_trade_value_usd": 400_000_000_000,
        "radius_km": 100
    }
]


# Sample of major global ports (subset of UN/LOCODE)
# In production, load full UN/LOCODE database
MAJOR_PORTS = [
    # Asia
    {"name": "Shanghai", "locode": "CNSHG", "country_iso": "CN", "lat": 31.2304, "lon": 121.4737, "teu": 47030},
    {"name": "Singapore", "locode": "SGSIN", "country_iso": "SG", "lat": 1.3521, "lon": 103.8198, "teu": 37500},
    {"name": "Ningbo-Zhoushan", "locode": "CNNGB", "country_iso": "CN", "lat": 29.8683, "lon": 121.5440, "teu": 35300},
    {"name": "Shenzhen", "locode": "CNSZX", "country_iso": "CN", "lat": 22.5431, "lon": 114.0579, "teu": 30000},
    {"name": "Busan", "locode": "KRPUS", "country_iso": "KR", "lat": 35.1796, "lon": 129.0756, "teu": 22700},
    {"name": "Hong Kong", "locode": "HKHKG", "country_iso": "HK", "lat": 22.3193, "lon": 114.1694, "teu": 17900},
    {"name": "Qingdao", "locode": "CNTAO", "country_iso": "CN", "lat": 36.0671, "lon": 120.3826, "teu": 25700},
    {"name": "Tianjin", "locode": "CNTSN", "country_iso": "CN", "lat": 39.0842, "lon": 117.2010, "teu": 22100},
    {"name": "Port Klang", "locode": "MYPKG", "country_iso": "MY", "lat": 3.0326, "lon": 101.4430, "teu": 13600},
    {"name": "Kaohsiung", "locode": "TWKHH", "country_iso": "TW", "lat": 22.6273, "lon": 120.3014, "teu": 9900},
    {"name": "Tokyo", "locode": "JPTYO", "country_iso": "JP", "lat": 35.6762, "lon": 139.6503, "teu": 4500},
    {"name": "Yokohama", "locode": "JPYOK", "country_iso": "JP", "lat": 35.4437, "lon": 139.6380, "teu": 2800},
    
    # Europe
    {"name": "Rotterdam", "locode": "NLRTM", "country_iso": "NL", "lat": 51.9244, "lon": 4.4777, "teu": 14700},
    {"name": "Antwerp", "locode": "BEANR", "country_iso": "BE", "lat": 51.2194, "lon": 4.4025, "teu": 12000},
    {"name": "Hamburg", "locode": "DEHAM", "country_iso": "DE", "lat": 53.5488, "lon": 9.9872, "teu": 8500},
    {"name": "Felixstowe", "locode": "GBFXT", "country_iso": "GB", "lat": 51.9617, "lon": 1.3513, "teu": 4200},
    {"name": "Valencia", "locode": "ESVLC", "country_iso": "ES", "lat": 39.4699, "lon": -0.3763, "teu": 5800},
    {"name": "Piraeus", "locode": "GRPIR", "country_iso": "GR", "lat": 37.9485, "lon": 23.7169, "teu": 5400},
    {"name": "Algeciras", "locode": "ESALG", "country_iso": "ES", "lat": 36.1333, "lon": -5.4500, "teu": 4800},
    {"name": "Bremerhaven", "locode": "DEBRV", "country_iso": "DE", "lat": 53.5396, "lon": 8.5809, "teu": 4900},
    
    # South Asia
    {"name": "Jawaharlal Nehru Port (Mumbai)", "locode": "INNSA", "country_iso": "IN", "lat": 18.9490, "lon": 72.9525, "teu": 5700},
    {"name": "Mundra", "locode": "INMUN", "country_iso": "IN", "lat": 22.7395, "lon": 69.7240, "teu": 6500},
    {"name": "Colombo", "locode": "LKCMB", "country_iso": "LK", "lat": 6.9344, "lon": 79.8428, "teu": 7200},

    # Middle East
    {"name": "Jebel Ali", "locode": "AEJEA", "country_iso": "AE", "lat": 24.9857, "lon": 55.0275, "teu": 14400},
    {"name": "Jeddah", "locode": "SAJED", "country_iso": "SA", "lat": 21.4858, "lon": 39.1925, "teu": 4800},
    {"name": "Salalah", "locode": "OMSLL", "country_iso": "OM", "lat": 17.0199, "lon": 54.0897, "teu": 3900},
    {"name": "Dammam", "locode": "SADMM", "country_iso": "SA", "lat": 26.4344, "lon": 50.1030, "teu": 2500},
    
    # North America
    {"name": "Los Angeles", "locode": "USLAX", "country_iso": "US", "lat": 33.7288, "lon": -118.2620, "teu": 10700},
    {"name": "Long Beach", "locode": "USLGB", "country_iso": "US", "lat": 33.7542, "lon": -118.2165, "teu": 9100},
    {"name": "New York/New Jersey", "locode": "USNYC", "country_iso": "US", "lat": 40.6840, "lon": -74.1682, "teu": 7800},
    {"name": "Savannah", "locode": "USSAV", "country_iso": "US", "lat": 32.0835, "lon": -81.0998, "teu": 4900},
    {"name": "Seattle", "locode": "USSEA", "country_iso": "US", "lat": 47.6062, "lon": -122.3321, "teu": 3400},
    {"name": "Oakland", "locode": "USOAK", "country_iso": "US", "lat": 37.8044, "lon": -122.2712, "teu": 2500},
    {"name": "Vancouver", "locode": "CAVAN", "country_iso": "CA", "lat": 49.2827, "lon": -123.1207, "teu": 3600},
    {"name": "Montréal", "locode": "CAMTR", "country_iso": "CA", "lat": 45.5017, "lon": -73.5673, "teu": 1900},
    
    # Latin America
    {"name": "Santos", "locode": "BRSSZ", "country_iso": "BR", "lat": -23.9608, "lon": -46.3331, "teu": 4300},
    {"name": "Colón", "locode": "PAONX", "country_iso": "PA", "lat": 9.3583, "lon": -79.9014, "teu": 4600},
    {"name": "Buenos Aires", "locode": "ARBUE", "country_iso": "AR", "lat": -34.6037, "lon": -58.3816, "teu": 1900},
    {"name": "Cartagena", "locode": "COCTG", "country_iso": "CO", "lat": 10.3910, "lon": -75.4794, "teu": 2800},
    
    # Africa
    {"name": "Durban", "locode": "ZADUR", "country_iso": "ZA", "lat": -29.8587, "lon": 31.0218, "teu": 2900},
    {"name": "Cape Town", "locode": "ZACPT", "country_iso": "ZA", "lat": -33.9249, "lon": 18.4241, "teu": 820},
    {"name": "Lagos", "locode": "NGLOS", "country_iso": "NG", "lat": 6.5244, "lon": 3.3792, "teu": 1200},
    {"name": "Djibouti", "locode": "DJJIB", "country_iso": "DJ", "lat": 11.5721, "lon": 43.1456, "teu": 1100},
    
    # Oceania
    {"name": "Melbourne", "locode": "AUMEL", "country_iso": "AU", "lat": -37.8136, "lon": 144.9631, "teu": 3100},
    {"name": "Sydney", "locode": "AUSYD", "country_iso": "AU", "lat": -33.8688, "lon": 151.2093, "teu": 2500},
    {"name": "Brisbane", "locode": "AUBNE", "country_iso": "AU", "lat": -27.4698, "lon": 153.0251, "teu": 1400},
    {"name": "Tauranga", "locode": "NZTRG", "country_iso": "NZ", "lat": -37.6866, "lon": 176.1673, "teu": 1200},
]


class PortChokepointSeeder:
    """Seeds Neo4j with ports and chokepoints.
    
    Usage:
        seeder = PortChokepointSeeder()
        seeder.seed_chokepoints()
        seeder.seed_ports()
        seeder.link_ports_to_chokepoints()
    """
    
    def __init__(self):
        self.client = get_neo4j_client()
        self.logger = logger.bind(seeder="PortChokepointSeeder")
        
        self.chokepoint_ids = {}  # name -> id mapping
        self.port_ids = {}  # locode -> id mapping
    
    def seed_chokepoints(self) -> int:
        """Seed chokepoints into Neo4j.
        
        Returns:
            Number of chokepoints created
        """
        created_count = 0
        
        query = """
        MERGE (c:Chokepoint {name: $name})
        ON CREATE SET 
            c.id = $id,
            c.latitude = $latitude,
            c.longitude = $longitude,
            c.daily_vessel_count = $daily_vessel_count,
            c.annual_trade_value_usd = $annual_trade_value_usd,
            c.radius_km = $radius_km,
            c.current_risk_score = 0.0,
            c.created_at = datetime()
        RETURN c.id as id
        """
        
        with self.client.session() as session:
            for chokepoint_data in CHOKEPOINTS:
                try:
                    result = session.run(query, {
                        "id": f"chokepoint-{chokepoint_data['name'].lower().replace(' ', '-')}",
                        **chokepoint_data
                    })
                    record = result.single()
                    
                    if record:
                        self.chokepoint_ids[chokepoint_data["name"]] = record["id"]
                        created_count += 1
                        
                except Exception as e:
                    self.logger.error(
                        "chokepoint_seed_failed",
                        name=chokepoint_data["name"],
                        error=str(e)
                    )
        
        self.logger.info(
            "chokepoints_seeded",
            count=created_count,
            total=len(CHOKEPOINTS)
        )
        
        return created_count
    
    def seed_ports(self) -> int:
        """Seed ports into Neo4j.
        
        Returns:
            Number of ports created
        """
        created_count = 0
        
        query = """
        MERGE (p:Port {locode: $locode})
        ON CREATE SET 
            p.id = $id,
            p.name = $name,
            p.country_iso = $country_iso,
            p.latitude = $latitude,
            p.longitude = $longitude,
            p.throughput_teu_annual = $throughput,
            p.congestion_score = 0.0,
            p.created_at = datetime()
        RETURN p.id as id
        """
        
        with self.client.session() as session:
            for port_data in MAJOR_PORTS:
                try:
                    result = session.run(query, {
                        "id": f"port-{port_data['locode']}",
                        "locode": port_data["locode"],
                        "name": port_data["name"],
                        "country_iso": port_data["country_iso"],
                        "latitude": port_data["lat"],
                        "longitude": port_data["lon"],
                        "throughput": port_data["teu"] * 1000  # Convert to actual TEU
                    })
                    record = result.single()
                    
                    if record:
                        self.port_ids[port_data["locode"]] = record["id"]
                        created_count += 1
                        
                except Exception as e:
                    self.logger.error(
                        "port_seed_failed",
                        name=port_data["name"],
                        error=str(e)
                    )
        
        self.logger.info(
            "ports_seeded",
            count=created_count,
            total=len(MAJOR_PORTS)
        )
        
        return created_count
    
    def link_ports_to_chokepoints(self) -> int:
        """Create PASSES_THROUGH relationships between ports and nearby chokepoints.
        
        This is a simplified version - in production use geospatial calculation.
        
        Returns:
            Number of relationships created
        """
        # Manual mapping of major ports to chokepoints they use
        port_chokepoint_links = [
            # Suez Canal connections
            ("CNSHG", "Suez Canal"),  # Shanghai
            ("SGSIN", "Suez Canal"),  # Singapore
            ("CNNGB", "Suez Canal"),  # Ningbo
            ("CNSZX", "Suez Canal"),  # Shenzhen
            ("NLRTM", "Suez Canal"),  # Rotterdam
            ("BEANR", "Suez Canal"),  # Antwerp
            ("AEJEA", "Suez Canal"),  # Jebel Ali
            
            # Panama Canal connections
            ("USLAX", "Panama Canal"),  # LA
            ("USLGB", "Panama Canal"),  # Long Beach
            ("USNYC", "Panama Canal"),  # NY/NJ
            ("CNSHG", "Panama Canal"),  # Shanghai (alternative route)
            ("SGSIN", "Panama Canal"),  # Singapore
            
            # Strait of Hormuz connections
            ("AEJEA", "Strait of Hormuz"),  # Jebel Ali
            ("SAJED", "Strait of Hormuz"),  # Jeddah
            ("OMSLL", "Strait of Hormuz"),  # Salalah
            ("SGSIN", "Strait of Hormuz"),  # Singapore
            ("INNSA", "Strait of Hormuz"),  # JNPT (Mumbai) — uses INNSA locode

            # Strait of Malacca connections
            ("CNSHG", "Strait of Malacca"),  # Shanghai
            ("SGSIN", "Strait of Malacca"),  # Singapore
            ("CNNGB", "Strait of Malacca"),  # Ningbo
            ("CNSZX", "Strait of Malacca"),  # Shenzhen
            ("MYPKG", "Strait of Malacca"),  # Port Klang (corrected from MYPTI)
            ("TWKHH", "Strait of Malacca"),  # Kaohsiung
            
            # Bab-el-Mandeb connections
            ("SAJED", "Bab-el-Mandeb"),  # Jeddah
            ("OMSLL", "Bab-el-Mandeb"),  # Salalah
            ("AEJEA", "Bab-el-Mandeb"),  # Jebel Ali
        ]
        
        query = """
        MATCH (p:Port {locode: $locode})
        MATCH (c:Chokepoint {name: $chokepoint_name})
        MERGE (p)-[r:PASSES_THROUGH]->(c)
        ON CREATE SET r.created_at = datetime()
        RETURN count(r) as created
        """
        
        created_count = 0
        
        with self.client.session() as session:
            for locode, chokepoint_name in port_chokepoint_links:
                try:
                    result = session.run(query, {
                        "locode": locode,
                        "chokepoint_name": chokepoint_name
                    })
                    record = result.single()
                    
                    if record and record["created"] > 0:
                        created_count += 1
                        
                except Exception as e:
                    self.logger.debug(
                        "port_chokepoint_link_skipped",
                        locode=locode,
                        chokepoint=chokepoint_name,
                        error=str(e)
                    )
        
        self.logger.info(
            "port_chokepoint_links_created",
            count=created_count
        )
        
        return created_count
    
    def run_full_seed(self) -> dict:
        """Run complete seeding process.
        
        Returns:
            Summary of seeding results
        """
        self.logger.info("starting_full_seed")
        
        chokepoints = self.seed_chokepoints()
        ports = self.seed_ports()
        links = self.link_ports_to_chokepoints()
        
        result = {
            "chokepoints_seeded": chokepoints,
            "ports_seeded": ports,
            "relationships_created": links
        }
        
        self.logger.info("full_seed_complete", **result)
        
        return result


if __name__ == "__main__":
    # CLI usage
    print("Port and Chokepoint Seeder for Meridian")
    print("=" * 50)
    
    seeder = PortChokepointSeeder()
    results = seeder.run_full_seed()
    
    print(f"\nSeeding complete:")
    print(f"  Chokepoints: {results['chokepoints_seeded']}")
    print(f"  Ports: {results['ports_seeded']}")
    print(f"  Relationships: {results['relationships_created']}")
