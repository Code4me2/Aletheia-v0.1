#!/bin/bash

# Haystack RAG Migration Verification Script
# This script verifies that the RAG-only migration was completed successfully

echo "======================================"
echo "Haystack RAG Migration Verification"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if services are defined in docker-compose
echo "1. Checking Docker configuration..."
if grep -q "haystack_service_rag.py" ../n8n/haystack-service/Dockerfile 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Dockerfile updated to use RAG-only service"
else
    echo -e "${RED}✗${NC} Dockerfile not updated"
fi

if grep -q "requirements-rag.txt" ../n8n/haystack-service/Dockerfile 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Dockerfile using RAG-specific requirements"
else
    echo -e "${RED}✗${NC} Dockerfile not using RAG requirements"
fi

echo ""
echo "2. Checking n8n node configuration..."
if grep -q '"version": "2.0.0"' custom-nodes/n8n-nodes-haystack/package.json 2>/dev/null; then
    echo -e "${GREEN}✓${NC} n8n node updated to version 2.0.0"
else
    echo -e "${RED}✗${NC} n8n node not updated"
fi

if grep -q "n8n-nodes-haystack-rag" custom-nodes/n8n-nodes-haystack/package.json 2>/dev/null; then
    echo -e "${GREEN}✓${NC} n8n node renamed to RAG version"
else
    echo -e "${RED}✗${NC} n8n node not renamed"
fi

echo ""
echo "3. Starting services (if not already running)..."
echo "Running: docker-compose -f ../docker-compose.yml -f docker-compose.haystack.yml up -d"
docker-compose -f ../docker-compose.yml -f docker-compose.haystack.yml up -d

echo ""
echo "4. Waiting for services to be ready..."
sleep 10

echo ""
echo "5. Testing Haystack RAG service health..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health 2>/dev/null)
if [[ $HEALTH_RESPONSE == *"healthy"* ]]; then
    echo -e "${GREEN}✓${NC} Haystack service is healthy"
    if [[ $HEALTH_RESPONSE == *"unified"* ]]; then
        echo -e "${GREEN}✓${NC} Running in unified mode (with PostgreSQL)"
    elif [[ $HEALTH_RESPONSE == *"standalone"* ]]; then
        echo -e "${YELLOW}!${NC} Running in standalone mode"
    fi
else
    echo -e "${RED}✗${NC} Haystack service health check failed"
fi

echo ""
echo "6. Testing RAG endpoints..."

# Test document ingestion
echo "   Testing document ingestion..."
INGEST_RESPONSE=$(curl -s -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '[{"content": "This is a test document for RAG migration verification", "metadata": {"source": "migration_test"}}]' 2>/dev/null)

if [[ $INGEST_RESPONSE == *"success"* ]] || [[ $INGEST_RESPONSE == *"document_id"* ]]; then
    echo -e "${GREEN}✓${NC} Document ingestion working"
else
    echo -e "${RED}✗${NC} Document ingestion failed"
fi

# Test search
echo "   Testing search functionality..."
SEARCH_RESPONSE=$(curl -s -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test document", "top_k": 5, "search_type": "hybrid"}' 2>/dev/null)

if [[ $SEARCH_RESPONSE == *"results"* ]] || [[ $SEARCH_RESPONSE == *"hits"* ]]; then
    echo -e "${GREEN}✓${NC} Search functionality working"
else
    echo -e "${RED}✗${NC} Search functionality failed"
fi

echo ""
echo "7. Checking removed endpoints (should fail)..."
HIERARCHY_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/hierarchy \
  -H "Content-Type: application/json" \
  -d '{"document_id": "test"}' 2>/dev/null)

if [[ $HIERARCHY_RESPONSE == "404" ]] || [[ $HIERARCHY_RESPONSE == "405" ]]; then
    echo -e "${GREEN}✓${NC} Hierarchy endpoint properly removed (returns $HIERARCHY_RESPONSE)"
else
    echo -e "${RED}✗${NC} Hierarchy endpoint still exists (returns $HIERARCHY_RESPONSE)"
fi

echo ""
echo "======================================"
echo "Migration Verification Complete"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Check n8n UI for the updated Haystack RAG node"
echo "2. Update any existing workflows to use the new operations"
echo "3. Test with real documents and queries"
echo ""