# Court Processor API Cleanup Plan

## Current State Analysis

### Active APIs (KEEP)
1. **simplified_api.py** (port 8104) - NEW simplified database API
2. **api/webhook_server.py** - Used by docker-compose for RECAP webhooks
3. **court_processor** - Main CLI tool

### Unused/Redundant APIs (ARCHIVE)
1. **standalone_database_api.py** (port 8103) - Replaced by simplified_api.py
2. **api/unified_api.py** - Not referenced in docker-compose
3. **api/court_processor_api.py** - Not actively used
4. **api/database_search_endpoint.py** - Functionality in simplified_api.py
5. **api/flp_api.py** - FLP integration, check if needed

### Documentation to Update/Consolidate
- STANDALONE_API_USAGE.md → Archive (replaced by API_MIGRATION_GUIDE.md)
- API_UNIFICATION_ANALYSIS.md → Archive (historical)
- CLI_AND_API_GUIDE.md → Update to reference new API
- Multiple overlapping docs in docs/ folder

## Cleanup Actions

### Phase 1: Archive Unused APIs
```bash
# Move old APIs to archive
mv standalone_database_api.py ARCHIVED_OLD_CODE/
mv api/unified_api.py ARCHIVED_OLD_CODE/
mv api/court_processor_api.py ARCHIVED_OLD_CODE/
mv api/database_search_endpoint.py ARCHIVED_OLD_CODE/
```

### Phase 2: Consolidate Documentation
```bash
# Archive old docs
mv STANDALONE_API_USAGE.md ARCHIVED_OLD_CODE/docs/
mv API_UNIFICATION_ANALYSIS.md ARCHIVED_OLD_CODE/docs/
```

### Phase 3: Update Active Documentation
- Update README.md to reference simplified_api.py
- Create single API_GUIDE.md for current state

## Dependencies Check
- webhook_server.py is used by docker-compose ✓
- simplified_api.py is standalone ✓
- No other services depend on removed APIs ✓

## Rollback Plan
All files moved to ARCHIVED_OLD_CODE/ can be restored if needed