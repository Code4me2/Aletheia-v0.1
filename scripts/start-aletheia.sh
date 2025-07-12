#!/bin/bash

# Aletheia v0.1 - Unified Startup Script
# This script provides a single command to start all services with minimal manual intervention

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
echo -e "${BLUE}║       Aletheia v0.1 Startup Script     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for service
wait_for_service() {
    local service_name=$1
    local check_command=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "  Waiting for $service_name"
    while [ $attempt -le $max_attempts ]; do
        if eval "$check_command" >/dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo -e " ${RED}✗${NC}"
    return 1
}

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

if ! command_exists docker; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    exit 1
fi

if ! command_exists docker-compose; then
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}✗ Docker daemon is not running${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites met${NC}"
echo ""

# Check for .env file
cd "$PROJECT_ROOT"

if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating from template...${NC}"
    cp .env.example .env
    
    # Generate secure random values
    echo -e "${YELLOW}🔐 Generating secure credentials...${NC}"
    
    # Generate random passwords and keys
    DB_PASSWORD=$(openssl rand -hex 16)
    N8N_ENCRYPTION_KEY=$(openssl rand -hex 32)
    NEXTAUTH_SECRET=$(openssl rand -hex 32)
    N8N_API_KEY=$(openssl rand -hex 16)
    N8N_API_SECRET=$(openssl rand -hex 32)
    
    # Update .env file with generated values
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/CHANGE_ME_STRONG_PASSWORD_32_CHARS/$DB_PASSWORD/g" .env
        sed -i '' "s/GENERATE_RANDOM_32_CHAR_HEX_STRING/$N8N_ENCRYPTION_KEY/g" .env
        sed -i '' "s/GENERATE_RANDOM_64_CHAR_STRING/$NEXTAUTH_SECRET/g" .env
        sed -i '' "s/GENERATE_RANDOM_API_KEY/$N8N_API_KEY/g" .env
        sed -i '' "s/GENERATE_RANDOM_API_SECRET/$N8N_API_SECRET/g" .env
    else
        # Linux
        sed -i "s/CHANGE_ME_STRONG_PASSWORD_32_CHARS/$DB_PASSWORD/g" .env
        sed -i "s/GENERATE_RANDOM_32_CHAR_HEX_STRING/$N8N_ENCRYPTION_KEY/g" .env
        sed -i "s/GENERATE_RANDOM_64_CHAR_STRING/$NEXTAUTH_SECRET/g" .env
        sed -i "s/GENERATE_RANDOM_API_KEY/$N8N_API_KEY/g" .env
        sed -i "s/GENERATE_RANDOM_API_SECRET/$N8N_API_SECRET/g" .env
    fi
    
    echo -e "${GREEN}✓ Generated secure credentials${NC}"
    echo -e "${YELLOW}⚠️  Please review .env file and add any missing API keys${NC}"
fi

# Parse command line arguments
INCLUDE_HAYSTACK=false
SKIP_WORKFLOW_IMPORT=false
FORCE_RECREATE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --with-haystack)
            INCLUDE_HAYSTACK=true
            shift
            ;;
        --skip-workflow-import)
            SKIP_WORKFLOW_IMPORT=true
            shift
            ;;
        --force-recreate)
            FORCE_RECREATE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --with-haystack         Include Haystack/Elasticsearch services"
            echo "  --skip-workflow-import  Skip automatic n8n workflow import"
            echo "  --force-recreate       Force recreate containers"
            echo "  --help                 Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                     # Start core services only"
            echo "  $0 --with-haystack     # Start all services including Haystack"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Start core services
echo ""
echo -e "${YELLOW}🚀 Starting core services...${NC}"

COMPOSE_CMD="docker-compose"
if [ "$FORCE_RECREATE" = true ]; then
    COMPOSE_CMD="$COMPOSE_CMD up -d --force-recreate"
else
    COMPOSE_CMD="$COMPOSE_CMD up -d"
fi

if [ "$INCLUDE_HAYSTACK" = true ]; then
    echo -e "${BLUE}  Including Haystack/Elasticsearch services${NC}"
    COMPOSE_FILES="-f docker-compose.yml -f n8n/docker-compose.haystack.yml"
    eval "$COMPOSE_CMD $COMPOSE_FILES"
else
    eval "$COMPOSE_CMD"
fi

# Wait for services to be ready
echo ""
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"

# Wait for database
wait_for_service "PostgreSQL" "docker-compose exec -T db pg_isready -U aletheia_user"

# Wait for n8n
wait_for_service "n8n" "curl -s http://localhost:5678/healthz"

# Wait for web interface
wait_for_service "Web Interface" "curl -s http://localhost:8080"

# Wait for lawyer-chat
wait_for_service "Lawyer Chat" "curl -s http://localhost:8080/chat/api/csrf"

if [ "$INCLUDE_HAYSTACK" = true ]; then
    # Wait for Elasticsearch
    wait_for_service "Elasticsearch" "curl -s http://localhost:9200/_cluster/health"
    
    # Wait for Haystack
    wait_for_service "Haystack API" "curl -s http://localhost:8000/health"
    
    # Setup Elasticsearch index if needed
    echo -e "${YELLOW}🔧 Setting up Elasticsearch index...${NC}"
    if [ -f "n8n/haystack-service/elasticsearch_setup.py" ]; then
        docker-compose exec -T haystack-service python /app/elasticsearch_setup.py || true
        echo -e "${GREEN}✓ Elasticsearch index setup complete${NC}"
    fi
fi

# Auto-import n8n workflow
if [ "$SKIP_WORKFLOW_IMPORT" = false ]; then
    echo ""
    echo -e "${YELLOW}📦 Importing n8n workflow...${NC}"
    
    # Wait a bit more for n8n to fully initialize
    sleep 5
    
    # Check if workflow already exists
    WORKFLOW_EXISTS=$(curl -s http://localhost:5678/rest/workflows 2>/dev/null | grep -c "Basic_workflow" || true)
    
    if [ "$WORKFLOW_EXISTS" -eq 0 ]; then
        echo -e "${BLUE}  Workflow not found, importing...${NC}"
        
        # Read workflow file
        WORKFLOW_JSON=$(cat "$PROJECT_ROOT/workflow_json/web_UI_basic" | jq -c .)
        
        # Import workflow via n8n API
        IMPORT_RESPONSE=$(curl -s -X POST http://localhost:5678/rest/workflows \
            -H "Content-Type: application/json" \
            -d "$WORKFLOW_JSON" 2>/dev/null)
        
        if echo "$IMPORT_RESPONSE" | grep -q '"id"'; then
            WORKFLOW_ID=$(echo "$IMPORT_RESPONSE" | jq -r '.id')
            echo -e "${GREEN}✓ Workflow imported successfully (ID: $WORKFLOW_ID)${NC}"
            
            # Activate the workflow
            echo -e "${YELLOW}  Activating workflow...${NC}"
            ACTIVATE_RESPONSE=$(curl -s -X PATCH "http://localhost:5678/rest/workflows/$WORKFLOW_ID" \
                -H "Content-Type: application/json" \
                -d '{"active": true}' 2>/dev/null)
            
            if echo "$ACTIVATE_RESPONSE" | grep -q '"active":true'; then
                echo -e "${GREEN}✓ Workflow activated${NC}"
            else
                echo -e "${YELLOW}⚠️  Could not activate workflow automatically${NC}"
                echo -e "${YELLOW}   Please activate it manually in n8n interface${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️  Could not import workflow automatically${NC}"
            echo -e "${YELLOW}   Please import manually from: workflow_json/web_UI_basic${NC}"
        fi
    else
        echo -e "${GREEN}✓ Workflow already exists${NC}"
    fi
fi

# Display status and access information
echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✓ Aletheia v0.1 is now running!   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}🌐 Access Points:${NC}"
echo -e "   Main Interface:    ${GREEN}http://localhost:8080${NC}"
echo -e "   n8n Workflows:     ${GREEN}http://localhost:8080/n8n/${NC}"
echo -e "   Lawyer Chat:       ${GREEN}http://localhost:8080/chat${NC}"
echo -e "   AI Portal:         ${GREEN}http://localhost:8085${NC}"

if [ "$INCLUDE_HAYSTACK" = true ]; then
    echo -e "   Elasticsearch:     ${GREEN}http://localhost:9200${NC}"
    echo -e "   Haystack API:      ${GREEN}http://localhost:8000${NC}"
    echo -e "   API Docs:          ${GREEN}http://localhost:8000/docs${NC}"
fi

echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
if [ "$SKIP_WORKFLOW_IMPORT" = false ] && [ "$WORKFLOW_EXISTS" -eq 0 ]; then
    echo -e "   1. Check n8n workflows at http://localhost:8080/n8n/"
    echo -e "   2. Ensure the Basic_workflow is active"
    echo -e "   3. Test the AI Chat interface"
else
    echo -e "   1. Test the AI Chat interface at http://localhost:8080"
    echo -e "   2. Try the Lawyer Chat at http://localhost:8080/chat"
fi

echo ""
echo -e "${YELLOW}💡 Management Commands:${NC}"
echo -e "   View logs:         ${BLUE}docker-compose logs -f [service]${NC}"
echo -e "   Stop all:          ${BLUE}docker-compose down${NC}"
echo -e "   Health check:      ${BLUE}./scripts/health-check.sh${NC}"
echo ""