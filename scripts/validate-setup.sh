#!/bin/bash

# Aletheia Setup Validation Script
# This script checks your environment without making any changes
# Safe to run at any time

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project name for docker containers
PROJECT_NAME=${COMPOSE_PROJECT_NAME:-aletheia_development}

echo "========================================="
echo "Aletheia Setup Validation"
echo "========================================="
echo ""

# Track overall health
ISSUES_FOUND=0

# Function to check a condition
check() {
    local description="$1"
    local command="$2"
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $description"
        return 0
    else
        echo -e "${RED}✗${NC} $description"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
        return 1
    fi
}

# Function to warn about a condition
warn() {
    local description="$1"
    local command="$2"
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠${NC}  $description"
        return 0
    else
        return 1
    fi
}

# 1. Check Docker
echo "1. Docker Environment"
echo "---------------------"
check "Docker is installed" "which docker"
check "Docker daemon is running" "docker info"
check "Docker Compose is installed" "which docker-compose || docker compose version"
echo ""

# 2. Check required files
echo "2. Required Files"
echo "-----------------"
check ".env file exists" "test -f .env"
check "docker-compose.yml exists" "test -f docker-compose.yml"
check "nginx/nginx.conf exists" "test -f nginx/nginx.conf"

# Warn if using default .env
if [ -f .env ] && [ -f .env.example ]; then
    if diff -q .env .env.example > /dev/null 2>&1; then
        warn ".env file appears unchanged from .env.example (passwords should be changed)" "false"
    fi
fi
echo ""

# 3. Check ports
echo "3. Port Availability"
echo "--------------------"
echo "Checking if required ports are available or used by Aletheia..."

check_port() {
    local port=$1
    local service=$2
    
    # Check if port is in use
    if lsof -i :$port > /dev/null 2>&1; then
        # Check if it's used by our container - look for the port mapping in docker ps
        if docker ps --format "{{.Ports}}" | grep -q "0.0.0.0:$port->\|:::$port->"; then
            echo -e "${GREEN}✓${NC} Port $port: In use by Aletheia ($service)"
        else
            echo -e "${RED}✗${NC} Port $port: In use by another process (needed for $service)"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
    else
        echo -e "${YELLOW}⚠${NC}  Port $port: Available (needed for $service)"
    fi
}

check_port 8080 "Main web interface"
check_port 5678 "n8n workflows"
check_port 8085 "AI Portal"
check_port 5432 "PostgreSQL"
echo ""

# 4. Check running containers
echo "4. Container Status"
echo "-------------------"

if docker ps > /dev/null 2>&1; then
    # Get list of expected services from docker-compose.yml
    EXPECTED_SERVICES=(web db n8n redis lawyer-chat ai-portal court-processor)
    
    for service in "${EXPECTED_SERVICES[@]}"; do
        # Find container with this service name (use word boundary to avoid partial matches)
        container=$(docker ps --format "{{.Names}}" | grep -E "${PROJECT_NAME}-${service}-[0-9]" | head -1)
        if [ ! -z "$container" ]; then
            # Check health status
            health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "none")
            if [ "$health" = "healthy" ]; then
                echo -e "${GREEN}✓${NC} $service: Running and healthy"
            elif [ "$health" = "none" ] || [ -z "$health" ]; then
                echo -e "${GREEN}✓${NC} $service: Running (no health check)"
            else
                echo -e "${YELLOW}⚠${NC}  $service: Running but $health"
            fi
        else
            echo -e "${YELLOW}⚠${NC}  $service: Not running"
        fi
    done
else
    echo -e "${RED}✗${NC} Unable to check container status"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi
echo ""

# 5. Check nginx configuration
echo "5. Nginx Configuration"
echo "----------------------"

# Check if nginx container is running
nginx_container=$(docker ps --format "{{.Names}}" | grep -E "${PROJECT_NAME}-web-[0-9]" | head -1)
if [ ! -z "$nginx_container" ]; then
    # Test nginx configuration
    if docker exec "$nginx_container" nginx -t > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Nginx configuration is valid"
    else
        echo -e "${RED}✗${NC} Nginx configuration has errors"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
    
    # Check if nginx needs reload (by checking if lawyer-chat is newer than nginx)
    nginx_start=$(docker inspect --format='{{.State.StartedAt}}' "$nginx_container" 2>/dev/null)
    lawyer_container=$(docker ps --format "{{.Names}}" | grep -E "${PROJECT_NAME}-lawyer-chat-[0-9]" | head -1)
    
    if [ ! -z "$lawyer_container" ]; then
        lawyer_start=$(docker inspect --format='{{.State.StartedAt}}' "$lawyer_container" 2>/dev/null)
        
        if [ ! -z "$lawyer_start" ] && [ ! -z "$nginx_start" ]; then
            if [[ "$lawyer_start" > "$nginx_start" ]]; then
                warn "Nginx may need reload (lawyer-chat restarted after nginx)" "false"
                echo "  Fix: docker exec $nginx_container nginx -s reload"
            fi
        fi
    fi
else
    echo -e "${YELLOW}⚠${NC}  Nginx container not running"
fi
echo ""

# 6. Test endpoints
echo "6. Service Endpoints"
echo "--------------------"

test_endpoint() {
    local url=$1
    local description=$2
    
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "^[23]"; then
        echo -e "${GREEN}✓${NC} $description: Accessible"
    else
        echo -e "${YELLOW}⚠${NC}  $description: Not accessible"
    fi
}

if docker ps --format "{{.Names}}" | grep -q "web"; then
    test_endpoint "http://localhost:8080/health" "Main health check"
    test_endpoint "http://localhost:8080/" "Web interface"
    test_endpoint "http://localhost:8080/chat" "Lawyer chat"
    test_endpoint "http://localhost:8080/n8n/" "n8n workflows"
fi
echo ""

# 7. Environment Variables
echo "7. Environment Variables"
echo "------------------------"

if [ -f .env ]; then
    # Check for critical variables
    check_env_var() {
        local var=$1
        local description=$2
        
        if grep -q "^${var}=" .env; then
            value=$(grep "^${var}=" .env | cut -d'=' -f2)
            if [[ "$value" == *"CHANGE_ME"* ]] || [[ "$value" == *"GENERATE"* ]] || [[ "$value" == *"YOUR"* ]]; then
                echo -e "${YELLOW}⚠${NC}  $description: Using default value (should be changed)"
            else
                echo -e "${GREEN}✓${NC} $description: Configured"
            fi
        else
            echo -e "${RED}✗${NC} $description: Not set"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
    }
    
    check_env_var "DB_PASSWORD" "Database password"
    check_env_var "N8N_ENCRYPTION_KEY" "n8n encryption key"
    check_env_var "NEXTAUTH_SECRET" "NextAuth secret"
else
    echo -e "${RED}✗${NC} .env file not found"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi
echo ""

# Summary
echo "========================================="
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo "Your Aletheia setup appears to be correctly configured."
else
    echo -e "${RED}✗ Found $ISSUES_FOUND issue(s)${NC}"
    echo ""
    echo "Quick fixes:"
    echo "1. If .env is missing: cp .env.example .env"
    echo "2. If containers not running: docker-compose up -d"
    echo "3. If nginx needs reload: docker exec aletheia_development-web-1 nginx -s reload"
    echo "4. If ports are in use: Check what's using them with: lsof -i :<port>"
    echo ""
    echo "For more help, see DEVELOPER_ONBOARDING.md"
fi
echo "========================================="

exit $ISSUES_FOUND