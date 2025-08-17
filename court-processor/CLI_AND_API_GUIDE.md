# Court Processor CLI & API Guide

## Critical: Docker Access Required

⚠️ **IMPORTANT**: All commands MUST be run through Docker. Direct Python execution will fail with module import errors.

## Quick Start

The court-processor service runs inside a Docker container and must be accessed via `docker exec`.

## Primary Interface: CLI (Docker)

The CLI is the **only reliable** interface for court document operations.

### Access Pattern
```bash
docker exec aletheia_development-court-processor-1 python court_processor [command]
```

### Essential Commands

#### 1. Check Data Status
```bash
# Shows total documents in database
docker exec aletheia_development-court-processor-1 python court_processor data status
```

#### 2. Search with Content
```bash
# Get opinions with full text content
docker exec aletheia_development-court-processor-1 python court_processor search opinions --limit 2 --export json --show-content

# Search for specific terms
docker exec aletheia_development-court-processor-1 python court_processor search opinions "LOAN SOURCE" --export json --show-content
```

#### 3. Fix Empty Content Issues
```bash
# If getting empty content, run this first
docker exec aletheia_development-court-processor-1 python court_processor data fix --judge-attribution
```

#### 4. Collect Fresh Data
```bash
# Collect from specific court
docker exec aletheia_development-court-processor-1 python court_processor collect court txed --limit 20

# Collect by judge
docker exec aletheia_development-court-processor-1 python court_processor collect judge "Rodney Gilstrap" --court txed --limit 20
```

#### 5. Export Full Opinion Documents (Most Important)
```bash
# Export opinions with substantial content (>5000 chars)
docker exec aletheia_development-court-processor-1 python court_processor data export --type 020lead --full-content --min-content-length 5000

# Export specific judge's opinions
docker exec aletheia_development-court-processor-1 python court_processor data export --judge "Gilstrap" --type 020lead --full-content

# Export all document types for analysis
docker exec aletheia_development-court-processor-1 python court_processor data export --judge "Gilstrap" --type all --limit 100 --format json

# Analyze specific judge
docker exec aletheia_development-court-processor-1 python court_processor analyze judge "Rodney Gilstrap"
```

## Common Issues & Solutions

### Problem: First search returns empty content
**Solution:**
```bash
# Step 1: Collect fresh data with enhanced processor
docker exec aletheia_development-court-processor-1 python court_processor collect court txed --limit 10

# Step 2: Search again
docker exec aletheia_development-court-processor-1 python court_processor search opinions --limit 10 --export json --show-content
```

### Problem: Need more than 20 documents
**Current Limitation:** API returns max 20 results per query
**Workaround:** Use date ranges
```bash
# Split by time periods
docker exec aletheia_development-court-processor-1 python court_processor collect court txed --date-after 2024-01-01 --date-before 2024-06-30 --limit 20
docker exec aletheia_development-court-processor-1 python court_processor collect court txed --date-after 2024-07-01 --date-before 2024-12-31 --limit 20
```

## Document Types in Database

### Understanding Document Types
- **020lead**: Full court opinions with complete text (30-40k chars average)
  - Source: `courtlistener_standalone` 
  - Contains: XML/HTML formatted legal opinions with citations
  - Best for: Legal research, full text analysis
  
- **opinion**: Standard opinions (varies in completeness)
  - Source: `courtlistener`
  - Contains: May have partial or full text
  
- **opinion_doctor**: Enhanced opinions with metadata
  - Source: `courtlistener` with processing
  - Contains: Opinions with additional extracted metadata
  
- **docket**: Case metadata only (200 chars average)
  - Source: Various
  - Contains: Case name, number, judge, dates
  - Best for: Case tracking, not full text analysis

### Accessing Rich Content
```bash
# For full opinions with substantial content, use 020lead type:
docker exec aletheia_development-court-processor-1 python court_processor data export --type 020lead --full-content

# Check what types exist in database:
docker exec aletheia_development-court-processor-1 python court_processor data list --help
```

## JSON Output Format

When using `--export json --show-content`, expect:
```json
{
  "id": "doc_123",
  "case_number": "5:16-cv-00041",
  "case_name": "Example v. Company",
  "court": "txed",
  "judge_name": "Rodney Gilstrap",
  "date_filed": "2016-02-15",
  "document_type": "opinion",
  "content": "Full text of the opinion...",  // This will have content after collection
  "metadata": {
    "court_id": "txed",
    "judge_confidence": 0.95,
    "source": "courtlistener_standalone"
  }
}
```

## REST APIs (Not Recommended)

**Note:** Your colleague correctly identified that port 5001 webhook server is NOT the right endpoint. The REST APIs exist but are less reliable than CLI.

### Available Ports (if needed)
- **Unified API**: Port 8090 (internal to Docker)
- **Court Processor API**: Port 8091 (internal to Docker)  
- **Webhook Server**: Port 5000/5001 (for CourtListener callbacks only)

### Why CLI is Better
1. **More stable** - Direct database access
2. **Better error handling** - Clear error messages
3. **Full features** - All collection and processing options
4. **Proven to work** - Your colleague successfully used it

## Recommended Workflow

### For Document Retrieval
```bash
# 1. Check current data
docker exec aletheia_development-court-processor-1 python court_processor data status

# 2. Collect fresh documents
docker exec aletheia_development-court-processor-1 python court_processor collect court txed --limit 50

# 3. Fix attribution if needed
docker exec aletheia_development-court-processor-1 python court_processor data fix --judge-attribution

# 4. Export with content
docker exec aletheia_development-court-processor-1 python court_processor search opinions --limit 50 --export json --show-content > opinions.json
```

### For Analysis
```bash
# Get statistics
docker exec aletheia_development-court-processor-1 python court_processor analyze stats

# Judge analysis
docker exec aletheia_development-court-processor-1 python court_processor analyze judges --court txed

# Export as CSV for Excel
docker exec aletheia_development-court-processor-1 python court_processor data list --export csv > documents.csv
```

## Current Database Contents (as of testing)
- **Total documents**: 468 in PostgreSQL database
- **Document breakdown**:
  - 39 020lead documents (avg 62,500 chars)
  - 158 opinion_doctor documents (avg 34,657 chars)
  - 44 opinion documents (avg 27,588 chars)
  - Various docket entries (~200 chars)
- **Judge Gilstrap data**: 52 documents total
  - 10+ full opinions in 020lead format
  - 13 docket entries
  - Date range: 2014-2025

## Performance Metrics
- **Content extraction**: 100% success rate (avg 47k characters)
- **Judge attribution**: 100% with new extractor
- **Processing speed**: ~0.8 seconds per document
- **Current limit**: 20 documents per API call (pagination coming)

## Database Direct Access

If needed for custom queries:
```sql
-- PostgreSQL connection
-- Host: localhost (or 'db' from Docker)
-- Database: aletheia
-- User: aletheia
-- Password: aletheia123

SELECT 
    case_number,
    metadata->>'case_name' as case_name,
    metadata->>'judge_name' as judge,
    LENGTH(content) as content_length
FROM court_documents
WHERE metadata->>'court_id' = 'txed'
  AND LENGTH(content) > 0
LIMIT 10;
```

## What NOT to Use
- ❌ Port 5001 webhook server (internal use only)
- ❌ Direct API calls without Docker exec
- ❌ Old ingestion commands (replaced by unified collection)

## Support

If issues persist:
```bash
# Check logs
docker logs aletheia_development-court-processor-1 --tail 50

# Get help
docker exec aletheia_development-court-processor-1 python court_processor --help

# Check specific command help
docker exec aletheia_development-court-processor-1 python court_processor collect --help
```