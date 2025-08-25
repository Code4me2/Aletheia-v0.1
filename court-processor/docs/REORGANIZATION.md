# Court Processor Reorganization Plan

## Current State Analysis

### Active Components (IN USE)
1. **simplified_api.py** - Main REST API on port 8104
   - Uses `public.court_documents` table
   - Provides text extraction and search endpoints
   - Auto-starts via entrypoint.sh

2. **court_processor CLI** - Command-line interface
   - Uses `public.court_documents` table
   - Provides data management, analysis, and export functions
   - Must run inside Docker container

3. **pipeline.py** - Document processing pipeline
   - 11-stage processing pipeline
   - Enriches documents with metadata

### Database Tables Status
- **ACTIVE**: `public.court_documents` (485 documents)
- **PARTIAL**: `court_data.opinions_unified` (210 documents)
- **EMPTY**: `court_data.cl_opinions`, `court_data.cl_*` tables
- **MINIMAL**: `court_data.judges` (10 entries)

### Unused/Legacy Components
- Multiple SQL schema files for unused tables
- services/recap/* - RECAP integration (not actively used)
- services/flp_integration.py - FLP enhancement (not actively used)
- Numerous utility scripts in scripts/utilities/

## Reorganization Strategy

### Phase 1: Archive Unused Schemas
Create `archived/database_schemas/` with:
- init_courtlistener_schema.sql
- add_recap_schema.sql
- add_flp_supplemental_tables.sql
- create_unified_opinions_table.sql

Keep only:
- init_db.sql (rename to schema_legacy.sql for reference)

### Phase 2: Consolidate Active Code
```
court-processor/
├── README.md                    # Clear documentation
├── ACTIVE_SCHEMA.sql           # Document public.court_documents
├── api/
│   └── simplified_api.py      # Main API
├── cli/
│   └── court_processor         # CLI tool
├── core/
│   ├── pipeline.py            # Processing pipeline
│   ├── database.py            # Database connections
│   └── validators.py          # Pipeline validators
├── services/
│   └── courtlistener.py       # Active services only
├── archived/                   # All unused code
│   ├── database_schemas/      # Unused SQL schemas
│   ├── services/              # Unused services
│   └── scripts/               # Legacy scripts
└── docker/
    ├── Dockerfile
    └── entrypoint.sh
```

### Phase 3: Create Clear Documentation
1. **ACTIVE_SCHEMA.sql** - Document the actual schema in use
2. **API_REFERENCE.md** - Clear API documentation
3. **CLI_REFERENCE.md** - Clear CLI documentation
4. Update main README.md with only active functionality

## Migration Steps

### Step 1: Create Archive Directory Structure
```bash
mkdir -p archived/database_schemas
mkdir -p archived/services
mkdir -p archived/scripts
```

### Step 2: Move Unused Database Schemas
```bash
mv scripts/init_courtlistener_schema.sql archived/database_schemas/
mv scripts/add_recap_schema.sql archived/database_schemas/
mv scripts/add_flp_supplemental_tables.sql archived/database_schemas/
mv migrations/create_unified_opinions_table.sql archived/database_schemas/
```

### Step 3: Archive Unused Services
```bash
mv services/recap archived/services/
mv services/flp_integration.py archived/services/
```

### Step 4: Create Active Schema Documentation
Document the actual `public.court_documents` table structure

### Step 5: Simplify Directory Structure
- Move simplified_api.py to api/
- Move court_processor to cli/
- Create core/ for shared functionality

## Risks and Mitigations

### Risk 1: Breaking Active Functionality
**Mitigation**: 
- Test API endpoints before and after changes
- Keep backup of original structure
- Move files gradually, testing after each move

### Risk 2: Lost Future Functionality
**Mitigation**: 
- Archive everything, don't delete
- Document what each archived component was intended for
- Keep migration path documented

### Risk 3: Docker Build Issues
**Mitigation**: 
- Update Dockerfile paths carefully
- Test container build after changes
- Keep entrypoint.sh paths updated

## Implementation Order

1. **Create documentation** of current state (DONE - CONSOLIDATED_DOCS.md)
2. **Create archive directories**
3. **Move unused schemas** to archive
4. **Document active schema**
5. **Test everything still works**
6. **Move unused services** to archive
7. **Test again**
8. **Update README** with clear, current information
9. **Commit with clear message** about reorganization

## Success Criteria

- [ ] API still responds on port 8104
- [ ] CLI commands still work in Docker
- [ ] No unused schemas in scripts/
- [ ] Clear documentation of active components
- [ ] Archive preserves all code for future reference