# RECAP Integration Status

## Current State (As of 2025-07-25)

### ✅ Completed Components

1. **PACER Authentication** (`services/recap/authenticated_client.py`)
   - Direct PACER login via uscourts.gov API
   - Token management and logout
   - Pre-authentication before RECAP operations

2. **RECAP Fetch Client** (`services/recap/recap_fetch_client.py`)
   - Full implementation of CourtListener RECAP Fetch API
   - Methods for dockets, PDFs, and attachment pages
   - Cost tracking and status monitoring
   - Check availability before purchase

3. **PDF Handler** (`services/recap/recap_pdf_handler.py`)
   - Docket verification with retry logic
   - PDF download from CourtListener
   - Handles docket ID mismatch issue
   - Organized file storage by date

4. **Webhook Infrastructure**
   - Flask webhook server (`api/webhook_server.py`)
   - Webhook handler (`services/recap/webhook_handler.py`)
   - Request registration and tracking
   - Idempotency handling

5. **Docker Integration**
   - PACER credentials in docker-compose
   - Webhook service configuration
   - Volume mounts for PDF storage

### ❌ Missing Integration

1. **Document Ingestion Service Gap**
   ```python
   # In document_ingestion_service.py
   async def _fetch_and_process_recap(self, documents: List[Dict]) -> List[Dict]:
       """Process RECAP search results and fetch full content if needed"""
       # TODO: Implement RECAP document processing
       return []
   ```

2. **Orchestrator Integration**
   - PACER config exists but not used
   - No webhook URL configuration
   - No async request handling

3. **Database Tracking**
   - No table for pending RECAP requests
   - No webhook delivery tracking
   - No cost accounting

## Architecture Decision

Moving from direct PACER scraping to RECAP Fetch + Webhooks:

### Current Flow (Not Implemented):
```
Direct PACER Login → Scrape → Download → Process
```

### Target Flow (To Implement):
```
1. Search FREE RECAP first
2. If not found → RECAP Fetch API → Webhook → Download → Process
```

## Implementation Plan

### Phase 1: Complete Document Ingestion Integration
- Implement `_fetch_and_process_recap` method
- Use free-first approach
- Submit RECAP requests for missing documents
- Register requests with webhook handler

### Phase 2: Add Database Tracking
- Create `recap_fetch_requests` table
- Track request status and costs
- Handle webhook deliveries

### Phase 3: Update Orchestrator
- Use webhook URL from config
- Handle async document flow
- Report on pending vs completed

## Cost Implications

- FREE: Existing RECAP documents (14+ million)
- PAID: New PACER purchases ($0.10/page, max $3/doc)
- Current config: Max $50 per run

## Testing Status

- ✅ PACER authentication works
- ✅ RECAP Fetch API works
- ❌ Docket ID mismatch issue (workaround exists)
- ❌ Full pipeline integration not tested
- ❌ Webhook delivery not tested with real CourtListener

## Implementation Complete

### ✅ Free-First Logic Implemented

The `_fetch_and_process_recap` method now:
1. Searches FREE RECAP archive first
2. Only attempts PACER purchase if:
   - Document not found in free archive
   - PACER credentials provided
   - Cost limit not exceeded
   - `use_recap_fallback=True`

### Test Results

- FREE search works (no PACER auth attempted)
- PACER fallback activates only when enabled
- Authentication successful when credentials provided
- Webhook infrastructure ready but purchase logic not complete

### Known Issues

1. RECAP search returns 400 error (parameter format issue)
2. Database connection fails outside Docker
3. Purchase logic placeholder - needs specific docket targeting

## Next Steps

1. Fix RECAP search parameters
2. Implement specific docket purchase logic
3. Configure webhook URL in CourtListener account
4. Test with known missing documents
5. Add database tracking for async requests