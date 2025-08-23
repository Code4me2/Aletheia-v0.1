# Court Processor Integration Guide

**Version 1.0.0** - Successfully integrated and tested on June 26, 2025

## Overview

The court processor has been successfully integrated into data-compose, providing automated court opinion scraping and text extraction for RAG pipelines.

## What's Included

### New Service: court-processor

Added to `docker-compose.yml`:
```yaml
court-processor:
  build:
    context: ./court-processor
    dockerfile: Dockerfile
  environment:
    DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
    PYTHONPATH: /app
  volumes:
    - ./court-data/pdfs:/data/pdfs
    - ./court-data/logs:/data/logs
    - ./court-processor:/app
  depends_on:
    - db
  networks:
    - backend
  restart: unless-stopped
```

### Database Schema

New `court_data` schema in PostgreSQL with:
- **judges** table: Stores unique judge names
- **opinions** table: Full opinion text, metadata, and judge references
- **processing_log** table: Tracks scraping runs and errors

### Directory Structure

```
data-compose/
├── court-processor/          # Court processor source code
│   ├── processor.py         # Main processing logic
│   ├── pdf_processor.py     # PDF text extraction
│   ├── config/courts.yaml   # Court configurations
│   └── scripts/             # Database init and cron
└── court-data/              # Data storage
    ├── pdfs/               # Downloaded PDF files
    └── logs/               # Processing logs
```

## Verified Functionality

### Successfully Tested Features

1. **PDF Download & Storage**
   - Downloads court opinions from ustaxcourt.gov
   - Stores PDFs in `/court-data/pdfs/[court-code]/`
   - Handles duplicate detection

2. **Text Extraction**
   - PyMuPDF extracts text from PDFs
   - OCR fallback for scanned documents
   - Page markers preserved in text

3. **Judge Organization**
   - Normalizes judge names (e.g., "Smith" → "Judge Smith")
   - Links opinions to judges
   - Enables judge-based queries

4. **Full-Text Search**
   - PostgreSQL text search with highlighting
   - Query by keywords across all opinions
   - Returns excerpts with search terms highlighted

## Test Results

From Tax Court scraping (June 26, 2025):
```
- 20 opinions successfully processed
- 12 unique judges identified
- 100% text extraction success
- All opinions searchable by judge and text
```

## Usage Examples

### Query by Judge
```sql
-- Get all opinions by Judge Lauber
SELECT o.case_name, o.case_date, o.docket_number 
FROM court_data.opinions o
JOIN court_data.judges j ON o.judge_id = j.id
WHERE j.name = 'Judge Lauber'
ORDER BY o.case_date DESC;
```

### Full-Text Search
```sql
-- Search for "tax deduction" across all opinions
SELECT case_name, 
       ts_headline('english', text_content, query, 'MaxWords=20') as excerpt
FROM court_data.opinions,
     plainto_tsquery('english', 'tax deduction') query
WHERE to_tsvector('english', text_content) @@ query;
```

### Get Unprocessed Opinions for RAG
```sql
-- Get opinions not yet indexed
SELECT o.id, o.text_content, j.name as judge_name
FROM court_data.opinions o
JOIN court_data.judges j ON o.judge_id = j.id
WHERE o.vector_indexed = false
LIMIT 100;
```

## Daily Automation

Cron schedule (automatically configured):
- Tax Court: Daily at 2 AM
- First Circuit: Daily at 3 AM (when enabled)
- DC Circuit: Daily at 4 AM (when enabled)

## Integration with n8n

The court processor data is ready for n8n workflows:

1. Create PostgreSQL node to query opinions
2. Pass through Hierarchical Summarization
3. Index in Haystack for vector search
4. Update `vector_indexed` flag

## Configuration

### Enable Additional Courts

Edit `court-processor/config/courts.yaml`:
```yaml
courts:
  ca1:
    name: "First Circuit Court of Appeals"
    active: true  # Change to true to enable
    module: "ca1"
```

### Supported Courts
- `tax`: US Tax Court ✓ (tested)
- `ca1`: First Circuit Court of Appeals
- `dc`: DC Circuit Court of Appeals

## Maintenance

### Check Processing Status
```bash
docker-compose exec db psql -U your_db_user -d your_db_name -c "
SELECT court_code, run_date, opinions_processed, status 
FROM court_data.processing_log 
ORDER BY started_at DESC LIMIT 5;"
```

### Monitor Disk Usage
```bash
# Check PDF storage size
du -sh court-data/pdfs/

# Check database size
docker-compose exec db psql -U your_db_user -d your_db_name -c "
SELECT pg_size_pretty(pg_database_size('your_db_name'));"
```

## Security Notes

- Court processor runs in isolated container
- No external API exposure
- PDFs downloaded to restricted directory
- All text sanitized before database storage
- Judge names normalized to prevent injection

## Future Enhancements

1. **Additional Courts**: Add more federal and state courts
2. **Alert System**: n8n workflows for high-priority cases
3. **Deduplication**: Smart handling of amended opinions
4. **Analytics**: Judge-specific analytics and trends