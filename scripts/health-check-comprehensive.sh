#!/bin/bash

# Aletheia v0.1 - Comprehensive Health Check Script
# Checks the status of all services and provides detailed diagnostics

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Aletheia v0.1 Health Check Report    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

cd "$PROJECT_ROOT"

# Function to check service health
check_service() {
    local service_name=$1
    local check_command=$2
    local url=$3
    
    echo -n "  $service_name: "
    
    # Check if container is running
    if ! docker-compose ps | grep -q "$service_name.*Up"; then
        echo -e "${RED}✗ Container not running${NC}"
        return 1
    fi
    
    # Check service health
    if eval "$check_command" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
        if [ -n "$url" ]; then
            echo -e "    └─ URL: ${BLUE}$url${NC}"
        fi
        return 0
    else
        echo -e "${YELLOW}⚠️  Container running but service not responding${NC}"
        return 1
    fi
}

# Check Docker daemon
echo -e "${YELLOW}🐋 Docker Status:${NC}"
if docker info >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓ Docker daemon is running${NC}"
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | sed 's/,$//')
    echo -e "    └─ Version: ${BLUE}$DOCKER_VERSION${NC}"
else
    echo -e "  ${RED}✗ Docker daemon is not running${NC}"
    exit 1
fi

# Check core services
echo ""
echo -e "${YELLOW}📦 Core Services:${NC}"

SERVICES_HEALTHY=0
SERVICES_TOTAL=0

# PostgreSQL
((SERVICES_TOTAL++))
if check_service "db" "docker-compose exec -T db pg_isready -U aletheia_user" ""; then
    ((SERVICES_HEALTHY++))
fi

# n8n
((SERVICES_TOTAL++))
if check_service "n8n" "curl -s http://localhost:5678/healthz" "http://localhost:8080/n8n/"; then
    ((SERVICES_HEALTHY++))
    
    # Check workflow status
    echo -n "    └─ Workflows: "
    WORKFLOW_COUNT=$(curl -s http://localhost:5678/rest/workflows 2>/dev/null | jq '. | length' || echo "0")
    ACTIVE_WORKFLOWS=$(curl -s http://localhost:5678/rest/workflows 2>/dev/null | jq '[.[] | select(.active == true)] | length' || echo "0")
    echo -e "${BLUE}$WORKFLOW_COUNT total, $ACTIVE_WORKFLOWS active${NC}"
fi

# Web interface
((SERVICES_TOTAL++))
if check_service "web" "curl -s http://localhost:8080" "http://localhost:8080"; then
    ((SERVICES_HEALTHY++))
fi

# Lawyer Chat
((SERVICES_TOTAL++))
if check_service "lawyer-chat" "curl -s http://localhost:8080/chat/api/csrf" "http://localhost:8080/chat"; then
    ((SERVICES_HEALTHY++))
fi

# AI Portal
((SERVICES_TOTAL++))
if check_service "ai-portal" "curl -s http://localhost:8085" "http://localhost:8085"; then
    ((SERVICES_HEALTHY++))
fi

# Redis
((SERVICES_TOTAL++))
if check_service "redis" "docker-compose exec -T redis redis-cli ping" ""; then
    ((SERVICES_HEALTHY++))
fi

# Check optional services
echo ""
echo -e "${YELLOW}📦 Optional Services:${NC}"

OPTIONAL_HEALTHY=0
OPTIONAL_TOTAL=0

# Elasticsearch
if docker ps | grep -q "elasticsearch"; then
    ((OPTIONAL_TOTAL++))
    if check_service "elasticsearch" "curl -s http://localhost:9200/_cluster/health" "http://localhost:9200"; then
        ((OPTIONAL_HEALTHY++))
        # Get cluster status
        CLUSTER_STATUS=$(curl -s http://localhost:9200/_cluster/health 2>/dev/null | jq -r '.status' || echo "unknown")
        echo -e "    └─ Cluster status: ${BLUE}$CLUSTER_STATUS${NC}"
    fi
else
    echo -e "  Elasticsearch: ${BLUE}Not deployed${NC}"
fi

# Haystack
if docker ps | grep -q "haystack-service"; then
    ((OPTIONAL_TOTAL++))
    if check_service "haystack-service" "curl -s http://localhost:8000/health" "http://localhost:8000/docs"; then
        ((OPTIONAL_HEALTHY++))
    fi
else
    echo -e "  Haystack API: ${BLUE}Not deployed${NC}"
fi

# Court Processor
if docker ps | grep -q "court-processor"; then
    ((OPTIONAL_TOTAL++))
    if check_service "court-processor" "docker-compose ps court-processor | grep Up" ""; then
        ((OPTIONAL_HEALTHY++))
    fi
else
    echo -e "  Court Processor: ${BLUE}Not deployed${NC}"
fi

# Check disk usage
echo ""
echo -e "${YELLOW}💾 Disk Usage:${NC}"
DOCKER_DISK=$(docker system df --format "table {{.Type}}\t{{.Size}}\t{{.Reclaimable}}" | tail -n +2)
echo "$DOCKER_DISK" | while IFS=$'\t' read -r type size reclaimable; do
    echo -e "  $type: ${BLUE}$size${NC} (reclaimable: $reclaimable)"
done

# Check container logs for errors
echo ""
echo -e "${YELLOW}📋 Recent Errors (last 5 minutes):${NC}"
ERROR_COUNT=0
for service in web db n8n lawyer-chat ai-portal redis; do
    if docker-compose ps | grep -q "$service.*Up"; then
        ERRORS=$(docker-compose logs --tail=100 --since=5m $service 2>&1 | grep -iE "error|fatal|critical" | wc -l || echo "0")
        if [ "$ERRORS" -gt 0 ]; then
            echo -e "  ${RED}$service: $ERRORS errors${NC}"
            ((ERROR_COUNT+=ERRORS))
        fi
    fi
done
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "  ${GREEN}✓ No recent errors detected${NC}"
fi

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║            Health Summary              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"

TOTAL_SERVICES=$((SERVICES_TOTAL + OPTIONAL_TOTAL))
TOTAL_HEALTHY=$((SERVICES_HEALTHY + OPTIONAL_HEALTHY))

if [ "$TOTAL_HEALTHY" -eq "$TOTAL_SERVICES" ]; then
    echo -e "${GREEN}✓ All services are healthy ($TOTAL_HEALTHY/$TOTAL_SERVICES)${NC}"
elif [ "$SERVICES_HEALTHY" -eq "$SERVICES_TOTAL" ]; then
    echo -e "${GREEN}✓ Core services are healthy ($SERVICES_HEALTHY/$SERVICES_TOTAL)${NC}"
    if [ "$OPTIONAL_TOTAL" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Optional services: $OPTIONAL_HEALTHY/$OPTIONAL_TOTAL healthy${NC}"
    fi
else
    echo -e "${RED}✗ Service issues detected${NC}"
    echo -e "  Core: $SERVICES_HEALTHY/$SERVICES_TOTAL healthy"
    echo -e "  Optional: $OPTIONAL_HEALTHY/$OPTIONAL_TOTAL healthy"
fi

# Recommendations
if [ "$TOTAL_HEALTHY" -lt "$TOTAL_SERVICES" ]; then
    echo ""
    echo -e "${YELLOW}💡 Recommendations:${NC}"
    echo -e "  1. Check logs: ${BLUE}docker-compose logs -f [service-name]${NC}"
    echo -e "  2. Restart unhealthy services: ${BLUE}docker-compose restart [service-name]${NC}"
    echo -e "  3. Full restart: ${BLUE}./scripts/stop-aletheia.sh && ./scripts/start-aletheia.sh${NC}"
fi

echo ""