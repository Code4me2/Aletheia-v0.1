# Directory Status Before Cleanup

## Summary Statistics
- **Total Size**: 8.6M
- **Python Files**: 128
- **Documentation Files**: 44
- **JSON Files**: 52
- **Directories**: Multiple nested structures

## Current Directory Structure

### Core Implementation Files
- `eleven_stage_pipeline_robust_complete.py` - Main pipeline (1,836 lines)
- `pdf_processor.py` - OCR implementation
- `court_processor_orchestrator.py` - Pipeline orchestrator
- `pipeline_exceptions.py` - Custom exceptions
- `pipeline_validators.py` - Validation logic
- `error_reporter.py` - Error collection

### Services Directory
- `services/` - Core service implementations
  - `database.py` - Database connections
  - `document_ingestion_service.py` - Document retrieval
  - `courtlistener_service.py` - API integration
  - `recap/` - RECAP-specific services
  - Various field mappers and utilities

### Test Files (Many)
- `test_*.py` files scattered in root (22 files)
- `tests/` directory with additional tests
- `test_data/` directory

### Data/Output Files
- Multiple JSON result files from pipeline runs
- CSV exports
- Downloaded PDFs in various directories

### Documentation
- Status documents (CURRENT_STATUS_JULY_2025.md, etc.)
- Configuration guides
- Pipeline documentation
- Integration status reports

### Utility Scripts
- Debug scripts (`debug_*.py`)
- Analysis scripts (`analyze_*.py`)
- Run scripts (`run_*.py`)
- Data processing scripts

### Directories
```
.
├── api/                    # API implementations
├── archive/                # Archived files
├── config/                 # Configuration files
├── data/                   # Data files
├── docs/                   # Additional documentation
├── downloaded_pdfs/        # Downloaded PDF storage
├── logs/                   # Log files
├── migrations/             # Database migrations
├── n8n_workflows/          # Workflow files
├── opinion_pdfs/           # Opinion PDF storage
├── recap_pdfs/             # RECAP PDF storage
├── reports/                # Generated reports
├── scripts/                # Utility scripts
├── services/               # Core services
├── test_data/              # Test data
├── tests/                  # Test suite
└── utils/                  # Utility modules
```

## Observations

### Issues to Address
1. **Test files scattered**: Test files in root directory should be in tests/
2. **Multiple result JSONs**: Pipeline run results cluttering root
3. **Debug scripts**: Many one-off debug scripts in root
4. **Duplicate functionality**: Multiple scripts doing similar things
5. **PDF directories**: Multiple directories for PDFs (opinion_pdfs, recap_pdfs, downloaded_pdfs)

### What's Working Well
1. **Services directory**: Well-organized core services
2. **Pipeline files**: Core pipeline logic is centralized
3. **Documentation**: Good documentation coverage

### Recommended Cleanup Actions
1. Move all test files to `tests/` directory
2. Move pipeline results to `reports/` or archive
3. Consolidate PDF storage directories
4. Move debug/analysis scripts to `scripts/debug/`
5. Remove duplicate or obsolete files
6. Create clear README for navigation

## Critical Files to Preserve
1. Core pipeline implementation
2. Services directory structure
3. Current documentation
4. Configuration files
5. Database migrations
6. Active test suite