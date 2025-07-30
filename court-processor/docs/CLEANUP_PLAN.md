# Directory Cleanup Plan

## Proposed New Structure

```
court-processor/
├── src/                           # Source code
│   ├── pipeline/                  # Pipeline implementation
│   │   ├── __init__.py
│   │   ├── eleven_stage_pipeline.py
│   │   ├── exceptions.py
│   │   ├── validators.py
│   │   └── error_reporter.py
│   ├── services/                  # Services (keep as-is)
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── document_ingestion_service.py
│   │   ├── courtlistener_service.py
│   │   └── recap/
│   ├── processors/                # Document processors
│   │   ├── __init__.py
│   │   ├── pdf_processor.py
│   │   ├── judge_extractor.py
│   │   └── document_classifier.py
│   └── utils/                     # Utilities
│       ├── __init__.py
│       └── (existing utils)
├── tests/                         # All tests
│   ├── unit/
│   ├── integration/
│   └── test_data/
├── scripts/                       # Executable scripts
│   ├── run_pipeline.py
│   ├── analyze/                   # Analysis scripts
│   ├── debug/                     # Debug scripts
│   └── data_import/              # Import scripts
├── config/                        # Configuration
│   ├── docker/
│   └── settings/
├── docs/                          # Documentation
│   ├── current/                   # Current status docs
│   ├── guides/                    # How-to guides
│   └── architecture/             # System design
├── data/                          # Data storage
│   ├── pdfs/                      # All PDFs
│   ├── exports/                   # CSV exports
│   └── results/                   # Pipeline results
├── docker/                        # Docker files
│   ├── Dockerfile
│   └── docker-compose files
├── requirements.txt
├── README.md
└── .gitignore
```

## Cleanup Steps

### Phase 1: Create New Structure
1. Create `src/` directory and subdirectories
2. Create organized `tests/` structure
3. Create `scripts/` subdirectories
4. Create `data/` subdirectories

### Phase 2: Move Core Files
1. Move pipeline files to `src/pipeline/`
2. Move processors to `src/processors/`
3. Keep services in place (already well-organized)
4. Move utils to `src/utils/`

### Phase 3: Organize Tests
1. Move all `test_*.py` to `tests/`
2. Categorize into unit/integration
3. Keep test_data together

### Phase 4: Clean Up Scripts
1. Move `run_*.py` to `scripts/`
2. Move `analyze_*.py` to `scripts/analyze/`
3. Move `debug_*.py` to `scripts/debug/`
4. Move import scripts to `scripts/data_import/`

### Phase 5: Consolidate Data
1. Merge PDF directories into `data/pdfs/`
2. Move JSON results to `data/results/`
3. Move CSV exports to `data/exports/`

### Phase 6: Archive or Remove
1. Archive old pipeline result JSONs
2. Remove duplicate scripts
3. Remove obsolete debug files
4. Clean up root directory

## Benefits of New Structure

1. **Clear separation**: Source code vs scripts vs data
2. **Better imports**: Proper Python package structure
3. **Easier navigation**: Logical grouping
4. **Testing**: All tests in one place
5. **Data management**: Centralized data storage
6. **Documentation**: Organized by purpose

## Files to Review Before Moving

### Potentially Obsolete
- Multiple pipeline versions (adaptive, etc.)
- Old test results JSONs
- Debug scripts that were one-time use
- Duplicate analysis scripts

### Need Classification
- Various "fetch" and "process" scripts
- Integration test files
- Utility scripts with unclear purpose

## Post-Cleanup Actions

1. Update all imports in Python files
2. Update paths in configuration
3. Test the pipeline still works
4. Update documentation with new structure
5. Create navigation README