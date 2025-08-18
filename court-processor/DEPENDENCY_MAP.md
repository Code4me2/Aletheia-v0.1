# Court Processor Dependency Map

## Active Entry Points

### CLI (`court_processor`)
Direct imports:
- `services.enhanced_ingestion_service.EnhancedIngestionService` (used by collect judge, data fix)
- `services.database.get_db_connection` (used throughout)
- `services.unified_collection_service.UnifiedCollectionService` (used by collect court)
- `eleven_stage_pipeline_robust_complete.RobustElevenStagePipeline` (used by pipeline command)

### Unified Collection Service (`services/unified_collection_service.py`)
Direct imports:
- `services.enhanced_standalone_processor.EnhancedStandaloneProcessor`
- `services.database.get_db_connection`
- `services.document_ingestion_service.DocumentIngestionService`
- `eleven_stage_pipeline_robust_complete.RobustElevenStagePipeline` (optional)

### Enhanced Standalone Processor (`services/enhanced_standalone_processor.py`)
Direct imports:
- `comprehensive_judge_extractor.ComprehensiveJudgeExtractor`
- No service dependencies (self-contained)

### Enhanced Ingestion Service (`services/enhanced_ingestion_service.py`)
Direct imports:
- `services.courtlistener_service.CourtListenerService`
- `services.database.get_db_connection`
- `services.enhanced_retry_logic.EnhancedRetryClient`
- `comprehensive_judge_extractor.ComprehensiveJudgeExtractor`

### Document Ingestion Service (`services/document_ingestion_service.py`)
Direct imports:
- `services.courtlistener_service.CourtListenerService`
- `services.database.get_db_connection`
- `services.recap.authenticated_client.AuthenticatedRECAPClient`

### Eleven Stage Pipeline (`eleven_stage_pipeline_robust_complete.py`)
Direct imports:
- `services.database.get_db_connection`
- `services.service_config.SERVICES`
- `enhancements.enhanced_storage_with_dockets.EnhancedStorageProcessor`
- `error_reporter.ErrorCollector`
- `pipeline_validators` (various validators)
- `pipeline_exceptions` (custom exceptions)

## Files Currently in Active Use

### Core Files (Definitely Keep)
1. `court_processor` - CLI entry point
2. `services/database.py` - Database connections
3. `services/unified_collection_service.py` - Main collection orchestrator
4. `services/enhanced_standalone_processor.py` - Improved processor
5. `comprehensive_judge_extractor.py` - Judge extraction
6. `eleven_stage_pipeline_robust_complete.py` - Pipeline processing

### Currently Used but Could Be Replaced
1. `services/enhanced_ingestion_service.py` - Still used by `collect judge` and `data fix`
2. `services/courtlistener_service.py` - Used by enhanced_ingestion_service
3. `services/enhanced_retry_logic.py` - Used by enhanced_ingestion_service
4. `services/document_ingestion_service.py` - Used by unified_collection_service for PDF extraction

### Supporting Files (Check if Actually Used)
1. `services/service_config.py` - Used by pipeline
2. `error_reporter.py` - Used by pipeline
3. `pipeline_validators.py` - Used by pipeline
4. `pipeline_exceptions.py` - Used by pipeline
5. `enhancements/enhanced_storage_with_dockets.py` - Used by pipeline

## Potentially Redundant Files

### Duplicate Processors
- `services/standalone_enhanced_processor.py` - Superseded by enhanced_standalone_processor.py
- `services/unified_document_processor.py` - Not imported anywhere
- `services/legal_document_enhancer.py` - Not imported anywhere
- `services/recap_processor.py` - Not imported anywhere

### Duplicate Fetchers
- `services/enhanced_courtlistener_fetcher.py` - Not imported anywhere
- `services/flp_integration.py` - Not imported anywhere

### Other Unused Services
- `services/comprehensive_field_mapper.py` - Not imported anywhere
- `services/judge_initials_mapping.py` - Not imported anywhere
- `services/recap_docket_service.py` - Not imported anywhere
- `services/error_reporter.py` - Duplicate of root error_reporter.py

### Test Files (Review Separately)
- 25 test files, many with overlapping RECAP tests

### Utils (Likely Unused)
- `utils/database_optimizations.py`
- `utils/progressive_enhancement.py`
- `utils/testing_patterns.py`
- `utils/configuration.py`
- `utils/flp_api_endpoints.py`
- `utils/pagination_patterns.py`
- `utils/validation.py`

### Scripts (Hardcoded/Obsolete)
- `scripts/ingest_gilstrap_cases.py`
- `scripts/utilities/retrieve_gilstrap_2022_2023.py`
- Various other scripts with hardcoded parameters

## Migration Strategy

1. **Update CLI** to use UnifiedCollectionService for all collection operations
2. **Move redundant files** to REDUNDANT_FILES_TEMP
3. **Test all CLI commands**
4. **Restore only what breaks**