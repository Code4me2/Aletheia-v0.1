# Court Processor Directory Structure

## Root Directory
Core implementation files only:
- `court_processor_orchestrator.py` - Main workflow orchestrator
- `eleven_stage_pipeline_robust_complete.py` - Current 11-stage pipeline
- `pdf_processor.py` - PDF text extraction
- `requirements.txt` - Python dependencies
- `Dockerfile` - Docker configuration

## `/services`
Microservices and API clients:
- `database.py` - Database connection management
- `courtlistener_service.py` - CourtListener API client
- `document_ingestion_service.py` - Document acquisition
- `flp_integration.py` - Free Law Project tools
- `/recap` - RECAP Fetch API client (new)

## `/config`
Configuration files and environment settings

## `/docs`
All documentation:
- Pipeline design documents
- API documentation
- Status reports

## `/scripts`
Utility and maintenance scripts:
- `/utilities` - General utilities
- `/data_import` - Data import tools

## `/tests`
Active test suite (minimal, focused tests only)

## `/archive`
Historical code and test results:
- `/test_scripts` - Old test files
- `/investigation_scripts` - Analysis scripts
- `/old_implementations` - Previous pipeline versions
- `/test_results` - Historical test outputs

## `/reports`
Generated reports and analytics
