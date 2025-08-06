#!/bin/bash
# Script to implement port mapping fixes
# This script applies the recommended changes from HARDCODED_PORTS_CLEANUP.md

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Aletheia Port Mapping Fixes Implementation"
echo "=========================================="
echo

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Function to backup files before modification
backup_file() {
    local file=$1
    if [ -f "$file" ]; then
        cp "$file" "${file}.backup-$(date +%Y%m%d-%H%M%S)"
        log_info "Backed up $file"
    fi
}

# Phase 1: Frontend Fixes
echo "Phase 1: Frontend Fixes"
echo "-----------------------"

# Fix website/index.html
if grep -q "http://localhost:8085" "$PROJECT_ROOT/website/index.html"; then
    backup_file "$PROJECT_ROOT/website/index.html"
    sed -i.tmp 's|href="http://localhost:8085"|href="/portal"|g' "$PROJECT_ROOT/website/index.html"
    rm -f "$PROJECT_ROOT/website/index.html.tmp"
    log_info "Fixed hardcoded port in website/index.html"
else
    log_warn "website/index.html already fixed or not found"
fi

# Update website/js/config.js
if [ -f "$PROJECT_ROOT/website/js/config.js" ]; then
    if ! grep -q "services:" "$PROJECT_ROOT/website/js/config.js"; then
        backup_file "$PROJECT_ROOT/website/js/config.js"
        # Add services configuration
        cat >> "$PROJECT_ROOT/website/js/config.js" << 'EOF'

// Service URLs configuration
CONFIG.services = {
  aiPortal: '/portal',
  n8n: '/n8n',
  chat: '/chat',
  api: '/api',
  // Direct service access (for development)
  ...(window.location.hostname === 'localhost' ? {
    aiPortalDirect: `:${window.AI_PORTAL_PORT || '8102'}`,
    n8nDirect: `:${window.N8N_PORT || '8100'}`,
    haystackDirect: `:${window.HAYSTACK_PORT || '8500'}`
  } : {})
};
EOF
        log_info "Added services configuration to config.js"
    else
        log_warn "Services already configured in config.js"
    fi
fi

# Fix website/js/tests.js
if grep -q "http://localhost:8000" "$PROJECT_ROOT/website/js/tests.js" 2>/dev/null; then
    backup_file "$PROJECT_ROOT/website/js/tests.js"
    sed -i.tmp "s|this\.testApiUrl = 'http://localhost:8000'|this.testApiUrl = CONFIG.services?.haystackDirect \|\| '/api/rag'|g" "$PROJECT_ROOT/website/js/tests.js"
    rm -f "$PROJECT_ROOT/website/js/tests.js.tmp"
    log_info "Fixed hardcoded port in website/js/tests.js"
fi

echo
echo "Phase 2: Docker Compose Fixes"
echo "-----------------------------"

# Fix docker-compose.production.yml
if [ -f "$PROJECT_ROOT/docker-compose.production.yml" ]; then
    backup_file "$PROJECT_ROOT/docker-compose.production.yml"
    
    # Fix Prometheus port
    sed -i.tmp 's|"9090:9090"|"${PROMETHEUS_PORT:-9090}:9090"|g' "$PROJECT_ROOT/docker-compose.production.yml"
    
    # Fix Grafana port
    sed -i.tmp 's|"3001:3000"|"${GRAFANA_PORT:-3001}:3000"|g' "$PROJECT_ROOT/docker-compose.production.yml"
    
    # Fix Loki port
    sed -i.tmp 's|"3100:3100"|"${LOKI_PORT:-3100}:3100"|g' "$PROJECT_ROOT/docker-compose.production.yml"
    
    rm -f "$PROJECT_ROOT/docker-compose.production.yml.tmp"
    log_info "Fixed monitoring ports in docker-compose.production.yml"
fi

# Fix n8n/docker-compose.haystack.yml
if [ -f "$PROJECT_ROOT/n8n/docker-compose.haystack.yml" ]; then
    backup_file "$PROJECT_ROOT/n8n/docker-compose.haystack.yml"
    
    # Fix Elasticsearch cluster port
    sed -i.tmp 's|"9300:9300"|"${ELASTICSEARCH_CLUSTER_PORT:-9300}:9300"|g' "$PROJECT_ROOT/n8n/docker-compose.haystack.yml"
    
    # Fix Unstructured port
    sed -i.tmp 's|"8880:8880"|"${UNSTRUCTURED_PORT:-8880}:8880"|g' "$PROJECT_ROOT/n8n/docker-compose.haystack.yml"
    
    rm -f "$PROJECT_ROOT/n8n/docker-compose.haystack.yml.tmp"
    log_info "Fixed ports in n8n/docker-compose.haystack.yml"
fi

# Fix n8n/docker-compose.bitnet.yml
if [ -f "$PROJECT_ROOT/n8n/docker-compose.bitnet.yml" ]; then
    backup_file "$PROJECT_ROOT/n8n/docker-compose.bitnet.yml"
    
    sed -i.tmp 's|"8081:8080"|"${BITNET_PORT:-8081}:8080"|g' "$PROJECT_ROOT/n8n/docker-compose.bitnet.yml"
    
    rm -f "$PROJECT_ROOT/n8n/docker-compose.bitnet.yml.tmp"
    log_info "Fixed BitNet port in n8n/docker-compose.bitnet.yml"
fi

echo
echo "Phase 3: Shell Scripts"
echo "---------------------"

# Create port-config.sh
cat > "$PROJECT_ROOT/scripts/port-config.sh" << 'EOF'
#!/bin/bash
# Centralized port configuration loader

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source environment file if exists
if [ -f "${SCRIPT_DIR}/../.env" ]; then
    source "${SCRIPT_DIR}/../.env"
fi

# Export default ports if not set
export WEB_PORT=${WEB_PORT:-8080}
export N8N_PORT=${N8N_PORT:-8100}
export LAWYER_CHAT_PORT=${LAWYER_CHAT_PORT:-8101}
export AI_PORTAL_PORT=${AI_PORTAL_PORT:-8102}
export POSTGRES_PORT=${POSTGRES_PORT:-8200}
export REDIS_PORT=${REDIS_PORT:-8201}
export ELASTICSEARCH_PORT=${ELASTICSEARCH_PORT:-8202}
export HAYSTACK_PORT=${HAYSTACK_PORT:-8500}
export BITNET_PORT=${BITNET_PORT:-8501}
export PROMETHEUS_PORT=${PROMETHEUS_PORT:-8300}
export GRAFANA_PORT=${GRAFANA_PORT:-8301}

# Helper functions
get_service_url() {
    local service=$1
    case $service in
        web) echo "http://localhost:${WEB_PORT}" ;;
        n8n) echo "http://localhost:${WEB_PORT}/n8n" ;;
        chat) echo "http://localhost:${WEB_PORT}/chat" ;;
        ai-portal) echo "http://localhost:${WEB_PORT}/portal" ;;
        haystack) echo "http://localhost:${HAYSTACK_PORT}" ;;
        *) echo "http://localhost:${WEB_PORT}" ;;
    esac
}
EOF
chmod +x "$PROJECT_ROOT/scripts/port-config.sh"
log_info "Created scripts/port-config.sh"

# Update health_check.sh to use port-config.sh
if [ -f "$PROJECT_ROOT/health_check.sh" ]; then
    if ! grep -q "port-config.sh" "$PROJECT_ROOT/health_check.sh"; then
        backup_file "$PROJECT_ROOT/health_check.sh"
        # Create new health_check.sh
        cat > "$PROJECT_ROOT/health_check.sh" << 'EOF'
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
EOF
        chmod +x "$PROJECT_ROOT/health_check.sh"
        log_info "Updated health_check.sh to use dynamic ports"
    fi
fi

# Update ollama-to-llama-proxy.js
if [ -f "$PROJECT_ROOT/ollama-to-llama-proxy.js" ]; then
    if grep -q "const LLAMA_SERVER = 'http://localhost:11434'" "$PROJECT_ROOT/ollama-to-llama-proxy.js"; then
        backup_file "$PROJECT_ROOT/ollama-to-llama-proxy.js"
        sed -i.tmp "s|const LLAMA_SERVER = 'http://localhost:11434'|const LLAMA_SERVER = process.env.LLAMA_SERVER || 'http://localhost:11434'|g" "$PROJECT_ROOT/ollama-to-llama-proxy.js"
        sed -i.tmp "s|const PROXY_PORT = 11435|const PROXY_PORT = parseInt(process.env.OLLAMA_PROXY_PORT || '11435')|g" "$PROJECT_ROOT/ollama-to-llama-proxy.js"
        rm -f "$PROJECT_ROOT/ollama-to-llama-proxy.js.tmp"
        log_info "Updated ollama-to-llama-proxy.js to use environment variables"
    fi
fi

echo
echo "Phase 4: Test Configuration"
echo "---------------------------"

# Create test configuration
mkdir -p "$PROJECT_ROOT/test"
cat > "$PROJECT_ROOT/test/test-config.js" << 'EOF'
// Test environment configuration
const TEST_CONFIG = {
    // Use environment variables or defaults
    services: {
        haystack: process.env.HAYSTACK_URL || 'http://localhost:8500',
        n8n: process.env.N8N_URL || 'http://localhost:8100',
        elasticsearch: process.env.ELASTICSEARCH_URL || 'http://localhost:8202',
        postgres: process.env.DATABASE_URL || 'postgresql://localhost:8200/aletheia'
    },
    
    // Helper to get service URL
    getServiceUrl: function(service) {
        return this.services[service] || `http://localhost:${process.env.WEB_PORT || 8080}`;
    }
};

// For Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TEST_CONFIG;
}

// For browser
if (typeof window !== 'undefined') {
    window.TEST_CONFIG = TEST_CONFIG;
}
EOF
log_info "Created test/test-config.js"

echo
echo "========================================"
echo "Port Mapping Fixes Complete!"
echo "========================================"
echo
echo "Summary of changes:"
echo "- Frontend files updated to use relative URLs"
echo "- Docker Compose files updated with environment variables"
echo "- Created centralized port configuration script"
echo "- Updated shell scripts to use dynamic ports"
echo "- Created test configuration system"
echo
echo "Next steps:"
echo "1. Review the changes in your git diff"
echo "2. Test the services with: ./scripts/deploy.sh up"
echo "3. Commit the changes if everything works correctly"
echo
echo "Backup files created with .backup-* extension"