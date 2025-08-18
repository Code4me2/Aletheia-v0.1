# Data Retrieval Improvements Documentation

## Current State
The data retrieval system works well for small-scale operations (20 documents) with:
- **100% content extraction rate** (avg 47k chars/document)
- **100% judge attribution rate** via ComprehensiveJudgeExtractor
- **0.8 seconds per document** processing time
- Uses CourtListener Search API effectively

## Critical Improvements Needed

### 1. Pagination Support (CRITICAL)
**File:** `services/enhanced_standalone_processor.py`
**Method:** `search_court_documents()` (line ~95)

**Current Issue:** Hard limit of 20 results per query
**Required Changes:**
```python
# Add to search_court_documents method:
async def search_court_documents(self, ...):
    all_documents = []
    page = 1
    
    while True:
        params = {
            'q': query,
            'type': 'o',
            'page_size': 100,  # Max allowed by API
            'page': page
        }
        
        async with self.session.get(search_url, params=params) as response:
            data = await response.json()
            results = data.get('results', [])
            
            if not results:
                break
                
            all_documents.extend(results)
            
            # Check if more pages exist
            if not data.get('next'):
                break
                
            page += 1
            await asyncio.sleep(0.5)  # Rate limiting
    
    return all_documents[:max_documents]
```

### 2. Parallel Opinion Fetching
**File:** `services/enhanced_standalone_processor.py`
**Method:** `_fetch_opinions_batch()` (new method needed)

**Required Changes:**
```python
async def _fetch_opinions_batch(self, opinion_ids: List[str], batch_size: int = 10):
    """Fetch multiple opinions in parallel with rate limiting."""
    semaphore = asyncio.Semaphore(batch_size)
    
    async def fetch_with_limit(op_id):
        async with semaphore:
            return await self._fetch_opinion_by_id(op_id)
    
    opinions = await asyncio.gather(*[
        fetch_with_limit(op_id) for op_id in opinion_ids
    ])
    
    return [op for op in opinions if op]
```

### 3. Progress Tracking and Resumption
**File:** `services/unified_collection_service.py`
**Method:** `collect_documents()` (line ~50)

**Required Changes:**
```python
# Add progress tracking
async def collect_documents(self, ..., resume_from: Optional[str] = None):
    # Load progress from database
    if resume_from:
        progress = await self._load_progress(resume_from)
        start_index = progress.get('last_processed_index', 0)
    else:
        start_index = 0
        progress_id = str(uuid.uuid4())
    
    # Save progress periodically
    for i, doc in enumerate(documents[start_index:], start=start_index):
        # Process document...
        
        if i % 10 == 0:  # Save every 10 documents
            await self._save_progress(progress_id, {
                'last_processed_index': i,
                'last_document_id': doc['id'],
                'total_documents': len(documents)
            })
```

### 4. Database Schema for Progress
**New File Needed:** `migrations/add_progress_tracking.sql`
```sql
CREATE TABLE IF NOT EXISTS retrieval_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    progress_id VARCHAR(255) UNIQUE NOT NULL,
    last_processed_index INTEGER,
    last_document_id VARCHAR(255),
    total_documents INTEGER,
    status VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_progress_id ON retrieval_progress(progress_id);
```

## Implementation Priority

1. **Pagination** - Enables retrieval beyond 20 documents
2. **Parallel Fetching** - 5-10x performance improvement
3. **Progress Tracking** - Essential for large batches
4. **Error Recovery** - Resume from failures

## Testing Requirements

### Unit Tests Needed
- Test pagination with multiple pages
- Test parallel fetching with rate limits
- Test progress save/resume functionality
- Test error handling and recovery

### Integration Tests Needed
- Test full retrieval of 100+ documents
- Test interruption and resumption
- Test with various court/judge combinations

## Performance Targets

### Current Performance
- 20 documents max
- 0.8 sec/document
- No resumption capability

### Target Performance
- 10,000+ documents capability
- 0.1-0.2 sec/document (with parallel fetching)
- Full resumption from any interruption
- Progress visibility to user

## Dependencies
- asyncio for parallel processing
- PostgreSQL for progress tracking
- Rich library for progress bars (optional)

## Files to Modify
1. `services/enhanced_standalone_processor.py` - Add pagination and parallel fetching
2. `services/unified_collection_service.py` - Add progress tracking
3. `services/database.py` - Add progress table methods
4. `court_processor` CLI - Add resume flag support