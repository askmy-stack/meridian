#!/bin/bash
# Test Meridian API endpoints
# Usage: ./scripts/test_api.sh

echo "=============================================="
echo "MERIDIAN API ENDPOINT TESTS"
echo "=============================================="
echo ""
echo "Prerequisites:"
echo "- API server running: uvicorn src.api.main:app --reload"
echo "- Infrastructure: docker compose up -d"
echo ""

BASE_URL="http://localhost:8000"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

test_endpoint() {
    local method=$1
    local endpoint=$2
    local expected_status=$3
    local description=$4
    
    echo -n "Testing $method $endpoint... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        -X "$method" \
        "$BASE_URL$endpoint" 2>/dev/null)
    
    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC} ($response) - $description"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC} (got $response, expected $expected_status)"
        return 1
    fi
}

echo "--- Health Checks ---"
test_endpoint "GET" "/health" "200" "API health check"
test_endpoint "GET" "/health/neo4j" "200" "Neo4j connectivity"

echo ""
echo "--- Supplier Endpoints ---"
test_endpoint "GET" "/suppliers" "200" "List suppliers"
test_endpoint "POST" "/suppliers" "422" "Create supplier (needs body)"
test_endpoint "GET" "/suppliers/template/download" "200" "Download CSV template"

echo ""
echo "--- Statistics ---"
test_endpoint "GET" "/stats" "200" "System statistics"

echo ""
echo "--- Visualization ---"
test_endpoint "GET" "/visualization/network?depth=2" "200" "Network graph"
test_endpoint "GET" "/visualization/risk-map?entity_type=supplier" "200" "Risk map data"

echo ""
echo "--- Authentication ---"
test_endpoint "POST" "/auth/login" "422" "Login (needs credentials)"
test_endpoint "GET" "/auth/me" "403" "Get current user (needs auth)"

echo ""
echo "--- Intelligence ---"
test_endpoint "POST" "/intelligence/weekly-digest" "200" "Generate weekly digest"

echo ""
echo "=============================================="
echo "API TESTS COMPLETE"
echo "=============================================="
