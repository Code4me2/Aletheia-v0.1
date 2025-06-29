#!/bin/bash
echo "Checking Aletheia-v0.1 Services..."
echo "================================"

# Check each service
services=(
    "http://localhost:8080|Main Web"
    "http://localhost:8085|AI Portal"
    "http://localhost:8080/chat|Lawyer Chat"
    "http://localhost:8080/n8n/healthz|n8n"
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

echo "================================"
echo "Current Git Remote:"
git remote get-url origin 2>/dev/null || echo "No origin remote"
echo "Upstream: $(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo 'Not set')"