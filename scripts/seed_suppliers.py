#!/usr/bin/env python3
"""Seed Neo4j with demo supplier data from CSV.

Usage:
    python scripts/seed_suppliers.py --file data/sample_suppliers.csv
    make seed-suppliers  # Uses default file

This creates:
- Supplier nodes with risk scores
- Relationships to Port nodes
- Links between suppliers based on shared ports/countries
- Sample disruption paths for demo visualization
"""

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import structlog
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph.client import Neo4jClient

logger = structlog.get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed Neo4j with supplier data from CSV"
    )
    parser.add_argument(
        "--file",
        type=str,
        default="data/sample_suppliers.csv",
        help="Path to CSV file with supplier data (default: data/sample_suppliers.csv)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing Supplier nodes before seeding"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without writing to Neo4j"
    )
    return parser.parse_args()


def read_suppliers_csv(filepath: str) -> List[Dict]:
    """Read supplier data from CSV."""
    suppliers = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            supplier = {
                'id': f"SUP-{row['name'][:3].upper()}{hash(row['name']) % 10000:04d}",
                'name': row['name'],
                'country_iso': row['country_iso'],
                'city': row['city'],
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude']),
                'port_code': row.get('port_code'),
                'annual_volume_usd': float(row['annual_volume_usd']),
                'risk_score': float(row.get('risk_score', 0.5)),
                'critical': row.get('critical', 'False').lower() == 'true'
            }
            suppliers.append(supplier)
    return suppliers


def create_supplier_nodes(client: Neo4jClient, suppliers: List[Dict], dry_run: bool = False) -> int:
    """Create Supplier nodes in Neo4j."""
    if dry_run:
        logger.info("dry_run", action="create_nodes", count=len(suppliers))
        return len(suppliers)
    
    query = """
    UNWIND $suppliers AS supplier
    MERGE (s:Supplier {id: supplier.id})
    SET s.name = supplier.name,
        s.country_iso = supplier.country_iso,
        s.city = supplier.city,
        s.latitude = supplier.latitude,
        s.longitude = supplier.longitude,
        s.annual_volume_usd = supplier.annual_volume_usd,
        s.risk_score = supplier.risk_score,
        s.critical = supplier.critical,
        s.critical_flag = supplier.critical,
        s.created_at = datetime(),
        s.updated_at = datetime()
    RETURN count(s) as created
    """
    
    result = client.execute_query(query, {'suppliers': suppliers})
    created = result[0]['created'] if result else 0
    logger.info("suppliers_created", count=created)
    return created


def link_suppliers_to_ports(client: Neo4jClient, suppliers: List[Dict], dry_run: bool = False) -> int:
    """Create relationships between suppliers and ports."""
    # Build port linkages
    port_links = []
    for supplier in suppliers:
        if supplier['port_code']:
            port_links.append({
                'supplier_id': supplier['id'],
                'port_code': supplier['port_code']
            })
    
    if not port_links:
        return 0
    
    if dry_run:
        logger.info("dry_run", action="link_to_ports", count=len(port_links))
        return len(port_links)
    
    query = """
    UNWIND $links AS link
    MATCH (s:Supplier {id: link.supplier_id})
    MATCH (p:Port {locode: link.port_code})
    MERGE (s)-[r:SHIPS_VIA]->(p)
    SET r.created_at = datetime()
    RETURN count(r) as linked
    """
    
    try:
        result = client.execute_query(query, {'links': port_links})
        linked = result[0]['linked'] if result else 0
        logger.info("suppliers_linked_to_ports", count=linked)
        return linked
    except Exception as e:
        logger.warning("port_linking_failed", error=str(e), count=len(port_links))
        return 0


def create_supplier_relationships(client: Neo4jClient, suppliers: List[Dict], dry_run: bool = False) -> int:
    """Create relationships between suppliers (shared country = potential partners)."""
    # Group suppliers by country
    by_country: Dict[str, List[str]] = {}
    for s in suppliers:
        by_country.setdefault(s['country_iso'], []).append(s['id'])
    
    relationships = []
    for country, ids in by_country.items():
        if len(ids) > 1:
            # Create relationships between suppliers in same country
            for i, id1 in enumerate(ids):
                for id2 in ids[i+1:]:
                    relationships.append({
                        'id1': id1,
                        'id2': id2,
                        'country': country,
                        'relationship_type': 'SAME_COUNTRY'
                    })
    
    if not relationships:
        return 0
    
    if dry_run:
        logger.info("dry_run", action="create_relationships", count=len(relationships))
        return len(relationships)
    
    query = """
    UNWIND $relationships AS rel
    MATCH (s1:Supplier {id: rel.id1})
    MATCH (s2:Supplier {id: rel.id2})
    MERGE (s1)-[r:RELATED_TO]-(s2)
    SET r.relationship_type = rel.relationship_type,
        r.country = rel.country,
        r.created_at = datetime()
    RETURN count(r) as created
    """
    
    try:
        result = client.execute_query(query, {'relationships': relationships})
        created = result[0]['created'] if result else 0
        logger.info("supplier_relationships_created", count=created)
        return created
    except Exception as e:
        logger.warning("relationship_creation_failed", error=str(e))
        return 0


def create_disruption_scenarios(client: Neo4jClient, dry_run: bool = False) -> int:
    """Create sample disruption scenarios for demo purposes."""
    scenarios = [
        {
            'id': 'DIS-001',
            'name': 'Taiwan Strait Closure',
            'description': 'Geopolitical tensions close Taiwan Strait to shipping',
            'affected_countries': ['TW', 'CN'],
            'risk_multiplier': 2.5,
            'severity': 'critical'
        },
        {
            'id': 'DIS-002',
            'name': 'Suez Canal Blockage',
            'description': 'Major vessel blockage in Suez Canal',
            'affected_countries': ['EG'],
            'risk_multiplier': 1.8,
            'severity': 'high'
        },
        {
            'id': 'DIS-003',
            'name': 'Red Sea Crisis',
            'description': 'Ongoing Houthi attacks in Bab el-Mandeb',
            'affected_countries': ['EG', 'SA', 'YE'],
            'risk_multiplier': 1.5,
            'severity': 'high'
        }
    ]
    
    if dry_run:
        logger.info("dry_run", action="create_scenarios", count=len(scenarios))
        return len(scenarios)
    
    query = """
    UNWIND $scenarios AS sc
    MERGE (d:DisruptionScenario {id: sc.id})
    SET d.name = sc.name,
        d.description = sc.description,
        d.affected_countries = sc.affected_countries,
        d.risk_multiplier = sc.risk_multiplier,
        d.severity = sc.severity,
        d.active = true,
        d.created_at = datetime()
    RETURN count(d) as created
    """
    
    try:
        result = client.execute_query(query, {'scenarios': scenarios})
        created = result[0]['created'] if result else 0
        logger.info("disruption_scenarios_created", count=created)
        return created
    except Exception as e:
        logger.warning("scenario_creation_failed", error=str(e))
        return 0


def link_scenarios_to_suppliers(client: Neo4jClient, suppliers: List[Dict], dry_run: bool = False) -> int:
    """Link disruption scenarios to affected suppliers."""
    # Taiwan suppliers affected by DIS-001
    taiwan_suppliers = [s['id'] for s in suppliers if s['country_iso'] == 'TW']
    # Egypt suppliers affected by DIS-002
    egypt_suppliers = [s['id'] for s in suppliers if s['country_iso'] == 'EG']
    # Red Sea affected (Saudi, Yemen, Egypt)
    redsea_countries = ['SA', 'YE', 'EG', 'IL', 'JO']
    redsea_suppliers = [s['id'] for s in suppliers if s['country_iso'] in redsea_countries]
    
    links = []
    for sid in taiwan_suppliers:
        links.append({'supplier_id': sid, 'scenario_id': 'DIS-001', 'impact': 'direct'})
    for sid in egypt_suppliers:
        links.append({'supplier_id': sid, 'scenario_id': 'DIS-002', 'impact': 'direct'})
    for sid in redsea_suppliers:
        links.append({'supplier_id': sid, 'scenario_id': 'DIS-003', 'impact': 'indirect'})
    
    if not links:
        return 0
    
    if dry_run:
        logger.info("dry_run", action="link_scenarios", count=len(links))
        return len(links)
    
    query = """
    UNWIND $links AS link
    MATCH (s:Supplier {id: link.supplier_id})
    MATCH (d:DisruptionScenario {id: link.scenario_id})
    MERGE (s)-[r:AFFECTED_BY]->(d)
    SET r.impact = link.impact,
        r.created_at = datetime()
    RETURN count(r) as linked
    """
    
    try:
        result = client.execute_query(query, {'links': links})
        linked = result[0]['linked'] if result else 0
        logger.info("scenario_supplier_links_created", count=linked)
        return linked
    except Exception as e:
        logger.warning("scenario_linking_failed", error=str(e))
        return 0


def clear_existing_suppliers(client: Neo4jClient) -> int:
    """Clear all existing supplier data."""
    query = """
    MATCH (s:Supplier)
    OPTIONAL MATCH (s)-[r]-()
    DELETE r, s
    RETURN count(s) as deleted
    """
    
    try:
        result = client.execute_query(query)
        deleted = result[0]['deleted'] if result else 0
        logger.info("suppliers_cleared", count=deleted)
        return deleted
    except Exception as e:
        logger.error("clear_suppliers_failed", error=str(e))
        return 0


def print_summary(suppliers: List[Dict], stats: Dict):
    """Print seeding summary."""
    print("\n" + "="*60)
    print("SUPPLIER SEEDING SUMMARY")
    print("="*60)
    print(f"\nSuppliers loaded from CSV: {len(suppliers)}")
    print(f"By country:")
    by_country = {}
    for s in suppliers:
        by_country[s['country_iso']] = by_country.get(s['country_iso'], 0) + 1
    for country, count in sorted(by_country.items(), key=lambda x: -x[1])[:10]:
        print(f"  {country}: {count}")
    
    print(f"\nCritical suppliers: {sum(1 for s in suppliers if s['critical'])}")
    print(f"High risk (>0.7): {sum(1 for s in suppliers if s['risk_score'] > 0.7)}")
    print(f"Medium risk (0.4-0.7): {sum(1 for s in suppliers if 0.4 <= s['risk_score'] <= 0.7)}")
    print(f"Low risk (<0.4): {sum(1 for s in suppliers if s['risk_score'] < 0.4)}")
    
    if stats:
        print(f"\nNeo4j writes:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    print("="*60 + "\n")


def main():
    args = parse_args()
    
    # Load env
    load_dotenv()
    
    # Resolve CSV path
    csv_path = Path(args.file)
    if not csv_path.is_absolute():
        csv_path = Path(__file__).parent.parent / csv_path
    
    if not csv_path.exists():
        logger.error("csv_file_not_found", path=str(csv_path))
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)
    
    # Read CSV
    try:
        suppliers = read_suppliers_csv(str(csv_path))
    except Exception as e:
        logger.error("csv_read_failed", error=str(e))
        print(f"Error reading CSV: {e}")
        sys.exit(1)
    
    if not suppliers:
        logger.error("no_suppliers_in_csv")
        print("Error: No suppliers found in CSV")
        sys.exit(1)
    
    # Connect to Neo4j
    if not args.dry_run:
        client = Neo4jClient(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "meridian_password"),
        )
        
        # Clear if requested
        if args.clear:
            clear_existing_suppliers(client)
    else:
        client = None
    
    # Create data
    stats = {}
    
    stats['suppliers_created'] = create_supplier_nodes(client, suppliers, args.dry_run)
    stats['port_links'] = link_suppliers_to_ports(client, suppliers, args.dry_run)
    stats['supplier_relationships'] = create_supplier_relationships(client, suppliers, args.dry_run)
    stats['scenarios_created'] = create_disruption_scenarios(client, args.dry_run)
    stats['scenario_links'] = link_scenarios_to_suppliers(client, suppliers, args.dry_run)
    
    # Print summary
    print_summary(suppliers, stats)
    
    if args.dry_run:
        print("DRY RUN — No data written to Neo4j")
    else:
        print("Seeding complete! View the graph at http://localhost:7474")
        print("Query to see all suppliers:")
        print("  MATCH (s:Supplier) RETURN s LIMIT 25")


if __name__ == "__main__":
    main()
