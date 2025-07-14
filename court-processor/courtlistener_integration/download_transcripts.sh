#!/bin/bash
# Download transcripts from high-volume courts

set -e

# Load environment variables
export $(grep -v '^#' ../../.env | xargs)

# Check if API token is set
if [ -z "$COURTLISTENER_API_TOKEN" ]; then
    echo "Error: COURTLISTENER_API_TOKEN not set in .env"
    exit 1
fi

echo "=========================================="
echo "CourtListener Transcript Download"
echo "=========================================="
echo "Courts: Texas Eastern, N.D. California, S.D. New York"
echo "Period: Last 90 days"
echo "Type: Transcripts only"
echo ""

# Create log file with timestamp
LOG_FILE="../../data/logs/transcript_download_$(date +%Y%m%d_%H%M%S).log"
echo "Log file: $LOG_FILE"
echo ""

# Create a simple Python script to run the download
cat > run_download.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import after path is set
from bulk_download_enhanced import main

if __name__ == "__main__":
    # Set arguments for transcript-only download
    sys.argv = [
        'bulk_download_enhanced.py',
        '--courts', 'txed', 'cand', 'nysd',
        '--days', '90',
        '--transcripts-only'
    ]
    main()
EOF

echo "Starting transcript download..."
echo "This will take several hours. You can monitor progress in the log file."
echo ""

# Use the system Python with required packages installed
# Redirect paths to use local data directory
export DATA_DIR="../../data"
mkdir -p "$DATA_DIR/courtlistener" "$DATA_DIR/logs"

# Modify the script to use local paths
sed -i.bak 's|/data/|'"$DATA_DIR"'/|g' bulk_download_enhanced.py
sed -i.bak 's|/data/|'"$DATA_DIR"'/|g' run_download.py

# Try different Python execution methods
if command -v python3 &> /dev/null && python3 -c "import requests" 2>/dev/null; then
    echo "Using system python3 with requests installed"
    python3 run_download.py 2>&1 | tee "$LOG_FILE"
elif command -v python &> /dev/null && python -c "import requests" 2>/dev/null; then
    echo "Using system python with requests installed"
    python run_download.py 2>&1 | tee "$LOG_FILE"
else
    echo "Creating minimal download script without requests library..."
    
    # Create a curl-based downloader as fallback
    cat > minimal_transcript_download.py << 'EOFMIN'
#!/usr/bin/env python3
import os
import json
import subprocess
import time
from datetime import datetime, timedelta

API_TOKEN = os.environ.get('COURTLISTENER_API_TOKEN')
BASE_URL = "https://www.courtlistener.com/api/rest/v4/"
COURTS = ['txed', 'cand', 'nysd']

def api_call(endpoint, params=None):
    """Make API call using curl"""
    headers = [
        '-H', f'Authorization: Token {API_TOKEN}',
        '-H', 'User-Agent: Aletheia-v0.1/1.0'
    ]
    
    url = BASE_URL + endpoint
    if params:
        param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
        url += '?' + param_str
    
    cmd = ['curl', '-s'] + headers + [url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        print(f"Error calling {endpoint}: {result.stderr}")
        return None

def download_transcripts():
    """Download transcript metadata"""
    date_from = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    stats = {'courts': 0, 'documents': 0, 'transcripts': 0}
    
    for court in COURTS:
        print(f"\nProcessing {court}...")
        court_dir = f"../../data/courtlistener/{court}/recap_documents"
        os.makedirs(court_dir, exist_ok=True)
        
        # Get dockets
        params = {
            'court': court,
            'date_filed__gte': date_from,
            'page_size': 10
        }
        
        result = api_call('dockets/', params)
        if result and 'results' in result:
            print(f"Found {result.get('count', 0)} dockets")
            
            # Sample a few dockets for transcripts
            for docket in result['results'][:5]:
                # Get entries
                entries = api_call('docket-entries/', {'docket': docket['id'], 'page_size': 50})
                
                if entries and 'results' in entries:
                    for entry in entries['results']:
                        desc = entry.get('description', '').lower()
                        if 'transcript' in desc:
                            print(f"  Found potential transcript: {entry.get('description', '')[:80]}...")
                            stats['transcripts'] += 1
                            
                            # Save entry
                            filename = f"{court_dir}/transcript_entry_{entry['id']}.json"
                            with open(filename, 'w') as f:
                                json.dump(entry, f, indent=2)
                
                time.sleep(0.5)  # Rate limiting
        
        stats['courts'] += 1
    
    print(f"\n\nDownload Summary:")
    print(f"Courts processed: {stats['courts']}")
    print(f"Potential transcripts found: {stats['transcripts']}")

if __name__ == "__main__":
    download_transcripts()
EOFMIN
    
    python3 minimal_transcript_download.py 2>&1 | tee "$LOG_FILE"
fi

# Restore original files
if [ -f bulk_download_enhanced.py.bak ]; then
    mv bulk_download_enhanced.py.bak bulk_download_enhanced.py
fi
if [ -f run_download.py ]; then
    rm run_download.py
fi

echo ""
echo "=========================================="
echo "Download completed (or failed - check log)"
echo "Log file: $LOG_FILE"
echo "Data location: $DATA_DIR/courtlistener/"
echo "==========================================" 