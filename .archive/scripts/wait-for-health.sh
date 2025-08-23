#!/bin/bash
# Health check polling utility
# Usage: ./wait-for-health.sh <url> [timeout] [interval]

set -e

# Parameters
URL="${1}"
TIMEOUT="${2:-300}"  # Default 5 minutes
INTERVAL="${3:-5}"   # Default 5 seconds

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Validate parameters
if [ -z "$URL" ]; then
    echo -e "${RED}Error: URL is required${NC}"
    echo "Usage: $0 <url> [timeout] [interval]"
    exit 1
fi

# Function to check health
check_health() {
    curl -sf "$URL" > /dev/null 2>&1
    return $?
}

# Main polling loop
echo -e "${YELLOW}Waiting for $URL to be healthy...${NC}"
elapsed=0
while [ $elapsed -lt $TIMEOUT ]; do
    if check_health; then
        echo -e "${GREEN}✓ Service is healthy after ${elapsed}s${NC}"
        exit 0
    fi
    
    # Show progress every 10 seconds
    if [ $((elapsed % 10)) -eq 0 ] && [ $elapsed -gt 0 ]; then
        echo -e "${YELLOW}Still waiting... (${elapsed}s elapsed)${NC}"
    fi
    
    sleep $INTERVAL
    elapsed=$((elapsed + INTERVAL))
done

# Timeout reached
echo -e "${RED}✗ Service failed to become healthy after ${TIMEOUT}s${NC}"
exit 1