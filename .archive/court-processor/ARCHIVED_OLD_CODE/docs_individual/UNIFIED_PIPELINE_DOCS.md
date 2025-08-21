# Unified Document Processing Pipeline

## Overview

The Unified Document Processor implements a complete pipeline for legal document processing:

```
CourtListener → FLP Enhancement → Unstructured.io → PostgreSQL
     ↓              ↓                    ↓              ↓
   Fetch      Add Citations        Parse Layout    Store with
  Opinions    Judge Info         Extract Text    Deduplication
             Court Details      Structure Docs
```

## Architecture

### Components

1. **CourtListener Integration**
   - Fetches opinions via REST API
   - Supports filtering by court and date
   - Handles pagination automatically

2. **FLP Enhancement Suite**
   - Citation extraction and resolution
   - Judge information enrichment
   - Court metadata enhancement
   - All 7 FLP tools integrated

3. **Unstructured.io Processing**
   - Advanced document parsing
   - Handles PDFs, HTML, and text
   - Extracts structured elements
   - OCR support for scanned documents

4. **PostgreSQL Storage**
   - Unified schema with JSONB fields
   - Full-text search indexing
   - Efficient deduplication
   - Comprehensive metadata storage

### Deduplication Strategy

Documents are uniquely identified using SHA-256 hashing of:
- Court ID
- Docket number
- Case name
- Filing date
- Author string
- First 1000 characters of text

This prevents duplicate storage while allowing updates.

## API Endpoints

### Base URL: `http://localhost:8090`

### 1. Process Batch
```bash
POST /process/batch
{
  "court_id": "ca9",           # Optional
  "date_filed_after": "2024-01-01",  # Optional
  "max_documents": 100
}
```

### 2. Process Single Document
```bash
POST /process/single
{
  "cl_document": {
    "id": 12345,
    "court_id": "ca9",
    "case_name": "Smith v. Jones",
    "plain_text": "Opinion text..."
  }
}
```

### 3. Check Duplicates
```bash
POST /deduplication/check
{
  "documents": [
    {"court_id": "ca9", "docket_number": "12-34567", ...},
    {"court_id": "ca9", "docket_number": "12-34568", ...}
  ]
}
```

### 4. Pipeline Status
```bash
GET /pipeline/status
```

### 5. Refresh Deduplication Cache
```bash
POST /pipeline/refresh-dedup-cache
```

## Database Schema

### Table: `court_data.opinions_unified`

```sql
-- Core fields from CourtListener
cl_id               INTEGER UNIQUE
court_id            VARCHAR(15)
docket_number       VARCHAR(500)
case_name           TEXT
date_filed          DATE
author_str          VARCHAR(200)
per_curiam          BOOLEAN
type                VARCHAR(20)

-- Content fields
plain_text          TEXT
html                TEXT
pdf_url             TEXT

-- Enhanced fields (JSONB)
citations           JSONB  -- Array of citation objects
judge_info          JSONB  -- Judge details from FLP
court_info          JSONB  -- Court metadata from FLP
structured_elements JSONB  -- Unstructured.io output

-- System fields
document_hash       VARCHAR(64) UNIQUE
created_at          TIMESTAMPTZ
updated_at          TIMESTAMPTZ
```

### Indexes
- B-tree: court_id, date_filed, case_name, document_hash
- GIN: citations, structured_elements (JSONB)
- Full-text: plain_text + case_name

## Setup Instructions

### 1. Database Migration
```bash
# Run the migration to create tables
docker-compose -f docker-compose.unified.yml run --rm unified-db-migrate
```

### 2. Start Services
```bash
# Start all required services
docker-compose up -d db unstructured-service

# Start the unified processor
docker-compose -f docker-compose.yml -f docker-compose.unified.yml up -d unified-processor
```

### 3. Verify Installation
```bash
# Check service health
curl http://localhost:8090/

# Check pipeline status
curl http://localhost:8090/pipeline/status
```

## Usage Examples

### 1. Process Recent Ninth Circuit Opinions
```python
import requests

response = requests.post('http://localhost:8090/process/batch', json={
    'court_id': 'ca9',
    'date_filed_after': '2024-01-01',
    'max_documents': 50
})

print(response.json())
# {
#   "total_fetched": 50,
#   "new_documents": 48,
#   "duplicates": 2,
#   "errors": 0,
#   "processing_time": "2024-01-15T10:30:00Z"
# }
```

### 2. Check for Duplicates Before Processing
```python
# Check if documents already exist
check_response = requests.post('http://localhost:8090/deduplication/check', json={
    'documents': [
        {'court_id': 'ca9', 'docket_number': '22-12345', 'case_name': 'Test v. Case'},
        # ... more documents
    ]
})

duplicates = check_response.json()['duplicates']
print(f"Found {len(duplicates)} duplicates")
```

### 3. Process Specific Document
```python
# Process a single opinion
doc_response = requests.post('http://localhost:8090/process/single', json={
    'cl_document': {
        'id': 12345,
        'court_id': 'ca9',
        'case_name': 'Smith v. Jones',
        'plain_text': 'Full opinion text...',
        'date_filed': '2024-01-10'
    }
})

if doc_response.json()['success']:
    print(f"Saved as ID: {doc_response.json()['saved_id']}")
```

## Monitoring and Maintenance

### Check Processing Stats
```sql
-- Total documents by court
SELECT court_id, COUNT(*) as total
FROM court_data.opinions_unified
GROUP BY court_id
ORDER BY total DESC;

-- Recent processing activity
SELECT DATE(created_at) as process_date, COUNT(*) as docs_processed
FROM court_data.opinions_unified
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY process_date DESC;

-- Citation statistics
SELECT 
    AVG(jsonb_array_length(citations)) as avg_citations,
    MAX(jsonb_array_length(citations)) as max_citations
FROM court_data.opinions_unified
WHERE citations != '[]';
```

### Clear Duplicate Documents
```sql
-- Find duplicates (shouldn't exist with dedup)
WITH duplicates AS (
    SELECT 
        document_hash,
        COUNT(*) as count
    FROM court_data.opinions_unified
    GROUP BY document_hash
    HAVING COUNT(*) > 1
)
SELECT * FROM duplicates;
```

## Performance Considerations

1. **Batch Size**: Recommended 50-100 documents per batch
2. **Memory Usage**: ~2MB per document during processing
3. **Processing Time**: ~2-5 seconds per document (depending on size)
4. **Dedup Cache**: Grows ~64 bytes per document

## Troubleshooting

### Common Issues

1. **Unstructured Service Timeout**
   - Large PDFs may timeout
   - Increase timeout in unstructured_processor.py
   - Consider processing PDFs separately

2. **Memory Issues**
   - Reduce batch size
   - Process large documents individually
   - Monitor Docker memory limits

3. **Duplicate Key Errors**
   - Refresh deduplication cache
   - Check for concurrent processing
   - Verify document_hash uniqueness

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

1. **Parallel Processing**
   - Process multiple documents concurrently
   - Implement worker pool

2. **Incremental Updates**
   - Track last processed date per court
   - Automatic scheduled processing

3. **Enhanced Deduplication**
   - Fuzzy matching for similar documents
   - Version tracking for updates

4. **Export Features**
   - Bulk export to Elasticsearch
   - Generate citation networks
   - Export to various formats