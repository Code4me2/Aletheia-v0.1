# Court Processor File Inventory

## Active Core Files (Root Level)
✅ **api.py** - REST API server (port 8104)
✅ **cli.py** - Command-line interface
✅ **processor.py** - Document processing pipeline
✅ **exceptions.py** - Custom exception classes
✅ **validators.py** - Validation logic
✅ **court_processor** - Backward compatibility wrapper for CLI

## Configuration & Documentation
✅ **schema.sql** - Active database schema
✅ **requirements.txt** - Python dependencies
✅ **Dockerfile** - Container configuration
✅ **entrypoint.sh** - Container startup script
✅ **README.md** - Main documentation
✅ **CHANGES.md** - Recent changes summary
✅ **INVENTORY.md** - This file
✅ **legal_dictionary.txt** - Legal terms reference

## Active Directories
✅ **extractors/** - Extraction modules
  - judge.py - Judge name extraction
  - pdf.py - PDF processing
  - document_type.py - Document type detection

✅ **services/** - External integrations
  - database.py - Database connections
  - courtlistener.py - CourtListener API
  - ingestion.py - Document ingestion
  - config.py - Service configuration

✅ **utils/** - Utility functions
  - configuration.py - App configuration
  - validation.py - Data validation
  - reporter.py - Error reporting

✅ **config/** - Configuration files
  - courts.yaml - Court definitions
  - docker/doctor_docker_setup.yaml - Docker health checks

✅ **scripts/** - Active scripts
  - court-schedule - Cron schedule for processing

✅ **test_data/** - Test fixtures
  - Various JSON test data files

✅ **tests/** - Test suite
  - 14 test files for different components

✅ **docs/** - Documentation
  - ANALYSIS.md - System analysis
  - REORGANIZATION.md - Reorganization plan
  - NAMING_CHANGES.md - Naming convention changes

## Archived (in archived/ directory)
✅ **database_schemas/** - 5 unused SQL schemas
✅ **services/** - RECAP and FLP integrations
✅ **scripts/** - Legacy utility scripts
✅ **api/** - Old API implementation
✅ **n8n_workflows/** - n8n workflow definitions
✅ **reports/** - Old workflow reports
✅ **reorganize_directory.sh** - One-time reorganization script
✅ **run_verification_docker.sh** - Docker verification script
✅ **test_in_docker.sh** - Docker test runner
✅ **ARCHIVE_MANIFEST.md** - Archive documentation

## Summary
- **Active Files**: 14 root files + 6 directories
- **Archived**: ~50+ legacy files and directories
- **Test Files**: 14 test files + test data
- **Documentation**: Comprehensive and up-to-date

All files are accounted for and properly organized!