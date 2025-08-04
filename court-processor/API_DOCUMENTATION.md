# Court Processor API Documentation

## Overview

The Court Processor provides a unified API with distinct paths for legal document retrieval:

1. **Opinion Search API** - Broad searches on published court opinions (free)
2. **RECAP Docket API** - Specific docket retrieval from RECAP/PACER (may cost money)
3. **Processing Pipeline API** - Document processing through 11-stage pipeline

## Current Status (July 2025)

- ✅ **Unified API**: All endpoints consolidated on port 8090
- ✅ **Opinion Search**: Fully functional, connects to CourtListener
- ✅ **RECAP Docket**: Implemented with PACER authentication
- ✅ **Pipeline Integration**: Documents ready for 11-stage processing
- ✅ **Docker Deployment**: Running inside court-processor container

## API Endpoints

### Base URL
- Inside Docker: `http://localhost:8090`
- From host: Access through Docker network or add port mapping

### 1. Opinion Search (Broad Search)

#### `POST /search/opinions`

Search published court opinions using broad criteria.

**Request Body:**
```json
{
  "query": "intellectual property patent",      // Optional: Full-text search
  "court_ids": ["cafc", "ded"],                // Required: List of court IDs
  "date_filed_after": "2023-01-01",            // Optional: YYYY-MM-DD
  "date_filed_before": "2023-12-31",           // Optional: YYYY-MM-DD
  "document_types": ["opinion"],               // Optional: Default ["opinion"]
  "max_results": 100,                          // Optional: 1-1000, default 100
  "nature_of_suit": ["830"]                    // Optional: Nature of suit codes
}
```

**Response:**
```json
{
  "success": true,
  "total_results": 150,
  "documents_processed": 100,
  "search_criteria": {...},
  "processing_time": "0:00:01.234567",
  "results": [
    {
      "case_number": "22-2042",
      "case_name": "K-Fee System Gmbh v. Nespresso USA, Inc.",
      "document_type": "opinion",
      "content": "",  // May be empty if only PDF available
      "metadata": {
        "cl_id": "9455121",
        "court_id": "cafc",
        "court_name": "Court of Appeals for the Federal Circuit",
        "date_filed": "2023-12-26",
        "docket_number": "22-2042",
        "download_url": "https://cafc.uscourts.gov/opinions-orders/22-2042.pdf",
        "pdf_available": true,
        "requires_pdf_extraction": true
      }
    }
  ]
}
```

### 2. RECAP Docket Retrieval (Specific Dockets)

#### `POST /recap/docket`

Retrieve a specific docket by number, checking RECAP first, then PACER if needed.

**Request Body:**
```json
{
  "docket_number": "2:2024cv00181",    // Required: Exact docket number
  "court": "txed",                     // Required: Court ID
  "include_documents": true,           // Optional: Download PDFs
  "max_documents": 10,                 // Optional: Limit PDFs
  "date_start": "2024-01-01",         // Optional: Entry date range
  "date_end": "2024-12-31",           // Optional: Entry date range
  "force_purchase": false              // Optional: Skip RECAP, go to PACER
}
```

**Response:**
```json
{
  "success": true,
  "docket_number": "2:2024cv00181",
  "court": "txed",
  "case_name": "Example v. Corporation",
  "docket_id": 12345,
  "in_recap": false,
  "purchased_from_pacer": true,
  "purchase_cost": 3.00,
  "documents_downloaded": 5,
  "webhook_registered": true,
  "request_id": 67890,
  "status_url": "/recap/status/67890"
}
```

#### `GET /recap/status/{request_id}`

Check status of PACER purchase request.

**Response:**
```json
{
  "request_id": 67890,
  "status": "success",
  "completed": true,
  "docket_id": 12345,
  "documents_processed": 5
}
```

#### `POST /recap/webhook`

Webhook endpoint for CourtListener RECAP fetch completions (internal use).

### 3. Processing Pipeline

#### `POST /process/batch`

Process a batch of documents from CourtListener through the 11-stage pipeline.

**Request Body:**
```json
{
  "court_id": "cafc",              // Optional: Filter by court
  "date_filed_after": "2024-01-01", // Optional: Date filter
  "max_documents": 100             // Optional: 1-1000, default 100
}
```

#### `POST /process/single`

Process a single CourtListener document.

**Request Body:**
```json
{
  "cl_document": {...}  // Required: CourtListener document object
}
```

#### `GET /pipeline/status`

Get current pipeline status and metrics.

### 4. Documentation

#### `GET /docs/flows`

Get documentation about the two data flows.

## Court IDs

Common IP-focused courts:
- `cafc` - Court of Appeals for the Federal Circuit
- `ded` - District of Delaware  
- `txed` - Eastern District of Texas
- `cand` - Northern District of California
- `nysd` - Southern District of New York

## Nature of Suit Codes

IP-related codes:
- `820` - Copyright
- `830` - Patent
- `835` - Patent - Abbreviated New Drug Application
- `840` - Trademark

## Docker Deployment

### Current Setup
The unified API runs automatically inside the court-processor container on port 8090.

### Accessing the API

1. **From inside Docker network**:
```bash
# From another container
curl http://court-processor:8090/
```

2. **From host (requires port mapping)**:
Add to docker-compose.yml:
```yaml
court-processor:
  # ... existing config ...
  ports:
    - "8090:8090"
```

3. **Through NGINX proxy** (recommended for production)

### Testing the API
```bash
# Check health
docker exec aletheia-court-processor-1 python -c "import requests; print(requests.get('http://localhost:8090/').json())"

# View logs
docker logs aletheia-court-processor-1 --tail 50
```

## Pipeline Integration

Documents returned by either API can be processed through the 11-stage pipeline:

```bash
# Process stored documents
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py

# With PDF extraction
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py --extract-pdfs

# Process only new documents
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py --unprocessed
```

The pipeline will:
1. Retrieve documents from database
2. Extract PDFs if needed
3. Resolve courts (100% success)
4. Extract citations (avg 37 per opinion)
5. Validate citations
6. Normalize reporters
7. Enhance judge information (10-70% success)
8. Analyze document structure
9. Extract keywords
10. Store enhanced metadata
11. Index in Haystack for search

## Key Differences

| Feature | Opinion Search | RECAP Docket |
|---------|---------------|--------------|
| Search Type | Broad keywords, topics | Exact docket number |
| Data Source | CourtListener opinions | RECAP Archive / PACER |
| Cost | Free | Free if in RECAP, else $0.10/page |
| Coverage | Complete for published opinions | Spotty - only what users bought |
| Use Case | Legal research, precedents | Specific case documents |

## Environment Variables

Required in `.env`:
```bash
COURTLISTENER_API_KEY=your_token_here
PACER_USERNAME=your_username        # For RECAP/PACER
PACER_PASSWORD=your_password        # For RECAP/PACER
```

## Testing

### Test Opinion Search
```bash
# From inside container
docker exec aletheia-court-processor-1 python -c "
import requests
response = requests.post('http://localhost:8090/search/opinions', json={
    'court_ids': ['cafc'],
    'date_filed_after': '2023-01-01',
    'max_results': 5
})
print(response.json())
"
```

### Test RECAP Docket
```bash
# From inside container  
docker exec aletheia-court-processor-1 python -c "
import requests
response = requests.post('http://localhost:8090/recap/docket', json={
    'docket_number': '2:2024cv00181',
    'court': 'txed',
    'include_documents': False
})
print(response.json())
"
```

## Error Handling

Common errors:
- `404` - Docket not found in RECAP
- `401` - Invalid API credentials
- `402` - PACER account has insufficient funds
- `500` - Server error (check logs)

## Rate Limits

- CourtListener: 5,000 requests/day with API key
- PACER: No hard limit but costs money

## Future Enhancements

1. Add bulk docket retrieval
2. Implement webhook status persistence
3. Add cost estimation endpoint
4. Create admin dashboard for monitoring
5. Add support for bankruptcy courts