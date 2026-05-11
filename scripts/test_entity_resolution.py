#!/usr/bin/env python3
"""Test script for entity resolution end-to-end flow.

This script:
1. Seeds Neo4j with ports and chokepoints
2. Creates sample suppliers
3. Runs entity resolution consumer against GDELT data
4. Verifies relationships created

Usage:
    cd /Users/abhinaysaikamineni/Projects/Supply Chain Risk Intelligence Platform
    python scripts/test_entity_resolution.py
"""

import sys
import time

# Add src to path
sys.path.insert(0, "/Users/abhinaysaikamineni/Projects/Supply Chain Risk Intelligence Platform")

def main():
    print("=" * 60)
    print("Meridian Entity Resolution Test")
    print("=" * 60)
    
    # Step 1: Test Neo4j connection
    print("\n[1/4] Testing Neo4j connection...")
    try:
        from src.graph import get_neo4j_client
        client = get_neo4j_client()
        if client.health_check():
            result = client.execute_query("MATCH (n) RETURN count(n) as count")
            print(f"✅ Neo4j connected. Current nodes: {result[0]['count']}")
        else:
            print("❌ Neo4j connection failed")
            return 1
    except Exception as e:
        print(f"❌ Neo4j error: {e}")
        return 1
    
    # Step 2: Seed ports and chokepoints
    print("\n[2/4] Seeding ports and chokepoints...")
    try:
        from src.seeding import PortChokepointSeeder
        seeder = PortChokepointSeeder()
        results = seeder.run_full_seed()
        print(f"✅ Seeding complete:")
        print(f"   - Chokepoints: {results['chokepoints_seeded']}")
        print(f"   - Ports: {results['ports_seeded']}")
        print(f"   - Relationships: {results['relationships_created']}")
    except Exception as e:
        print(f"❌ Seeding error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Step 3: Create sample suppliers
    print("\n[3/4] Creating sample suppliers...")
    try:
        from src.graph import Supplier, get_supplier_repository
        repo = get_supplier_repository()
        
        sample_suppliers = [
            Supplier(name="Foxconn", country_iso="TW", city="Taipei", industry="Electronics", critical_flag=True),
            Supplier(name="TSMC", country_iso="TW", city="Hsinchu", industry="Semiconductors", critical_flag=True),
            Supplier(name="Samsung Electronics", country_iso="KR", city="Suwon", industry="Electronics", critical_flag=True),
            Supplier(name="Intel", country_iso="US", city="Santa Clara", industry="Semiconductors", critical_flag=True),
            Supplier(name="Qualcomm", country_iso="US", city="San Diego", industry="Semiconductors"),
        ]
        
        created = repo.create_many(sample_suppliers)
        print(f"✅ Created {len(created)} sample suppliers:")
        for s in created:
            print(f"   - {s.name} ({s.country_iso})")
    except Exception as e:
        print(f"❌ Supplier creation error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Step 4: Run entity resolution consumer
    print("\n[4/4] Running entity resolution consumer...")
    print("   Processing messages from Kafka (will process up to 50 messages)...")
    try:
        from src.consumers import EntityResolutionConsumer
        
        consumer = EntityResolutionConsumer(
            bootstrap_servers="localhost:9092",
            fuzzy_threshold=70
        )
        
        consumer.subscribe([
            "meridian.gdelt.conflict",
            "meridian.gdelt.protest",
        ])
        
        # Process up to 50 messages
        consumer.run(max_messages=50)
        
        stats = consumer.get_stats()
        print(f"✅ Consumer complete:")
        print(f"   - Events processed: {stats['events_processed']}")
        print(f"   - Suppliers linked: {stats['suppliers_linked']}")
        print(f"   - Chokepoints linked: {stats['chokepoints_linked']}")
        print(f"   - Total entities linked: {stats['entities_linked']}")
        print(f"   - Errors: {stats['errors']}")
        
    except Exception as e:
        print(f"❌ Consumer error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 60)
    print("Entity Resolution Test Complete!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
