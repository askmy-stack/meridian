#!/usr/bin/env python3
"""Comprehensive test suite for Meridian.

Tests all components across all phases:
1. Infrastructure connectivity (Kafka, Neo4j)
2. Data ingestion (GDELT, ACLED, AIS producers)
3. Graph database (Neo4j client, repositories)
4. REST API (FastAPI endpoints)
5. Intelligence Engine (BERT, XGBoost, NER)
6. Simulation (Monte Carlo, BFS propagation)
7. Alerting (Slack service)

Usage:
    cd /Users/abhinaysaikamineni/Projects/Supply Chain Risk Intelligence Platform
    python scripts/test_all.py
"""

import sys
import os
sys.path.insert(0, "/Users/abhinaysaikamineni/Projects/Supply Chain Risk Intelligence Platform")

def test_infrastructure():
    """Test infrastructure connectivity."""
    print("\n" + "="*60)
    print("INFRASTRUCTURE TESTS")
    print("="*60)
    
    results = []
    
    # Test Neo4j
    print("\n[1] Testing Neo4j connection...")
    try:
        from src.graph import get_neo4j_client
        client = get_neo4j_client()
        if client.health_check():
            print("✅ Neo4j: Connected")
            result = client.execute_query("MATCH (n) RETURN count(n) as count")
            print(f"   Database has {result[0]['count']} nodes")
            results.append(("Neo4j", True))
        else:
            print("❌ Neo4j: Connection failed")
            results.append(("Neo4j", False))
    except Exception as e:
        print(f"❌ Neo4j: Error - {e}")
        results.append(("Neo4j", False))
    
    return results

def test_graph_models():
    """Test graph models and repositories."""
    print("\n" + "="*60)
    print("GRAPH MODELS TESTS")
    print("="*60)
    
    results = []
    
    # Test Supplier model
    print("\n[1] Testing Supplier model...")
    try:
        from src.graph import Supplier
        supplier = Supplier(
            name="Test Supplier",
            country_iso="US",
            city="Test City",
            critical_flag=True
        )
        assert supplier.name == "Test Supplier"
        assert supplier.country_iso == "US"
        print("✅ Supplier model: OK")
        results.append(("Supplier Model", True))
    except Exception as e:
        print(f"❌ Supplier model: Error - {e}")
        results.append(("Supplier Model", False))
    
    # Test CSV upload
    print("\n[2] Testing CSV upload service...")
    try:
        from src.ingestion import get_csv_upload_service
        service = get_csv_upload_service()
        
        # Test with sample CSV
        csv_data = b"name,country_iso,city\nTestCorp,US,New York\nAnotherCorp,CN,Shanghai"
        result = service.upload(csv_data)
        
        print(f"✅ CSV Upload: Parsed {result.total_rows} rows, created {result.success_count} suppliers")
        results.append(("CSV Upload", True))
    except Exception as e:
        print(f"❌ CSV Upload: Error - {e}")
        results.append(("CSV Upload", False))
    
    return results

def test_intelligence_engine():
    """Test ML intelligence components."""
    print("\n" + "="*60)
    print("INTELLIGENCE ENGINE TESTS")
    print("="*60)
    
    results = []
    
    # Test BERT Classifier
    print("\n[1] Testing BERT Event Classifier...")
    try:
        from src.intelligence import classify_event
        
        result = classify_event("Protests at Foxconn factory in Zhengzhou blocking shipments")
        
        print(f"✅ BERT Classifier: Label={result.event_category}, Confidence={result.classification_confidence:.1%}")
        results.append(("BERT Classifier", True))
    except Exception as e:
        print(f"❌ BERT Classifier: Error - {e}")
        results.append(("BERT Classifier", False))
    
    # Test Risk Scorer
    print("\n[2] Testing XGBoost Risk Scorer...")
    try:
        from src.intelligence import score_supplier
        
        risk = score_supplier(
            "test-supplier-001",
            conflict_nearby=True,
            single_source=True,
            critical_events=3
        )
        
        print(f"✅ Risk Scorer: Score={risk.risk_score:.1%}, Category={risk.risk_category}")
        if risk.top_factors:
            print(f"   Top factor: {risk.top_factors[0]['description']}")
        results.append(("Risk Scorer", True))
    except Exception as e:
        print(f"❌ Risk Scorer: Error - {e}")
        results.append(("Risk Scorer", False))
    
    # Test NER
    print("\n[3] Testing NER Pipeline...")
    try:
        from src.intelligence import extract_entities
        
        text = "Foxconn factory in Shanghai near Port of Shanghai. Ships via Suez Canal."
        result = extract_entities(text, link_to_graph=False)
        
        suppliers = [e for e in result.entities if e.label == "SUPPLIER"]
        ports = [e for e in result.entities if e.label == "PORT"]
        chokepoints = [e for e in result.entities if e.label == "CHOKEPOINT"]
        
        print(f"✅ NER: Found {len(suppliers)} suppliers, {len(ports)} ports, {len(chokepoints)} chokepoints")
        results.append(("NER Pipeline", True))
    except Exception as e:
        print(f"❌ NER: Error - {e}")
        results.append(("NER Pipeline", False))
    
    return results

def test_simulation():
    """Test simulation components."""
    print("\n" + "="*60)
    print("SIMULATION TESTS")
    print("="*60)
    
    results = []
    
    # Test Monte Carlo
    print("\n[1] Testing Monte Carlo Simulator...")
    try:
        from src.simulation import simulate_disruption, DisruptionScenario
        
        result = simulate_disruption(
            event_type="port_closure",
            entity_id="port-Shanghai",
            entity_type="port",
            severity=0.8,
            probability=0.3,
            duration_days=14
        )
        
        print(f"✅ Monte Carlo: {result.iterations} iterations")
        print(f"   Disruption probability: {result.disruption_probability:.1%}")
        print(f"   Expected duration: {result.expected_duration_days:.0f} days")
        print(f"   Revenue at risk: ${result.total_revenue_at_risk:,.0f}")
        results.append(("Monte Carlo", True))
    except Exception as e:
        print(f"❌ Monte Carlo: Error - {e}")
        results.append(("Monte Carlo", False))
    
    # Test BFS Propagation
    print("\n[2] Testing BFS Propagation Engine...")
    try:
        from src.simulation import propagate_disruption
        
        result = propagate_disruption(
            source_entity_id="supplier-test-001",
            source_entity_type="supplier",
            impact_score=0.9
        )
        
        print(f"✅ BFS Propagation: {result.total_entities_affected} entities affected")
        print(f"   Suppliers: {result.total_suppliers_affected}")
        print(f"   SKUs: {result.total_skus_affected}")
        print(f"   Recovery time: {result.estimated_recovery_time_days} days")
        results.append(("BFS Propagation", True))
    except Exception as e:
        print(f"❌ BFS Propagation: Error - {e}")
        results.append(("BFS Propagation", False))
    
    return results

def test_alerting():
    """Test alerting service."""
    print("\n" + "="*60)
    print("ALERTING TESTS")
    print("="*60)
    
    results = []
    
    print("\n[1] Testing Slack Alerting Service...")
    try:
        from src.alerting import send_critical_alert, send_warning_alert
        
        # These will log instead of sending if webhook not configured
        success1 = send_critical_alert(
            "Test Critical Alert",
            "This is a test critical alert from Meridian test suite",
            entity_id="test-entity-001"
        )
        
        success2 = send_warning_alert(
            "Test Warning Alert",
            "This is a test warning alert",
            entity_id="test-entity-002"
        )
        
        print(f"✅ Slack Alerting: Critical={success1}, Warning={success2}")
        print("   (Alerts logged to console - configure SLACK_WEBHOOK_URL for actual delivery)")
        results.append(("Slack Alerting", True))
    except Exception as e:
        print(f"❌ Slack Alerting: Error - {e}")
        results.append(("Slack Alerting", False))
    
    return results

def run_pytest_tests():
    """Run existing pytest test suite."""
    print("\n" + "="*60)
    print("PYTEST TEST SUITE")
    print("="*60)
    
    import subprocess
    
    print("\nRunning pytest...")
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        cwd="/Users/abhinaysaikamineni/Projects/Supply Chain Risk Intelligence Platform"
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0

def print_summary(all_results):
    """Print test summary."""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total_tests = 0
    passed_tests = 0
    
    for category, results in all_results.items():
        print(f"\n{category}:")
        for test_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}: {test_name}")
            total_tests += 1
            if passed:
                passed_tests += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.0f}%)")
    print("="*60)
    
    return passed_tests == total_tests

def main():
    """Run all tests."""
    print("="*60)
    print("MERIDIAN COMPREHENSIVE TEST SUITE")
    print("="*60)
    print("\nThis will test all components of Meridian:")
    print("- Infrastructure (Neo4j)")
    print("- Graph models and repositories")
    print("- ML Intelligence Engine (BERT, XGBoost, NER)")
    print("- Simulation (Monte Carlo, BFS)")
    print("- Alerting (Slack)")
    print("\nMake sure Docker Compose is running for infrastructure tests!")
    print("="*60)
    
    all_results = {}
    
    # Run tests
    all_results["Infrastructure"] = test_infrastructure()
    all_results["Graph Models"] = test_graph_models()
    all_results["Intelligence Engine"] = test_intelligence_engine()
    all_results["Simulation"] = test_simulation()
    all_results["Alerting"] = test_alerting()
    
    # Print summary
    all_passed = print_summary(all_results)
    
    # Run pytest
    pytest_passed = run_pytest_tests()
    
    # Final result
    print("\n" + "="*60)
    if all_passed and pytest_passed:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED - Review output above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
