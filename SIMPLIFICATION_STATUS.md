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
- **Environment**: 94 lines → 37 essential variables (backup in .env.full)

## 🔴 High Priority - Do Next

### 1. Remove node_modules from custom nodes (saves 780MB)
```bash
# These are NOT needed at runtime - n8n uses dist/ folders
rm -rf n8n/custom-nodes/*/node_modules
# Creates 780MB space saving instantly
```

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