#!/bin/bash
# Rollback script for Aletheia-v0.1
# Usage: ./scripts/rollback.sh [staging|production] [version]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parameters
ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}

# Validate environment
if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    echo -e "${RED}Error: Invalid environment. Use 'staging' or 'production'${NC}"
    exit 1
fi

echo -e "${YELLOW}Rolling back Aletheia-v0.1 ${ENVIRONMENT} to version ${VERSION}...${NC}"

# Load environment variables
if [ -f ".env.${ENVIRONMENT}" ]; then
    cp ".env.${ENVIRONMENT}" .env
else
    echo -e "${RED}Error: .env.${ENVIRONMENT} file not found${NC}"
    exit 1
fi

# Stop current services
echo -e "${YELLOW}Stopping current services...${NC}"
docker-compose -f docker-compose.yml -f "docker-compose.${ENVIRONMENT}.yml" down

# Get registry configuration
REGISTRY="${DOCKER_REGISTRY:-ghcr.io}"
IMAGE_PREFIX="${IMAGE_PREFIX:-$GITHUB_REPOSITORY}"

# Pull specific version if not latest
if [ "$VERSION" != "latest" ]; then
    echo -e "${YELLOW}Pulling version ${VERSION}...${NC}"
    
    # Pull versioned images
    for service in web court-processor lawyer-chat ai-portal haystack; do
        IMAGE="${REGISTRY}/${IMAGE_PREFIX}/${service}:${VERSION}"
        echo "Pulling ${IMAGE}..."
        docker pull "${IMAGE}" || {
            echo -e "${RED}Failed to pull ${IMAGE}${NC}"
            echo "Make sure the version exists in the registry"
            exit 1
        }
    done
    
    # Create temporary override file with specific versions
    cat > docker-compose.rollback.yml <<EOF
version: '3.8'
services:
  web:
    image: ${REGISTRY}/${IMAGE_PREFIX}/web:${VERSION}
  court-processor:
    image: ${REGISTRY}/${IMAGE_PREFIX}/court-processor:${VERSION}
  lawyer-chat:
    image: ${REGISTRY}/${IMAGE_PREFIX}/lawyer-chat:${VERSION}
  ai-portal:
    image: ${REGISTRY}/${IMAGE_PREFIX}/ai-portal:${VERSION}
EOF

    # If haystack service exists in environment file, add it
    if grep -q "haystack:" "docker-compose.${ENVIRONMENT}.yml" 2>/dev/null; then
        cat >> docker-compose.rollback.yml <<EOF
  haystack:
    image: ${REGISTRY}/${IMAGE_PREFIX}/haystack:${VERSION}
EOF
    fi
    
    # Start services with rollback version
    echo -e "${YELLOW}Starting services with rollback version ${VERSION}...${NC}"
    docker-compose -f docker-compose.yml -f "docker-compose.${ENVIRONMENT}.yml" -f docker-compose.rollback.yml up -d
    
    # Clean up temporary file
    rm -f docker-compose.rollback.yml
else
    # Use latest images
    echo -e "${YELLOW}Rolling back to latest version...${NC}"
    docker-compose -f docker-compose.yml -f "docker-compose.${ENVIRONMENT}.yml" pull
    docker-compose -f docker-compose.yml -f "docker-compose.${ENVIRONMENT}.yml" up -d
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Health checks
echo -e "${YELLOW}Verifying rollback...${NC}"
ROLLBACK_SUCCESS=1

# Use health check utility
"$SCRIPT_DIR/wait-for-health.sh" "http://localhost:8080" 120 5 || ROLLBACK_SUCCESS=0

if [ $ROLLBACK_SUCCESS -eq 1 ]; then
    echo -e "${GREEN}✅ Rollback completed successfully${NC}"
else
    echo -e "${RED}❌ Rollback failed. Manual intervention required.${NC}"
    echo "Check logs: docker-compose -f docker-compose.yml -f docker-compose.${ENVIRONMENT}.yml logs"
    exit 1
fi