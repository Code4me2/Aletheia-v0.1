#!/bin/bash
# Deployment script for Aletheia-v0.1
# Usage: ./scripts/deploy.sh [staging|production]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default environment
ENVIRONMENT=${1:-staging}

# Validate environment
if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    echo -e "${RED}Error: Invalid environment. Use 'staging' or 'production'${NC}"
    exit 1
fi

echo -e "${GREEN}Deploying Aletheia-v0.1 to ${ENVIRONMENT}...${NC}"

# Check if required files exist
if [ ! -f ".env.${ENVIRONMENT}" ]; then
    echo -e "${RED}Error: .env.${ENVIRONMENT} file not found${NC}"
    exit 1
fi

if [ ! -f "docker-compose.${ENVIRONMENT}.yml" ]; then
    echo -e "${RED}Error: docker-compose.${ENVIRONMENT}.yml file not found${NC}"
    exit 1
fi

# Load environment variables
cp ".env.${ENVIRONMENT}" .env
echo -e "${GREEN}✓ Environment variables loaded${NC}"

# Build images
echo -e "${YELLOW}Building Docker images...${NC}"
docker-compose -f docker-compose.yml -f "docker-compose.${ENVIRONMENT}.yml" build --parallel

# Run database migrations (if needed)
echo -e "${YELLOW}Running database migrations...${NC}"
docker-compose -f docker-compose.yml -f "docker-compose.${ENVIRONMENT}.yml" run --rm db bash -c "
    until pg_isready -h db -U \$POSTGRES_USER; do
        echo 'Waiting for database...'
        sleep 2
    done
"

# Deploy services
echo -e "${YELLOW}Starting services...${NC}"
docker-compose -f docker-compose.yml -f "docker-compose.${ENVIRONMENT}.yml" up -d

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Health checks
echo -e "${YELLOW}Running health checks...${NC}"
HEALTH_CHECK_FAILED=0

# Use health check utility for all services
"$SCRIPT_DIR/wait-for-health.sh" "http://localhost:8080" 120 5 || HEALTH_CHECK_FAILED=1
"$SCRIPT_DIR/wait-for-health.sh" "http://localhost:8080/n8n/healthz" 180 5 || HEALTH_CHECK_FAILED=1
"$SCRIPT_DIR/wait-for-health.sh" "http://localhost:8080/chat/api/csrf" 120 5 || HEALTH_CHECK_FAILED=1

# Check database separately (different protocol)
echo -e "${YELLOW}Checking database health...${NC}"
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker-compose -f docker-compose.yml -f "docker-compose.${ENVIRONMENT}.yml" exec -T db pg_isready > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Database is healthy after ${elapsed}s${NC}"
        break
    fi
    sleep 5
    elapsed=$((elapsed + 5))
done

if [ $elapsed -ge $timeout ]; then
    echo -e "${RED}✗ Database health check failed after ${timeout}s${NC}"
    HEALTH_CHECK_FAILED=1
fi

# Final status
if [ $HEALTH_CHECK_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Deployment to ${ENVIRONMENT} completed successfully!${NC}"
    echo -e "${GREEN}Services are available at:${NC}"
    echo "  - Web UI: http://localhost:8080"
    echo "  - n8n UI: http://localhost:8080/n8n/"
    echo "  - AI Chat: http://localhost:8080/chat"
    
    if [ "$ENVIRONMENT" == "production" ]; then
        echo "  - Prometheus: http://localhost:9090"
        echo "  - Grafana: http://localhost:3000"
    fi
else
    echo -e "${RED}❌ Deployment completed with errors. Check the logs:${NC}"
    echo "  docker-compose -f docker-compose.yml -f docker-compose.${ENVIRONMENT}.yml logs"
    exit 1
fi