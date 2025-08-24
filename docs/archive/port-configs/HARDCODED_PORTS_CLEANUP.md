# Hardcoded Ports Cleanup Tasks

## Overview
This document tracks hardcoded ports and URLs that should be migrated to use the new flexible port mapping system.

## Issues Found

### 1. Frontend Files

#### website/index.html
- **Line 72**: `<a href="http://localhost:8085" class="app-menu-item">`
- **Impact**: AI Portal link broken when ports change
- **Fix**: Should use relative URL `/portal` through reverse proxy

#### website/js/tests.js
- **Line 14**: `this.testApiUrl = 'http://localhost:8000';`
- **Impact**: Tests fail when Haystack runs on different port
- **Fix**: Should read from CONFIG object

#### website/js/rag-testing.js
- Similar hardcoded test endpoints
- **Fix**: Should use environment-aware configuration

### 2. Docker Compose Files

#### docker-compose.production.yml
```yaml
- Prometheus: 9090 (hardcoded)
- Grafana: 3001:3000 (hardcoded) 
- Loki: 3100 (hardcoded)
```
**Fix**: Should use `${PROMETHEUS_PORT:-9090}` pattern

#### n8n/docker-compose.haystack.yml
```yaml
- Elasticsearch: 9300:9300 (hardcoded)
- Unstructured: 8880:8880 (hardcoded)
```
**Fix**: Should use environment variables

#### n8n/docker-compose.bitnet.yml
```yaml
- BitNet: 8081:8080 (hardcoded)
```
**Fix**: Should use `${BITNET_PORT:-8081}`

### 3. Shell Scripts

#### health_check.sh
```bash
# Lines 6-11: Hardcoded service URLs
services=(
    "http://localhost:8080|Main Web"
    "http://localhost:8085|AI Portal"
    "http://localhost:8080/chat|Lawyer Chat"
    "http://localhost:8080/n8n/healthz|n8n"
)
```
**Impact**: Health checks fail when ports change

#### test_haystack_rag.sh
- **Line 7**: `echo "Target: http://localhost:8000"`
- **Throughout**: Multiple curl commands with hardcoded localhost:8000
**Impact**: RAG tests fail when Haystack port changes

#### ollama-to-llama-proxy.js
```javascript
// Lines 4-5:
const LLAMA_SERVER = 'http://localhost:11434';
const PROXY_PORT = 11435;
```
**Impact**: Proxy fails when Ollama runs on different port

**Fix**: Scripts should source port configuration from environment

### 4. N8N Custom Nodes

Default endpoints in node configurations:
- n8n-nodes-deepseek: `http://host.docker.internal:11434`
- n8n-nodes-bitnet: `http://localhost:11434`
- n8n-nodes-unstructured: `http://localhost:8880`

**Fix**: Should use environment variables or configuration

### 5. Test Files

Many test files have hardcoded localhost URLs:
- JavaScript test files
- Shell test scripts
- Integration tests

**Fix**: Tests should be environment-aware

## Recommended Actions

### Phase 1: Critical Updates
1. Update website/index.html to remove hardcoded port 8085
2. Update docker-compose.production.yml monitoring ports
3. Create environment-aware configuration for frontend

### Phase 2: Service Updates  
1. Update all docker-compose files to use environment variables
2. Modify shell scripts to read from environment
3. Update N8N custom nodes to use configurable endpoints

### Phase 3: Test Updates
1. Create test configuration system
2. Update all test files to use dynamic ports
3. Add environment detection to test scripts

## Detailed Implementation Plan

### Phase 1: Critical Frontend Updates

#### 1.1 Fix website/index.html (Line 72)
```html
<!-- Current (WRONG): -->
<a href="http://localhost:8085" class="app-menu-item">

<!-- Fix Option 1 - Relative URL through reverse proxy: -->
<a href="/portal" class="app-menu-item">

<!-- Fix Option 2 - Dynamic from config: -->
<a href="#" class="app-menu-item" id="ai-portal-link">
<!-- Add to app.js: -->
document.getElementById('ai-portal-link').href = CONFIG.services?.aiPortal || '/portal';
```

#### 1.2 Update website/js/config.js
```javascript
// Add service URLs to CONFIG:
const CONFIG = window.DATA_COMPOSE_CONFIG || {
  // ... existing config ...
  services: {
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
  }
};
```

#### 1.3 Update website/js/tests.js (Line 14)
```javascript
// Current:
this.testApiUrl = 'http://localhost:8000';

// Fix:
this.testApiUrl = CONFIG.services?.haystackDirect || '/api/rag';
```

### Phase 2: Docker Compose Updates

#### 2.1 Fix docker-compose.production.yml
```yaml
# Monitoring services (lines 138-163)
prometheus:
  ports:
    - "${PROMETHEUS_PORT:-9090}:9090"  # Was: "9090:9090"

grafana:
  ports:
    - "${GRAFANA_PORT:-3001}:3000"     # Was: "3001:3000"

loki:
  ports:
    - "${LOKI_PORT:-3100}:3100"        # Was: "3100:3100"
```

#### 2.2 Fix n8n/docker-compose.haystack.yml
```yaml
elasticsearch:
  ports:
    - "${ELASTICSEARCH_PORT:-9200}:9200"
    - "${ELASTICSEARCH_CLUSTER_PORT:-9300}:9300"  # Was: "9300:9300"

unstructured-api:
  ports:
    - "${UNSTRUCTURED_PORT:-8880}:8880"  # Was: "8880:8880"
```

#### 2.3 Fix n8n/docker-compose.bitnet.yml
```yaml
bitnet:
  ports:
    - "${BITNET_PORT:-8081}:8080"  # Was: "8081:8080"
```

### Phase 3: Shell Script Updates

#### 3.1 Create scripts/port-config.sh
```bash
#!/bin/bash
# Centralized port configuration loader

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
```

#### 3.2 Update health_check.sh
```bash
#!/bin/bash

# Source port configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/port-config.sh"

echo "Checking Aletheia-v0.1 Services..."
echo "================================"

# Check each service using dynamic ports
services=(
    "$(get_service_url web)|Main Web"
    "$(get_service_url ai-portal)|AI Portal"
    "$(get_service_url chat)|Lawyer Chat"
    "$(get_service_url n8n)/healthz|n8n"
)

# ... rest of script remains the same ...
```

#### 3.3 Update ollama-to-llama-proxy.js
```javascript
const http = require('http');

// Use environment variables with defaults
const LLAMA_SERVER = process.env.LLAMA_SERVER || 'http://localhost:11434';
const PROXY_PORT = parseInt(process.env.OLLAMA_PROXY_PORT || '11435');

console.log(`Starting Ollama proxy: ${PROXY_PORT} -> ${LLAMA_SERVER}`);

const proxy = http.createServer(async (req, res) => {
  // ... rest of proxy code remains the same ...
});

proxy.listen(PROXY_PORT, () => {
  console.log(`Ollama proxy listening on port ${PROXY_PORT}`);
});
```

#### 3.4 Update test_haystack_rag.sh
```bash
#!/bin/bash
# Test Haystack RAG Functionality using curl

# Source port configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/port-config.sh"

HAYSTACK_URL="http://localhost:${HAYSTACK_PORT}"

echo "=============================================="
echo "Haystack RAG Functionality Test Suite"
echo "Time: $(date)"
echo "Target: ${HAYSTACK_URL}"
echo "=============================================="

# Update all curl commands to use ${HAYSTACK_URL}
# Example:
run_test "Health Check" "curl -s ${HAYSTACK_URL}/health" "ok"
```

### Phase 4: N8N Custom Nodes

#### 4.1 Update node configurations to use environment variables

For each custom node, update the default URL configuration:

**n8n-nodes-deepseek/src/DeepSeek.node.ts:**
```typescript
{
    displayName: 'Endpoint',
    name: 'endpoint',
    type: 'string',
    default: process.env.DEEPSEEK_ENDPOINT || process.env.OLLAMA_URL || 'http://host.docker.internal:11434/api/generate',
    placeholder: 'http://your-ollama-server:11434/api/generate',
    description: 'The Ollama API endpoint for DeepSeek',
}
```

**n8n-nodes-bitnet/nodes/BitNet/BitNet.node.ts:**
```typescript
{
    displayName: 'API URL',
    name: 'apiUrl',
    type: 'string',
    default: process.env.BITNET_URL || 'http://bitnet:8080',
    placeholder: 'http://bitnet:8080',
    description: 'BitNet server URL',
}
```

### Phase 5: Test Configuration

#### 5.1 Create test/test-config.js
```javascript
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
```

#### 5.2 Update test files to use configuration
```javascript
// In test files:
const config = require('./test-config');
const haystackUrl = config.getServiceUrl('haystack');
```

## Implementation Checklist

### High Priority (User-Facing)
- [ ] Update website/index.html line 72 to use relative URL
- [ ] Add service URLs to website/js/config.js
- [ ] Update website/js/tests.js to use CONFIG
- [ ] Fix docker-compose.production.yml monitoring ports
- [ ] Create scripts/port-config.sh for shell scripts
- [ ] Update health_check.sh to use port-config.sh

### Medium Priority (Operational)
- [ ] Update n8n/docker-compose.haystack.yml ports
- [ ] Update n8n/docker-compose.bitnet.yml ports  
- [ ] Add environment detection to N8N custom nodes
- [ ] Update all health check scripts
- [ ] Create test configuration system

### Low Priority (Development)
- [ ] Update all test files to use TEST_CONFIG
- [ ] Add port injection to frontend build process
- [ ] Document environment variable usage

## Benefits of Cleanup

1. **Consistency**: All services use the same port configuration system
2. **Flexibility**: Easy to change ports for different environments
3. **No Conflicts**: Automatic conflict detection prevents issues
4. **Documentation**: Single source of truth for all port mappings
5. **Testing**: Tests can run in any environment without modification
6. **Deployment**: Simplified deployment across different environments
7. **Development**: No more manual port changes when switching environments

## Priority

1. **High**: Frontend hardcoded URLs (user-facing)
2. **High**: Production docker-compose (deployment critical)
3. **Medium**: Shell scripts (operational tools)
4. **Low**: Test files (development only)
5. **Low**: N8N node defaults (have fallbacks)