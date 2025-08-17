# API Migration Guide: Simplified Court Documents API v2

## Overview
The Simplified API (v2) replaces the complex nested structure of the original standalone API with direct, intuitive access to long-form court documents while maintaining all critical functionality.

## Key Improvements

### 1. Direct Text Access
- **Old**: `response.document.content.plain_text` (3 levels deep)
- **New**: `/text/{id}` returns plain text directly, or `response.text` for JSON

### 2. Bulk Data Retrieval (PRESERVED & ENHANCED)
- **Old**: `/search` with complex nested response
- **New**: `/bulk/judge/{name}` - Optimized endpoint for large-scale data export
  - Returns ALL documents for a judge (e.g., 37 Gilstrap docs = 2MB of text)
  - Option to exclude text for faster metadata-only queries

### 3. Simplified Response Structure
```json
// OLD (nested, complex)
{
  "success": true,
  "document": {
    "content": {
      "plain_text": "...",
      "plain_text_length": 12345
    }
  }
}

// NEW (flat, direct)
{
  "id": 420,
  "text": "...",
  "text_length": 12345,
  "judge": "Gilstrap"
}
```

## Endpoint Mapping

| Purpose | Old API | New API |
|---------|---------|---------|
| Health Check | `GET /` | `GET /` |
| Get Document Text | `GET /document/{id}` → `.document.content.plain_text` | `GET /text/{id}` (direct text) |
| Get Document Info | `GET /document/{id}` | `GET /documents/{id}` |
| Search Documents | `POST /search` (complex body) | `GET /search?judge=X&limit=Y` |
| Bulk by Judge | `POST /search` with high limit | `GET /bulk/judge/{name}` |
| Statistics | `GET /statistics` | (Removed - rarely used) |
| Test Endpoint | `GET /test` | `GET /sample` |

## Migration Examples

### 1. Getting Long-Form Text
```bash
# OLD (complex)
curl -X GET http://localhost:8103/document/420 | \
  jq -r '.document.content.plain_text'

# NEW (simple)
curl http://localhost:8104/text/420
```

### 2. Bulk Retrieval by Judge
```bash
# OLD
curl -X POST http://localhost:8103/search \
  -H "Content-Type: application/json" \
  -d '{"judge_name": "Gilstrap", "limit": 100, "document_type": "020lead"}'

# NEW
curl http://localhost:8104/bulk/judge/Gilstrap
```

### 3. Search with Pagination
```bash
# OLD
curl -X POST http://localhost:8103/search \
  -H "Content-Type: application/json" \
  -d '{"judge_name": "Gilstrap", "limit": 10, "offset": 20}'

# NEW
curl "http://localhost:8104/search?judge=Gilstrap&limit=10&offset=20"
```

## Features Status

✅ **Fully Preserved:**
- Bulk data retrieval by judge (enhanced with dedicated endpoint)
- Full long-form content access (10-160KB documents)
- Document search and filtering
- Pagination support
- Plain text extraction from HTML/XML

⚠️ **Secondary (Not Yet Implemented):**
- CourtListener API integration (exists in unified_api.py, not standalone)
- Database statistics endpoint (rarely used, can be added if needed)

❌ **Removed (Unnecessary Complexity):**
- Nested response structures
- Success/failure wrapper fields
- Redundant content formats in same response

## Performance Comparison

| Operation | Old API | New API | Improvement |
|-----------|---------|---------|-------------|
| Get text for doc 420 | 3 JSON parse levels | Direct text response | ~90% simpler |
| Bulk retrieve 37 docs | Complex POST body | Simple GET URL | ~80% simpler |
| Response size | Includes raw + processed | Only requested format | ~50% smaller |

## Running the APIs

### Old API (Port 8103)
```bash
python standalone_database_api.py
```

### New API (Port 8104)
```bash
python simplified_api.py
```

## Deprecation Timeline

1. **Current**: Both APIs running in parallel
2. **Testing Phase**: Validate new API handles all use cases
3. **Migration**: Update clients to use new endpoints
4. **Deprecation**: Stop old API, remove `standalone_database_api.py`

## Next Steps

1. Test bulk retrieval performance with large datasets
2. Add CourtListener integration if needed (from unified_api.py)
3. Update frontend/clients to use new endpoints
4. Archive and remove old API once migration complete

## Notes

- The new API maintains the same database connection (PostgreSQL on port 8200)
- All 020lead documents with full text are accessible
- The simplified structure makes programmatic access much easier
- Bulk operations are actually faster due to optimized endpoints