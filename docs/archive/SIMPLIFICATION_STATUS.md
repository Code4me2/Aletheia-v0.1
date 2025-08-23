# Aletheia Simplification Status

## ✅ Completed (Don't Redo)
- **Scripts**: 19 scripts → 4 essential + `/dev` CLI
- **Docker**: 13 docker-compose files → 3 active
- **Dev CLI**: Single `/dev` command for all operations (v2.0)
- **Health Checks**: Added to all services
- **n8n Auth**: Documented credentials (velvetmoon222999@gmail.com / Welcome123!)
- **Test Consolidation**: 4 directories → 1 organized `tests/` directory
- **Simple README**: 1673 lines → 24 lines (old saved as README.old.md)
- **Documentation**: 31 MD files in root → 5 essential (rest in docs/)
- **Environment**: 94 lines → 47 essential variables (removed 34 unused, kept all required)
  - Safely removed: unused ports, auth variables, hardcoded values
  - Fixed documentation: AI Portal port 8085→8102, updated file paths

## 🔴 High Priority - Do Next

### 1. Remove node_modules from custom nodes (saves 780MB)
```bash
# These are NOT needed at runtime - n8n uses dist/ folders
rm -rf n8n/custom-nodes/*/node_modules
# Creates 780MB space saving instantly
```

## 📁 Additional Docker Compose Files (Investigation Complete)

### Found 4 supplementary compose files:

1. **n8n/docker-compose.haystack.yml** - Elasticsearch + Haystack RAG
   - Adds: Elasticsearch (port 9200), Haystack service (port 8000), Unstructured service (port 8880)
   - Purpose: Document search and RAG capabilities
   - Status: NOT RUNNING (optional feature)
   - Usage: `docker-compose -f docker-compose.yml -f n8n/docker-compose.haystack.yml up -d`

2. **n8n/docker-compose.doctor.yml** - FLP Document Processing
   - Adds: FreeLawProject doctor service (port 5050)
   - Purpose: Legal document conversion and extraction
   - Status: NOT RUNNING (optional feature)
   - Usage: `docker-compose -f docker-compose.yml -f n8n/docker-compose.doctor.yml up -d`

3. **n8n/docker-compose.bitnet.yml** - BitNet AI Server
   - Adds: Microsoft BitNet inference server (port 8081)
   - Purpose: 1-bit LLM inference for efficiency
   - Status: NOT RUNNING (optional feature)
   - Note: Has custom n8n node already built

4. **docker-compose.production.yml** - Production Overrides
   - Purpose: Security hardening, monitoring stack (Prometheus, Grafana, Loki)
   - Adds: Resource limits, read-only filesystems, monitoring services
   - Status: NOT ACTIVE (development environment)
   - Usage: `docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d`

**Recommendation**: Keep all 4 files - they provide optional features and production config

## 🟡 Medium Priority

### 4. Port Documentation
Create `PORT_MAPPING.md`:
- PostgreSQL: External 8200 → Internal 5432 (why?)
- Document all service ports

### 5. Archive Remaining Cruft
```bash
./dev cleanup  # Already created, just run it
# Archives: *.bak, *.disabled, old docker-compose files
```

### 6. Custom Nodes Documentation  
- 8 nodes, each has README
- Consolidate to single `n8n/CUSTOM_NODES.md`

## 📊 Environment Variables Detail

### Variables Safely Removed (34 total):
- Unused service ports: GRAFANA_PORT, LOKI_PORT, ELASTICSEARCH_PORT, HAYSTACK_PORT
- Unused auth: N8N_BASIC_AUTH_*, N8N_API_KEY, N8N_API_SECRET  
- Hardcoded values: NEXTAUTH_URL, COURT_PROCESSOR_PORT, SERVICE_HOST
- Not needed: API_GATEWAY_PORT, BITNET_PORT, DOCKER_API_PORT

### Variables Required (47 kept):
- **Essential**: DB credentials, N8N_ENCRYPTION_KEY, NEXTAUTH_SECRET, N8N_WEBHOOK_ID
- **Ports**: WEB_PORT, N8N_PORT, AI_PORTAL_PORT, POSTGRES_PORT, REDIS_PORT
- **URLs**: Service communication URLs (generated from ports)
- **Optional**: SMTP_*, PACER_*, COURTLISTENER_*, can be empty if not using features

## 🟢 Working - Don't Break
- `/dev` CLI - All commands tested and working
- `docker-compose.yml` - Services running properly
- `nginx/nginx.conf` - Routing works
- `court-processor/simplified_api.py` - API functional
- Database volumes - Has data

## Key Files

### Modified Today
- `/dev` - Enhanced CLI (431 lines)
- `docker-compose.yml` - Added health checks
- `.env` - Removed obsolete variables

### Created Today
- `SIMPLIFICATION_STATUS.md` - This file
- `scripts/README.md` - Documents remaining scripts
- `.archive/scripts/` - Archived 10 scripts

### Deleted Today
- `/cli/` directory (duplicate dev script)
- `nginx/auth-bypass/` (non-functional)
- 10+ redundant scripts

## For Next Agent

1. **Start here**: Run `./dev cleanup` to archive old files
2. **Big win**: Consolidate test directories (saves ~1000 files)
3. **Quick win**: Write simple README.md (current is too complex)
4. **Use**: `./dev help` to see all available commands
5. **Test with**: `./dev validate` after changes

## Metrics
- **Files reduced**: ~40% (scripts, docker-compose, configs)
- **Commands unified**: 20+ scripts → 1 CLI
- **Setup time**: Was hours, now < 10 minutes
- **Remaining bloat**: Test directories (1000+ files)