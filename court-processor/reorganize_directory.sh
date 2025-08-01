#!/bin/bash
# Reorganize court-processor directory for better structure

echo "Reorganizing court-processor directory..."

# Create organized directory structure
mkdir -p archive/test_scripts
mkdir -p archive/investigation_scripts
mkdir -p archive/old_implementations
mkdir -p config
mkdir -p docs
mkdir -p scripts/utilities
mkdir -p scripts/data_import
mkdir -p services/recap

# Move test scripts to archive
echo "Moving test scripts to archive..."
mv test_*.py archive/test_scripts/ 2>/dev/null || true
mv check_*.py archive/investigation_scripts/ 2>/dev/null || true
mv investigate_*.py archive/investigation_scripts/ 2>/dev/null || true
mv improved_*.py archive/old_implementations/ 2>/dev/null || true

# Move documentation
echo "Moving documentation..."
mv *.md docs/ 2>/dev/null || true
mv *.txt docs/ 2>/dev/null || true
mv API_courtlistener.txt ../docs/ 2>/dev/null || true  # Keep in parent
mv recap_documentation.txt docs/ 2>/dev/null || true

# Move utility scripts
echo "Moving utility scripts..."
mv insert_test_data.py scripts/data_import/ 2>/dev/null || true
mv retrieve_edtx_5years.py scripts/utilities/ 2>/dev/null || true

# Move test results to archive
mkdir -p archive/test_results
mv *_test_*.json archive/test_results/ 2>/dev/null || true
mv test_results_*.json archive/test_results/ 2>/dev/null || true

# Move old pipeline versions to archive
echo "Moving old pipeline implementations..."
mv *_pipeline_*.py archive/old_implementations/ 2>/dev/null || true
mv pipeline_*.py archive/old_implementations/ 2>/dev/null || true

# Keep only core files in root
echo "Core files remaining in root:"
echo "- court_processor_orchestrator.py (main orchestrator)"
echo "- eleven_stage_pipeline_robust_complete.py (current pipeline)"
echo "- pdf_processor.py (PDF processing)"
echo "- requirements.txt"
echo "- Dockerfile"
echo "- .env files"

# Create README for organization
cat > DIRECTORY_STRUCTURE.md << 'EOF'
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
EOF

echo ""
echo "Reorganization complete!"
echo "Review DIRECTORY_STRUCTURE.md for the new organization"
echo ""
echo "Next steps:"
echo "1. Review files that couldn't be moved (if any)"
echo "2. Update imports in remaining files"
echo "3. Add .gitignore entries for archive directories"
echo "4. Implement RECAP Fetch client in services/recap/"