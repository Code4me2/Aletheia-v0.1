# API Unification Analysis & Issues

## Current State: Two Parallel Systems

### 1. CLI System (WORKS - Gets Full Content)
- **Service**: `UnifiedCollectionService` 
- **Processor**: `EnhancedStandaloneProcessor`
- **Method**: Uses CourtListener Search API (`/api/rest/v4/search/`)
- **Content**: Successfully retrieves 020lead documents with 15-40KB full opinions
- **Database**: Stores complete documents with source: `courtlistener_standalone`

### 2. API System (BROKEN - Returns Empty Content)
- **Service**: `DocumentIngestionService`
- **Endpoint**: `/search/opinions` on port 8090
- **Method**: Uses CourtListener Opinion API (`/api/rest/v4/opinions/`)
- **Content**: Returns empty content (0 bytes)
- **Problem**: Follows Opinion→Cluster→Docket chain which loses content

## Key Issues Identified

### Issue #1: Different Data Sources
```python
# CLI uses Search API (WORKS)
url = "https://www.courtlistener.com/api/rest/v4/search/"
params = {'q': 'judge:gilstrap', 'type': 'o'}
# Returns: Full text content in results

# API uses Opinion API (BROKEN)
url = "https://www.courtlistener.com/api/rest/v4/opinions/"
# Returns: Metadata only, no content
```

### Issue #2: Service Mismatch
- **unified_api.py** imports `DocumentIngestionService` (broken approach)
- **court_processor CLI** uses `UnifiedCollectionService` (working approach)
- These services are NOT unified - they use completely different methods

### Issue #3: Database Schema Confusion
- **020lead documents**: Created by standalone processor, contain full content
- **opinion documents**: Created by ingestion service, often empty
- **opinion_doctor documents**: Pipeline-processed, variable content
- Same data represented differently depending on ingestion path

### Issue #4: API Endpoint Confusion
The `/search/opinions` endpoint promises to search opinions but:
1. Uses the wrong CourtListener API
2. Returns empty content
3. Doesn't access existing 020lead documents in database
4. Creates new empty documents instead of using existing full ones

## Evidence of the Problem

### Working CLI Command:
```bash
docker exec aletheia_development-court-processor-1 python court_processor \
  data export --judge "Gilstrap" --type 020lead --full-content
# Returns: 13,848 character legal opinion with full text
```

### Broken API Call:
```python
requests.post('http://localhost:8090/search/opinions', json={
    'court_ids': ['txed'],
    'query': 'Gilstrap'
})
# Returns: 0 character content field
```

## Root Cause Analysis

The fundamental issue is that we have **two completely different ingestion pipelines** that are not actually unified:

1. **Legacy Pipeline** (DocumentIngestionService)
   - Designed for Opinion API which requires multiple API calls
   - Opinion → Cluster → Docket traversal
   - Often results in empty content
   - Used by the "unified" API

2. **Enhanced Pipeline** (EnhancedStandaloneProcessor)
   - Uses Search API directly
   - Single API call returns full content
   - Creates 020lead documents with complete text
   - Used by CLI but NOT by API

## Proposed Solution

### Immediate Fix: Update Unified API
Replace DocumentIngestionService with UnifiedCollectionService in unified_api.py:

```python
# REMOVE THIS:
from services.document_ingestion_service import DocumentIngestionService

# ADD THIS:
from services.unified_collection_service import UnifiedCollectionService

# UPDATE search_opinions endpoint to use:
async with UnifiedCollectionService() as service:
    results = await service.collect_documents(
        court_id=court_id,
        judge_name=query,  # Map query to judge search
        date_after=date_after,
        date_before=date_before,
        max_documents=max_results
    )
```

### Long-term Fix: True Unification

1. **Single Ingestion Service**: Merge all ingestion logic into one service
2. **Consistent Document Model**: Use same schema regardless of source
3. **Content Priority**: Always prefer Search API for content retrieval
4. **Fallback Chain**: Search API → Opinion API → PDF extraction
5. **Database First**: Check existing 020lead documents before making API calls

## Testing Requirements

After fixing the API:
1. Verify `/search/opinions` returns content >5000 chars
2. Ensure existing 020lead documents are accessible via API
3. Confirm judge attribution works through API
4. Test pagination once implemented

## Performance Implications

- **Current API**: Makes 3+ API calls per document (Opinion→Cluster→Docket)
- **Fixed API**: Makes 1 API call per search (batch results)
- **Expected improvement**: 3-5x faster, 100% content retrieval

## Migration Path

1. Update unified_api.py to use UnifiedCollectionService
2. Test with existing 020lead documents
3. Add database query to check existing documents first
4. Implement proper pagination (current limit: 20)
5. Deprecate DocumentIngestionService or refactor for RECAP-only use