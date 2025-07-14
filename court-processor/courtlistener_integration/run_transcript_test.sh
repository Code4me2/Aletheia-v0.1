#!/bin/bash
# Test script for RECAP transcript functionality

set -e

echo "================================"
echo "RECAP Transcript Test Runner"
echo "================================"
echo ""

# Check if API token is set
if [ -z "$COURTLISTENER_API_TOKEN" ]; then
    echo "Error: COURTLISTENER_API_TOKEN not set in environment"
    echo "Please add it to your .env file"
    exit 1
fi

# Create data directories
mkdir -p /data/courtlistener
mkdir -p /data/logs

echo "1. Testing RECAP API endpoints..."
python3 test_recap_api.py

echo ""
echo "2. Running small test download (last 30 days, transcripts only)..."
python3 bulk_download_enhanced.py \
    --courts ded \
    --days 30 \
    --transcripts-only

echo ""
echo "3. Loading data into PostgreSQL..."
# First ensure the schema exists
if [ -f "../scripts/add_recap_schema.sql" ]; then
    echo "   Creating RECAP schema..."
    psql $DATABASE_URL -f ../scripts/add_recap_schema.sql
fi

# Load the data
python3 load_recap_to_postgres.py --court ded

echo ""
echo "================================"
echo "Test Complete!"
echo "================================"
echo ""
echo "To view transcript data in the database:"
echo "  psql \$DATABASE_URL -c 'SELECT * FROM court_data.transcript_documents LIMIT 5;'"
echo ""
echo "To see transcript statistics:"
echo "  psql \$DATABASE_URL -c 'SELECT * FROM court_data.recap_stats;'"