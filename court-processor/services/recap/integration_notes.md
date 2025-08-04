# RECAP Fetch API Integration Notes

## Key Improvements for Pipeline

### 1. Document Acquisition Flow (Current vs Improved)

**Current Flow:**
1. Search for documents
2. Try to download PDFs directly (often fails)
3. Extract text if available

**Improved Flow with RECAP Fetch:**
1. Search for documents
2. Check if already in RECAP (free)
3. If not available:
   - Submit RECAP Fetch request with PACER credentials
   - Monitor request status
   - Download once purchased
4. Extract text from purchased document

### 2. Cost Management

```python
# Add to orchestrator configuration
'recap': {
    'pacer_username': os.getenv('PACER_USERNAME'),
    'pacer_password': os.getenv('PACER_PASSWORD'),
    'monthly_budget': 500.00,  # $500/month limit
    'check_existing': True,     # Always check RECAP first
    'purchase_pdfs': True,      # Purchase individual PDFs
    'purchase_dockets': True    # Purchase full dockets
}
```

### 3. Integration Points

#### In `document_ingestion_service.py`:
```python
# Add RECAP Fetch support
from services.recap.recap_fetch_client import RECAPFetchClient

async def _fetch_document_with_recap(self, document_id, court):
    """Fetch document using RECAP Fetch API if needed."""
    
    # First check if already available
    if await self._is_in_recap(document_id):
        return await self._download_from_recap(document_id)
    
    # Purchase using PACER credentials
    async with RECAPFetchClient(
        self.cl_token,
        self.pacer_username,
        self.pacer_password
    ) as client:
        result = await client.fetch_pdf(document_id)
        # Monitor and download...
```

#### In `courtlistener_service.py`:
```python
# Add method to check RECAP availability
async def is_document_in_recap(self, recap_doc_id):
    """Check if document is already in RECAP."""
    url = f"{self.BASE_URL}/recap-documents/{recap_doc_id}/"
    # Check if accessible...
```

### 4. Environment Variables Needed

Add to `.env`:
```
# PACER Credentials
PACER_USERNAME=your_pacer_username
PACER_PASSWORD=your_pacer_password

# Cost limits
PACER_MONTHLY_BUDGET=500.00
PACER_DAILY_LIMIT=50.00
```

### 5. Benefits

1. **Reliability**: No more failed PDF downloads
2. **Coverage**: Access to ALL PACER documents
3. **Cost Control**: Track spending, set limits
4. **Public Good**: All purchases added to free RECAP archive
5. **Text Extraction**: Automatic OCR on all PDFs

### 6. Implementation Priority

1. **Phase 1**: Add RECAP Fetch for PDFs that fail to download
2. **Phase 2**: Add docket purchasing for comprehensive data
3. **Phase 3**: Add attachment page support
4. **Phase 4**: Implement cost optimization strategies

### 7. Testing Strategy

```python
# Test with small dataset first
test_config = {
    'court_ids': ['txed'],
    'max_per_court': 5,
    'recap': {
        'purchase_pdfs': True,
        'max_cost_per_run': 15.00  # Max $15 for testing
    }
}
```

## Directory Cleanup Benefits

The reorganized structure provides:
- Clear separation of core vs auxiliary code
- Archived old implementations for reference
- Dedicated space for RECAP integration
- Clean root directory with only essential files
- Better documentation organization

Run `./reorganize_directory.sh` to clean up the directory structure.