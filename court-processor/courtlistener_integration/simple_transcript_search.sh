#!/bin/bash
# Simple transcript search using curl

echo "=========================================="
echo "CourtListener Transcript Search"
echo "=========================================="

# Load API token
source ../../.env

if [ -z "$COURTLISTENER_API_TOKEN" ]; then
    echo "Error: COURTLISTENER_API_TOKEN not set"
    exit 1
fi

BASE_URL="https://www.courtlistener.com/api/rest/v4"
OUTPUT_DIR="../../data/courtlistener/transcript_samples"
mkdir -p "$OUTPUT_DIR"

# Function to make API calls
api_call() {
    local endpoint=$1
    local params=$2
    
    curl -s -H "Authorization: Token $COURTLISTENER_API_TOKEN" \
         -H "User-Agent: Aletheia-v0.1/1.0" \
         "${BASE_URL}/${endpoint}?${params}"
}

echo "Searching for recent transcripts..."
echo ""

# Search for RECAP documents with "transcript" in description
COURTS=("txed" "cand" "nysd")

for court in "${COURTS[@]}"; do
    echo "Searching $court for transcripts..."
    
    # Search for transcript documents
    response=$(api_call "recap-documents/" "description__icontains=transcript&docket_entry__docket__court=${court}&page_size=10&ordering=-date_created")
    
    if [ $? -eq 0 ]; then
        # Save response
        echo "$response" > "${OUTPUT_DIR}/${court}_transcripts.json"
        
        # Parse and display summary using Python
        python3 -c "
import json
import sys

try:
    data = json.loads('''${response}''')
    count = data.get('count', 0)
    print(f'  Found {count} transcript documents')
    
    if 'results' in data and data['results']:
        print('  Recent transcripts:')
        for doc in data['results'][:3]:
            desc = doc.get('description', 'No description')[:80]
            pages = doc.get('page_count', 'Unknown')
            print(f'    - {desc}... ({pages} pages)')
except Exception as e:
    print(f'  Error parsing response: {e}')
"
    else
        echo "  Error querying API"
    fi
    
    echo ""
    sleep 1  # Rate limiting
done

# Try a different approach - search docket entries
echo "Alternative search - checking docket entries..."

for court in "${COURTS[@]}"; do
    echo "Checking recent entries in $court..."
    
    # Get recent docket entries
    response=$(api_call "docket-entries/" "docket__court=${court}&description__icontains=transcript&page_size=10&ordering=-date_filed")
    
    if [ $? -eq 0 ]; then
        echo "$response" > "${OUTPUT_DIR}/${court}_entries_with_transcripts.json"
        
        # Count results
        count=$(echo "$response" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(data.get('count', 0))
except:
    print(0)
")
        echo "  Found $count docket entries mentioning transcripts"
    fi
    
    echo ""
    sleep 1
done

echo "=========================================="
echo "Search complete!"
echo "Results saved in: $OUTPUT_DIR"
echo ""
echo "To view results:"
echo "  ls -la $OUTPUT_DIR"
echo "  cat $OUTPUT_DIR/txed_transcripts.json | python3 -m json.tool | head -50"
echo "=========================================="