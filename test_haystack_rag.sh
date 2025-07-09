#!/bin/bash
# Test Haystack RAG Functionality using curl

echo "=============================================="
echo "Haystack RAG Functionality Test Suite"
echo "Time: $(date)"
echo "Target: http://localhost:8000"
echo "=============================================="
echo

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name=$1
    local test_cmd=$2
    local expected_pattern=$3
    
    echo -n "Test: $test_name... "
    
    result=$(eval "$test_cmd" 2>&1)
    
    if echo "$result" | grep -q "$expected_pattern"; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        echo "  Output: $(echo "$result" | head -n 1)"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test 1: Health Check
echo "1. Health Check"
run_test "Service health" \
    "curl -s http://localhost:8000/health" \
    '"status":"healthy"'
echo

# Test 2: Document Ingestion
echo "2. Document Ingestion"
INGEST_DATA='[{
    "content": "The legal framework for data protection includes GDPR in Europe.",
    "metadata": {"source": "legal_guide.pdf", "category": "data_protection"},
    "document_type": "legal_document"
}, {
    "content": "Contract law principles include offer and acceptance.",
    "metadata": {"source": "contract_basics.pdf", "category": "contracts"},
    "document_type": "legal_document"
}]'

RESPONSE=$(curl -s -X POST http://localhost:8000/ingest \
    -H "Content-Type: application/json" \
    -d "$INGEST_DATA")

if echo "$RESPONSE" | grep -q "document_ids"; then
    echo -e "${GREEN}✅ Document ingestion successful${NC}"
    ((TESTS_PASSED++))
    
    # Extract document IDs for later tests
    DOC_ID=$(echo "$RESPONSE" | grep -o '"document_ids":\[[^]]*\]' | grep -o '"[a-f0-9-]*"' | head -1 | tr -d '"')
    echo "  Document ID: $DOC_ID"
else
    echo -e "${RED}❌ Document ingestion failed${NC}"
    echo "  Response: $RESPONSE"
    ((TESTS_FAILED++))
fi
echo

# Test 3: BM25 Search
echo "3. BM25 Search"
SEARCH_DATA='{
    "query": "GDPR data protection",
    "top_k": 5,
    "use_bm25": true,
    "use_vector": false,
    "use_hybrid": false
}'

run_test "BM25 search" \
    "curl -s -X POST http://localhost:8000/search -H 'Content-Type: application/json' -d '$SEARCH_DATA'" \
    '"results":\['
echo

# Test 4: Vector Search
echo "4. Vector Search"
VECTOR_SEARCH='{
    "query": "regulations for handling personal data",
    "top_k": 5,
    "use_bm25": false,
    "use_vector": true,
    "use_hybrid": false
}'

run_test "Vector search" \
    "curl -s -X POST http://localhost:8000/search -H 'Content-Type: application/json' -d '$VECTOR_SEARCH'" \
    '"results":\['
echo

# Test 5: Hybrid Search
echo "5. Hybrid Search"
HYBRID_SEARCH='{
    "query": "contract law",
    "top_k": 5,
    "use_hybrid": true
}'

run_test "Hybrid search" \
    "curl -s -X POST http://localhost:8000/search -H 'Content-Type: application/json' -d '$HYBRID_SEARCH'" \
    '"search_type":"hybrid"'
echo

# Test 6: Document Context Retrieval
echo "6. Document Context Retrieval"
if [ ! -z "$DOC_ID" ]; then
    run_test "Get document context" \
        "curl -s http://localhost:8000/get_document_with_context/$DOC_ID" \
        '"content":'
else
    echo -e "${RED}❌ Skipped - No document ID available${NC}"
    ((TESTS_FAILED++))
fi
echo

# Test 7: Search with Filters
echo "7. Search with Filters"
FILTERED_SEARCH='{
    "query": "legal",
    "top_k": 5,
    "use_hybrid": true,
    "filters": {"metadata.category": "contracts"}
}'

run_test "Filtered search" \
    "curl -s -X POST http://localhost:8000/search -H 'Content-Type: application/json' -d '$FILTERED_SEARCH'" \
    '"results":'
echo

# Test 8: Empty Search Results
echo "8. Empty Search Results"
EMPTY_SEARCH='{
    "query": "xyz123nonexistentquery789abc",
    "top_k": 5,
    "use_hybrid": true
}'

run_test "Empty search handling" \
    "curl -s -X POST http://localhost:8000/search -H 'Content-Type: application/json' -d '$EMPTY_SEARCH'" \
    '"total_results":'
echo

# Summary
echo "=============================================="
echo "Test Summary"
echo "=============================================="
echo -e "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC} ✅"
echo -e "Failed: ${RED}$TESTS_FAILED${NC} ❌"
echo -e "Success Rate: $(( TESTS_PASSED * 100 / (TESTS_PASSED + TESTS_FAILED) ))%"
echo "=============================================="