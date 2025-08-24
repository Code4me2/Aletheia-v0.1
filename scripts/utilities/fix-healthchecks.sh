#!/bin/bash

# Script to recreate containers with updated health checks
# This is needed when health check configurations change in docker-compose.yml

set -e

echo "====================================="
echo "  Fixing Container Health Checks"
echo "====================================="
echo ""
echo "This script will recreate containers to apply updated health check configurations."
echo "WARNING: This will briefly interrupt services."
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

echo ""
echo "Recreating containers with updated health checks..."

# Services that need health check updates
SERVICES_TO_RECREATE="ai-portal ai-portal-nginx lawyer-chat"

for service in $SERVICES_TO_RECREATE; do
    echo ""
    echo "Recreating $service..."
    docker-compose up -d --force-recreate --no-deps $service
    
    # Wait a moment for the container to start
    sleep 2
    
    # Check if health check is now present
    container_name=$(docker-compose ps -q $service)
    if [ -n "$container_name" ]; then
        health_status=$(docker inspect --format='{{if .State.Health}}configured{{else}}not configured{{end}}' $container_name 2>/dev/null || echo "error")
        echo "Health check for $service: $health_status"
    fi
done

echo ""
echo "====================================="
echo "  Health Check Fix Complete"
echo "====================================="
echo ""
echo "Run './dev status' to verify health checks are working."