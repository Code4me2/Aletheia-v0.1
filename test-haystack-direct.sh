#!/bin/bash

echo "Testing Haystack Search API directly from n8n container..."
echo

# Test 1: Direct API call with correct parameters (should work)
echo "Test 1: Correct parameters (should succeed)"
docker exec aletheia-n8n-1 wget -qO- \
  --post-data='{"query":"test","top_k":5,"search_type":"hybrid"}' \
  --header='Content-Type: application/json' \
  http://haystack-service:8000/search 2>&1 | jq .

echo
echo "Test 2: Wrong parameters that n8n was sending (should fail with 422)"
docker exec aletheia-n8n-1 wget -qO- \
  --post-data='{"query":"test","topK":5,"use_hybrid":true}' \
  --header='Content-Type: application/json' \
  http://haystack-service:8000/search 2>&1

echo
echo "Test 3: Check if haystack-service is resolvable from n8n"
docker exec aletheia-n8n-1 ping -c 1 haystack-service 2>&1 | grep -E "(PING|bytes from)"