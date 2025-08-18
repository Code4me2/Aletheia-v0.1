# Cleanup Status Report

## Current Situation

### What We've Moved (Currently in REDUNDANT_FILES_TEMP)

#### Service Files That Are Actually Redundant:
1. `services/standalone_enhanced_processor.py` - Superseded by enhanced version
2. `services/enhanced_courtlistener_fetcher.py` - Not used anywhere
3. `services/comprehensive_field_mapper.py` - Not used anywhere
4. `services/judge_initials_mapping.py` - Not used anywhere
5. `services/recap_processor.py` - Not used anywhere
6. `services/error_reporter.py` - Duplicate of root error_reporter.py

#### Files We Should NOT Have Moved (But Can't Restore Yet):
These are needed by API servers but we need to verify API usage first:
- ❌ `services/unified_document_processor.py` - RESTORED (needed by unified_api.py)
- ❌ `services/recap_docket_service.py` - RESTORED (needed by APIs)
- ❌ `services/flp_integration.py` - RESTORED (needed by flp_api.py)
- ❌ `services/legal_document_enhancer.py` - RESTORED (needed by unified_document_processor)

#### Other Files Moved:
- `court_processor_orchestrator.py` - Seems unused
- `pipeline_adapter.py` - Seems unused
- 10 redundant test files (mostly RECAP variations)
- 4 utils files (database_optimizations, progressive_enhancement, testing_patterns, pagination_patterns)
- Hardcoded scripts (ingest_gilstrap_cases.py, retrieve_gilstrap_2022_2023.py)

## Critical Dependencies We've Discovered

### CLI Dependencies:
- ✅ `collect court` → UnifiedCollectionService → enhanced_standalone_processor
- ❌ `collect judge` → EnhancedIngestionService (needs updating)
- ❌ `data fix` → EnhancedIngestionService (needs updating)
- ✅ `analyze` commands → Direct database queries
- ✅ `pipeline` → eleven_stage_pipeline_robust_complete

### API Server Dependencies:
1. **unified_api.py** needs:
   - unified_document_processor
   - document_ingestion_service
   - recap_docket_service
   - recap.webhook_handler

2. **flp_api.py** needs:
   - flp_integration

3. **court_processor_api.py** needs:
   - document_ingestion_service
   - recap_docket_service
   - recap.webhook_handler

4. **webhook_server.py** needs:
   - recap.webhook_handler

## What's Actually Being Used

### Core Active Files:
1. CLI entry point (`court_processor`)
2. Database service (`services/database.py`)
3. Unified collection service (`services/unified_collection_service.py`)
4. Enhanced standalone processor (`services/enhanced_standalone_processor.py`)
5. Pipeline (`eleven_stage_pipeline_robust_complete.py`)
6. Judge extractor (`comprehensive_judge_extractor.py`)

### Services Still Needed But Could Be Improved:
1. `services/enhanced_ingestion_service.py` - Used by CLI but should be replaced
2. `services/courtlistener_service.py` - Used by multiple services
3. `services/document_ingestion_service.py` - Used for PDF extraction

### API-Related (Status Unknown):
- All 4 API servers
- Services they depend on

## Recommendations

### Immediate Actions:
1. ✅ DONE - Restore API files
2. ✅ DONE - Restore services needed by APIs
3. Test API functionality to determine if they're actively used
4. Update CLI to use UnifiedCollectionService everywhere

### Safe to Remove:
1. `services/standalone_enhanced_processor.py` (old Gilstrap version)
2. `services/enhanced_courtlistener_fetcher.py`
3. `services/comprehensive_field_mapper.py`
4. `services/judge_initials_mapping.py`
5. `services/recap_processor.py`
6. `services/error_reporter.py` (duplicate)
7. Redundant test files
8. Large utils files (if truly unused)
9. Hardcoded scripts

### Need Investigation:
1. Are the API servers actively used?
2. Can we consolidate the 4 API servers into 1?
3. Should we update enhanced_ingestion_service or replace it?

## Size Impact

- Files moved: 27 (excluding restored)
- Lines removed: ~9,000
- Potential additional removal: ~5,000 lines if APIs not needed

## Next Steps

1. Test API servers to see if they're functional and needed
2. Update CLI to use UnifiedCollectionService consistently
3. Remove truly redundant files permanently
4. Document which components are active vs legacy