#!/bin/bash

# Source port configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/port-config.sh"

echo "Checking Aletheia-v0.1 Services..."
echo "================================"

# Check each service using dynamic ports
services=(
    "$(get_service_url web)|Main Web"
    "$(get_service_url ai-portal)|AI Portal"
    "$(get_service_url chat)|Lawyer Chat"
    "$(get_service_url n8n)/healthz|n8n"
)

for service in "${services[@]}"; do
    IFS='|' read -r url name <<< "$service"
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    if [ "$response" = "200" ] || [ "$response" = "401" ]; then
        echo "✓ $name ($url) - OK"
    else
        echo "✗ $name ($url) - Failed (HTTP $response)"
    fi
done

echo "================================"
echo "Container Status:"
echo "================================"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(ai-portal|lawyer-chat|n8n|web|db|court)" || echo "No matching containers found"
