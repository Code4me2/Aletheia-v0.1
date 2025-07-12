#!/bin/bash

# Aletheia v0.1 - Unified Stop Script
# This script provides a clean way to stop all services

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
echo -e "${BLUE}║       Aletheia v0.1 Stop Script        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

cd "$PROJECT_ROOT"

# Parse command line arguments
REMOVE_VOLUMES=false
REMOVE_IMAGES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --remove-volumes)
            REMOVE_VOLUMES=true
            shift
            ;;
        --remove-images)
            REMOVE_IMAGES=true
            shift
            ;;
        --clean)
            REMOVE_VOLUMES=true
            REMOVE_IMAGES=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --remove-volumes   Remove data volumes (WARNING: Deletes all data!)"
            echo "  --remove-images    Remove Docker images"
            echo "  --clean           Remove both volumes and images"
            echo "  --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                 # Stop containers, preserve data"
            echo "  $0 --clean         # Complete cleanup"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if services are running
echo -e "${YELLOW}🔍 Checking running services...${NC}"

# Check if Haystack services are running
HAYSTACK_RUNNING=false
if docker ps | grep -q "elasticsearch\|haystack-service"; then
    HAYSTACK_RUNNING=true
    echo -e "${BLUE}  Found Haystack/Elasticsearch services${NC}"
fi

# Stop services
echo ""
echo -e "${YELLOW}🛑 Stopping services...${NC}"

if [ "$HAYSTACK_RUNNING" = true ]; then
    echo -e "${BLUE}  Stopping all services including Haystack...${NC}"
    docker-compose -f docker-compose.yml -f n8n/docker-compose.haystack.yml down
else
    echo -e "${BLUE}  Stopping core services...${NC}"
    docker-compose down
fi

# Remove volumes if requested
if [ "$REMOVE_VOLUMES" = true ]; then
    echo ""
    echo -e "${RED}⚠️  WARNING: This will delete all data!${NC}"
    read -p "Are you sure you want to remove all volumes? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}🗑️  Removing volumes...${NC}"
        docker-compose down -v
        echo -e "${GREEN}✓ Volumes removed${NC}"
    else
        echo -e "${BLUE}  Skipping volume removal${NC}"
    fi
fi

# Remove images if requested
if [ "$REMOVE_IMAGES" = true ]; then
    echo ""
    echo -e "${YELLOW}🗑️  Removing images...${NC}"
    docker-compose down --rmi local
    echo -e "${GREEN}✓ Local images removed${NC}"
fi

# Final status
echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║    ✓ Aletheia v0.1 has been stopped    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

if [ "$REMOVE_VOLUMES" = false ]; then
    echo -e "${BLUE}💾 Data has been preserved${NC}"
    echo -e "   To start again: ${GREEN}./scripts/start-aletheia.sh${NC}"
else
    echo -e "${YELLOW}⚠️  All data has been removed${NC}"
    echo -e "   Fresh start: ${GREEN}./scripts/start-aletheia.sh${NC}"
fi
echo ""