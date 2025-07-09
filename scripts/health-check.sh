#!/bin/bash
# Health check script for Aletheia services
# Usage: ./scripts/health-check.sh [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Environment
ENVIRONMENT=${1:-development}

# Base URL based on environment
case $ENVIRONMENT in
  production)
    BASE_URL="https://aletheia.example.com"
    ;;
  staging)
    BASE_URL="https://staging.aletheia.example.com"
    ;;
  *)
    BASE_URL="http://localhost:8080"
    ;;
esac

echo -e "${YELLOW}Running health checks for ${ENVIRONMENT} environment...${NC}"

# Track failures
FAILED_CHECKS=0

# Function to check endpoint
check_endpoint() {
  local name=$1
  local url=$2
  local expected_status=${3:-200}
  
  status=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")
  
  if [ "$status" = "$expected_status" ]; then
    echo -e "${GREEN}✓ $name is healthy (HTTP $status)${NC}"
    return 0
  else
    echo -e "${RED}✗ $name is unhealthy (HTTP $status, expected $expected_status)${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
    return 1
  fi
}

# Check services
check_endpoint "Web UI" "${BASE_URL}/"
check_endpoint "n8n Service" "${BASE_URL}/n8n/healthz"
check_endpoint "Lawyer Chat" "${BASE_URL}/chat/api/csrf"
check_endpoint "AI Portal" "${BASE_URL}:8085/" 200 || true  # Optional service

# Database check (only for local/staging)
if [ "$ENVIRONMENT" != "production" ]; then
  if docker-compose exec -T db pg_isready > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Database is healthy${NC}"
  else
    echo -e "${RED}✗ Database is unhealthy${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
  fi
fi

# Check Haystack service (if deployed)
check_endpoint "Haystack API" "${BASE_URL}:8000/health" 200 || true

# Summary
echo ""
if [ $FAILED_CHECKS -eq 0 ]; then
  echo -e "${GREEN}✅ All health checks passed!${NC}"
  exit 0
else
  echo -e "${RED}❌ $FAILED_CHECKS health checks failed${NC}"
  exit 1
fi