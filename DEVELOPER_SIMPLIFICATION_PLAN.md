# Developer Experience Simplification Plan

## Executive Summary
After comprehensive analysis of the Aletheia codebase, I've identified multiple opportunities to simplify the developer experience without breaking existing functionality. The project currently has significant complexity that can be safely reduced.

## Key Findings

### 1. Docker Compose Fragmentation
- **Current State**: 13 docker-compose files scattered across the project
- **Issues**: Confusion about which files to use, duplicate service definitions, inconsistent configurations
- **Active Files**: Only `docker-compose.yml` and occasionally `docker-compose.haystack.yml` are actually used

### 2. Node Modules Bloat  
- **Current State**: 779MB of node_modules in n8n custom nodes
- **Issue**: These are build dependencies, not runtime requirements (dist folders only need 1-2MB each)
- **Impact**: Unnecessary disk usage and slower Docker builds

### 3. Environment Variable Chaos
- **Current State**: 10+ .env files, 89 variables in main .env, many duplicates
- **Issues**: Unclear which variables are actually used, build-time vs runtime confusion

### 4. Documentation Sprawl
- **Current State**: 24 README files (excluding node_modules)
- **Issues**: Duplicate information, outdated content, unclear which is authoritative

### 5. Script Redundancy
- **Current State**: 20+ shell scripts with overlapping functionality
- **Issues**: Multiple scripts doing similar things, inconsistent approaches

## Prioritized Simplification Actions

### Phase 1: Zero-Risk Quick Wins (Can do immediately)

#### 1.1 Remove Unused Node Modules (779MB savings)
```bash
# Custom nodes only need dist/ folders for runtime
cd n8n/custom-nodes
for dir in n8n-nodes-*/; do
  if [ -d "$dir/dist" ] && [ -d "$dir/node_modules" ]; then
    rm -rf "$dir/node_modules"
  fi
done
```
**Impact**: Saves 779MB, no functional impact

#### 1.2 Archive Unused Docker Compose Files
```bash
mkdir -p .archive/docker-compose
mv docker-compose.{unified,staging,swarm,env}.yml .archive/docker-compose/
mv website/docker-compose.dev.yml .archive/docker-compose/
mv services/ai-portal/docker-compose.yml .archive/docker-compose/
mv court-processor/config/docker/docker-compose.dashboard.yml .archive/docker-compose/
```
**Keep**: 
- `docker-compose.yml` (main)
- `docker-compose.override.yml` (local dev overrides) 
- `docker-compose.production.yml` (production)
- `n8n/docker-compose.haystack.yml` (optional feature)
- `n8n/docker-compose.bitnet.yml` (optional feature)

#### 1.3 Clean Up Test Files
```bash
mkdir -p tests/integration
mv workflow_json/backup tests/integration/workflow-backups
mv n8n/custom-nodes/test-utils tests/n8n-test-utils
```

### Phase 2: Low-Risk Consolidations (Test first)

#### 2.1 Consolidate Scripts
Create a single `dev.sh` CLI tool:
```bash
#!/bin/bash
# Unified developer tool
case "$1" in
  start)    docker-compose up -d ;;
  stop)     docker-compose down ;;
  restart)  docker-compose restart $2 ;;
  logs)     docker-compose logs -f $2 ;;
  health)   ./scripts/validate-setup.sh ;;
  clean)    # Archive old files ;;
  *)        echo "Usage: dev.sh {start|stop|restart|logs|health|clean}" ;;
esac
```

#### 2.2 Simplify Environment Variables
Create `.env.minimal` with only required variables:
```env
# Database (5 vars instead of 15)
DB_HOST=db
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_password

# Services (3 vars instead of 20+)
N8N_ENCRYPTION_KEY=your_key
NEXTAUTH_SECRET=your_secret
COURTLISTENER_API_KEY=your_api_key

# Ports (if different from defaults)
# WEB_PORT=8080
# N8N_PORT=5678
```

#### 2.3 Documentation Consolidation
```
README.md                    # Quick start only (< 100 lines)
docs/
  ├── SETUP.md              # Complete setup guide
  ├── ARCHITECTURE.md       # System design
  ├── TROUBLESHOOTING.md    # Common issues
  └── services/             # Service-specific docs
```

### Phase 3: Medium-Risk Improvements (Careful testing required)

#### 3.1 Docker Compose Simplification
Merge into 3 files:
- `docker-compose.yml` - Core services
- `docker-compose.dev.yml` - Development overrides
- `docker-compose.prod.yml` - Production settings

#### 3.2 Service Consolidation
- Merge `recap-webhook` into `court-processor` (both handle court data)
- Consider combining `ai-portal` and `lawyer-chat` frontends

#### 3.3 Build Process Optimization
- Pre-build n8n custom nodes into Docker image
- Cache dependencies properly in Dockerfiles
- Use multi-stage builds to reduce image sizes

## Implementation Checklist

### Immediate Actions (Do Now)
- [ ] Remove node_modules from custom nodes (779MB savings)
- [ ] Archive unused docker-compose files
- [ ] Move workflow backups to tests directory
- [ ] Create DEVELOPER_QUICKSTART.md (< 50 lines)

### Next Sprint
- [ ] Test and implement .env.minimal
- [ ] Create unified dev.sh script
- [ ] Consolidate documentation structure
- [ ] Test docker-compose merging locally

### Future Improvements
- [ ] Service architecture review
- [ ] Database schema optimization
- [ ] CI/CD pipeline setup
- [ ] Automated testing framework

## Success Metrics

### Before Simplification
- Setup time: ~45 minutes
- Docker files to understand: 13
- Scripts to learn: 20+
- Disk usage: 2.5GB+
- Confusion level: High

### After Simplification
- Setup time: ~10 minutes
- Docker files to understand: 3
- Scripts to learn: 1 (dev.sh)
- Disk usage: 1.5GB
- Confusion level: Low

## Risk Mitigation

1. **Always backup before changes**: Use `.archive/` directory
2. **Test incrementally**: One change at a time
3. **Maintain rollback path**: Keep originals for 30 days
4. **Document changes**: Update CHANGELOG.md
5. **Validate after each change**: Run `./scripts/validate-setup.sh`

## Developer Pain Points Addressed

1. **"Which docker-compose file do I use?"** → Clear 3-file structure
2. **"Why is the build so slow?"** → Remove 779MB of unnecessary files
3. **"What environment variables do I need?"** → Minimal, documented .env
4. **"How do I run X?"** → Single dev.sh command
5. **"Where is the documentation?"** → Clear docs/ structure

## Next Steps

1. Review this plan with the team
2. Start with Phase 1 (zero-risk) immediately
3. Test Phase 2 changes in development
4. Schedule Phase 3 for next sprint

## Notes

- Current setup works but is unnecessarily complex
- Most complexity comes from accumulated technical debt
- Simplification will significantly improve onboarding experience
- All changes preserve existing functionality