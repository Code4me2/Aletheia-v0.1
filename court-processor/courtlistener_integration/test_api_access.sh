#!/bin/bash
# Test CourtListener API access and permissions

echo "Testing CourtListener API Access"
echo "================================="

source ../../.env

if [ -z "$COURTLISTENER_API_TOKEN" ]; then
    echo "Error: COURTLISTENER_API_TOKEN not set"
    exit 1
fi

BASE_URL="https://www.courtlistener.com/api/rest/v4"

echo "1. Testing basic API access..."
curl -s -H "Authorization: Token $COURTLISTENER_API_TOKEN" \
     -H "User-Agent: Aletheia-v0.1/1.0" \
     "${BASE_URL}/" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    if 'courts' in data:
        print('✓ API connection successful')
    else:
        print('✗ Unexpected API response')
        print(json.dumps(data, indent=2)[:200])
except Exception as e:
    print(f'✗ Error: {e}')
"

echo ""
echo "2. Testing courts endpoint..."
curl -s -H "Authorization: Token $COURTLISTENER_API_TOKEN" \
     "${BASE_URL}/courts/txed/" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    if 'full_name' in data:
        print(f'✓ Court access working: {data[\"full_name\"]}')
    else:
        print('✗ Court access failed')
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f'✗ Error: {e}')
"

echo ""
echo "3. Testing dockets endpoint..."
curl -s -H "Authorization: Token $COURTLISTENER_API_TOKEN" \
     "${BASE_URL}/dockets/?court=txed&page_size=1" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    if 'results' in data:
        print(f'✓ Dockets access working: {data[\"count\"]} dockets available')
    else:
        print('✗ Dockets access failed')
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f'✗ Error: {e}')
"

echo ""
echo "4. Testing docket-entries endpoint..."
# First get a docket ID
DOCKET_ID=$(curl -s -H "Authorization: Token $COURTLISTENER_API_TOKEN" \
     "${BASE_URL}/dockets/?court=txed&page_size=1" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    if 'results' in data and data['results']:
        print(data['results'][0]['id'])
except:
    pass
")

if [ -n "$DOCKET_ID" ]; then
    curl -s -H "Authorization: Token $COURTLISTENER_API_TOKEN" \
         "${BASE_URL}/docket-entries/?docket=${DOCKET_ID}&page_size=1" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    if 'results' in data:
        print(f'✓ Docket entries access working')
    else:
        print('✗ Docket entries access failed')
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f'✗ Error: {e}')
"
else
    echo "✗ Could not get docket ID for testing"
fi

echo ""
echo "5. Testing opinions endpoint..."
curl -s -H "Authorization: Token $COURTLISTENER_API_TOKEN" \
     "${BASE_URL}/opinions/?cluster__docket__court=txed&page_size=1" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    if 'results' in data:
        print(f'✓ Opinions access working: {data[\"count\"]} opinions available')
    else:
        print('✗ Opinions access failed')
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f'✗ Error: {e}')
"

echo ""
echo "6. Testing search endpoint for transcripts..."
curl -s -H "Authorization: Token $COURTLISTENER_API_TOKEN" \
     "${BASE_URL}/search/?q=transcript&court=txed&type=r&page_size=5" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    if 'results' in data:
        print(f'✓ Search working: {data[\"count\"]} results for \"transcript\"')
        if data['results']:
            print('  Sample results:')
            for r in data['results'][:3]:
                print(f'    - {r.get(\"caseName\", \"Unknown\")}')
    else:
        print('✗ Search failed')
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f'✗ Error: {e}')
"

echo ""
echo "================================="
echo "Note: RECAP document access may require special permissions"
echo "We can still search for transcripts in docket entries and opinions"