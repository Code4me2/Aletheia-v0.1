# Court Processor - Judiciary Insights Platform

A unified CLI for analyzing judicial behavior, court patterns, and legal trends. Replaces 45+ scattered scripts with a single human-centered interface focused on judiciary insights.

## 🎯 Purpose

Enable data-driven analysis of:
- **Judge Attribution**: Understanding WHO made decisions (>95% attribution target)
- **Temporal Patterns**: Tracking judicial behavior over time
- **Case Tracking**: Following cases through their lifecycle
- **Court Jurisdiction**: Regional and jurisdictional patterns

## ⚡ Key Features

- **Unified CLI**: Single entry point replacing 45+ scripts
- **Human-Centered Commands**: Organized by user goals, not technical implementation
- **Data Quality Focus**: Clear visibility into judge attribution and metadata completeness
- **Progress Feedback**: Know what's happening during long operations
- **11-Stage Pipeline**: Production-ready processing with 78% metadata completeness

## 🚀 Quick Start

### Using Docker (Recommended)
```bash
# Check data quality status
docker exec aletheia-court-processor-1 ./court_processor data status

# Analyze a specific judge
docker exec aletheia-court-processor-1 ./court_processor analyze judge "Rodney Gilstrap"

# Collect documents from a court
docker exec aletheia-court-processor-1 ./court_processor collect court txed --years 2020-2025 --limit 100

# Run enhancement pipeline
docker exec aletheia-court-processor-1 ./court_processor pipeline run --limit 50 --no-strict
```

### Local Usage (Development)
```bash
# Make executable
chmod +x court_processor

# Set database connection
export DATABASE_URL="postgresql://user:pass@localhost:5432/dbname"

# Run commands
./court_processor data status
./court_processor analyze judge "Rodney Gilstrap" --court txed
```

## 📋 Command Structure

The CLI is organized around user goals:

### 1. Analyze - Get Judiciary Insights
```bash
# Analyze a judge's patterns
docker exec aletheia-court-processor-1 ./court_processor analyze judge "Rodney Gilstrap" [options]
  --court COURT_ID        # Filter by court (e.g., txed)
  --years YYYY-YYYY       # Year range (e.g., 2020-2025)
  --focus TYPE            # Case type focus (e.g., patent)
  --export FORMAT         # Export format (json|csv|summary)
```

### 2. Data - Export, List & Fix
```bash
# Export full court opinions with content
docker exec aletheia-court-processor-1 ./court_processor data export [options]
  --type TYPE            # Document type (opinion|opinion_doctor|020lead|docket)
  --judge "Name"         # Filter by judge name
  --court COURT_ID       # Filter by court
  --min-content-length N # Minimum content size (filters placeholders)
  --format FORMAT        # json|jsonl|csv
  --full-content         # Include full opinion text
  --content-format TYPE  # raw|text|both
  --compact              # API-ready compact JSON
  --pretty               # Human-readable formatting

# List documents
docker exec aletheia-court-processor-1 ./court_processor data list [options]
  --status STATUS        # with-content|without-content|all
  --type TYPE            # Document type filter
  --limit N              # Number to show

# Check data quality status
docker exec aletheia-court-processor-1 ./court_processor data status

# Fix data quality issues
docker exec aletheia-court-processor-1 ./court_processor data fix [options]
  --judge-attribution     # Fix missing judge data
  --docket-linking       # Fix missing docket numbers
  --filter-court COURT   # Only fix specific court
  --limit N              # Maximum documents to fix
```

### 3. Collect - Gather Documents
```bash
# Collect from a court
docker exec aletheia-court-processor-1 ./court_processor collect court COURT_ID [options]

# Collect by judge
docker exec aletheia-court-processor-1 ./court_processor collect judge "Judge Name" [options]
  --court COURT_ID       # Filter by court
  --years YYYY-YYYY      # Year range
  --limit N              # Maximum documents
```

### 4. Pipeline - Process Documents
```bash
# Run enhancement pipeline
docker exec aletheia-court-processor-1 ./court_processor pipeline run [options]
  --limit N              # Number of documents (default: 10)
  --force                # Force reprocess
  --unprocessed          # Only new documents
  --extract-pdfs         # Extract PDF content
  --no-strict            # Process with warnings
```

## 📊 Current Status

### Data Quality (As of Testing)
- **Total Documents**: 2,245
- **Judge Attribution**: 12.0% ❌ (need >95%)
- **Docket Numbers**: 4.1% ❌ (need >90%)
- **Court IDs**: 12.7% ❌ (need 100%)
- **Text Content**: 93.1% ⚠️ (need >95%)

### Pipeline Performance
- **11-Stage Pipeline**: Production ready with 78% metadata completeness
- **Court Resolution**: 100% success rate
- **Citation Extraction**: 100% success rate
- **Judge Enhancement**: 10-70% (varies by document type)
- **PDF Extraction**: Available with `--extract-pdfs` flag

### Recent Improvements (August 2025)
- ✅ **Unified CLI**: Replaced 45+ scripts with single human-centered interface
- ✅ **Enhanced Ingestion**: Comprehensive judge extraction from multiple sources
- ✅ **Progress Feedback**: Clear status during long operations
- ✅ **Data Quality Tools**: Built-in commands to check and fix issues
- ✅ **Reduced Retries**: Faster response for 202 processing documents

## 🔍 Example Workflows

### Complete Judge Analysis
```bash
# 1. Check if we have data for the judge
docker exec aletheia-court-processor-1 ./court_processor analyze judge "Rodney Gilstrap"

# 2. If data quality is low, collect more
docker exec aletheia-court-processor-1 ./court_processor collect judge "Rodney Gilstrap" --court txed --years 2020-2025

# 3. Process through enhancement pipeline
docker exec aletheia-court-processor-1 ./court_processor pipeline run --limit 100 --no-strict

# 4. Analyze with complete data
docker exec aletheia-court-processor-1 ./court_processor analyze judge "Rodney Gilstrap" --export json
```

### Fix Data Quality Issues
```bash
# 1. Check current status
docker exec aletheia-court-processor-1 ./court_processor data status

# 2. Fix judge attribution if < 95%
docker exec aletheia-court-processor-1 ./court_processor data fix --judge-attribution

# 3. Verify improvement
docker exec aletheia-court-processor-1 ./court_processor data status
```

## 📚 Practical Examples

### Export Full Court Opinions
```bash
# Export real court opinions (50KB+ of legal text)
docker exec aletheia-court-processor-1 ./court_processor data export \
  --type 020lead \
  --min-content-length 50000 \
  --limit 5 \
  --full-content \
  --content-format text \
  --compact \
  --output patent_opinions.json

# Human-readable export with formatting
docker exec aletheia-court-processor-1 ./court_processor data export \
  --type 020lead \
  --min-content-length 30000 \
  --limit 3 \
  --pretty
```

### Search and Analyze
```bash
# Search for patent infringement cases
docker exec aletheia-court-processor-1 ./court_processor search opinions "patent infringement" --limit 10

# Analyze Judge Gilstrap's patent cases
docker exec aletheia-court-processor-1 ./court_processor analyze judge "Rodney Gilstrap" --focus patent
```

### Data Quality Management
```bash
# List documents with actual content
docker exec aletheia-court-processor-1 ./court_processor data list --status with-content --limit 10

# Export Judge Gilstrap's opinions for analysis
docker exec aletheia-court-processor-1 ./court_processor data export \
  --judge "Gilstrap" \
  --min-content-length 30000 \
  --format csv \
  --output gilstrap_analysis.csv
```

## 📁 Project Structure

```
court-processor/
├── court_processor                          # NEW: Unified CLI entry point
├── cp                                       # NEW: Shorthand wrapper
├── eleven_stage_pipeline_robust_complete.py # Production pipeline
├── services/                                
│   ├── enhanced_ingestion_service.py       # NEW: Enhanced data collection
│   ├── courtlistener_service.py           # API client
│   └── database.py                         # Database connections
├── comprehensive_judge_extractor.py        # NEW: Multi-source judge extraction
├── scripts/                                # Legacy scripts (being replaced)
│   └── utilities/                          # 45+ individual scripts
└── archived/                               # Old implementations
    ├── cli_implementations_2025/           # Previous CLI attempts
    └── broken_components/                  # Unified processor (broken)
```

## 🔧 Configuration

Environment variables (in parent `.env`):
```env
COURTLISTENER_API_TOKEN=your-token-here
DATABASE_URL=postgresql://user:pass@host:5432/dbname  # For local development
```

## 🚧 Known Issues & Solutions

### Issue: 202 Processing Delays
- **Symptom**: CourtListener returns 202 for documents still processing
- **Solution**: Enhanced retry logic with exponential backoff (automatically handled)

### Issue: Low Judge Attribution (12%)
- **Symptom**: Most documents missing judge information
- **Solution**: Use `data fix --judge-attribution` or collect with comprehensive extraction

### Issue: Database Connection
- **Symptom**: "could not translate host name 'db'" error
- **Solution**: Use Docker commands or set DATABASE_URL for local development

## 📖 Documentation

### Current Documentation
- [UNIFIED_CLI_README.md](./UNIFIED_CLI_README.md) - Detailed CLI usage guide
- [CLI_HUMAN_USABILITY_PLAN.md](./CLI_HUMAN_USABILITY_PLAN.md) - Design rationale
- [COMPREHENSIVE_SYSTEM_UNDERSTANDING.md](./COMPREHENSIVE_SYSTEM_UNDERSTANDING.md) - System architecture
- [API_FIELD_MAPPING_CRITICAL.md](./API_FIELD_MAPPING_CRITICAL.md) - API traversal details

### Legacy Documentation
- Moved to `docs/` directory for historical reference
- See `archived/` for old implementations

## 🤝 Contributing

Focus areas for contribution:
- Improve judge extraction patterns
- Add more analysis commands
- Enhance progress feedback
- Create export templates

## 📝 License

Part of Aletheia-v0.1 - see parent repository for license details.