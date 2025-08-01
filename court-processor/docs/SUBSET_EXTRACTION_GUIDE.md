# Data Subset Extraction Guide

## Overview
This guide covers the best practices for extracting specific subsets of legal data from CourtListener through the complete pipeline to Haystack/PostgreSQL ingestion.

## 1. API-Level Filtering (Most Efficient)

### A. Court-Based Filtering
```python
# Single court
params = {
    'court': 'txed',  # Eastern District of Texas
    'filed_after': '2020-01-01'
}

# Multiple courts (IP-heavy districts)
IP_COURTS = ['txed', 'deld', 'cand', 'nysd', 'ilnd', 'cafc']
for court in IP_COURTS:
    params = {'court': court}
```

### B. Judge-Based Filtering
```python
# Specific judge
params = {
    'q': 'judge:gilstrap',
    'court': 'txed',
    'filed_after': '2020-01-01'
}
```

### C. Case Type Filtering (Nature of Suit)
```python
# IP-specific cases
IP_NOS_CODES = {
    '820': 'Copyright',
    '830': 'Patent', 
    '835': 'Patent-ANDA',
    '840': 'Trademark'
}

params = {
    'q': ' OR '.join([f'nos_code:{code}' for code in IP_NOS_CODES.keys()]),
    'filed_after': '2020-01-01'
}
```

### D. Date Range Filtering
```python
params = {
    'filed_after': '2023-01-01',
    'filed_before': '2023-12-31',
    'court': 'txed'
}
```

### E. Combined Filtering
```python
# Patent cases from Judge Gilstrap in 2023
params = {
    'q': 'judge:gilstrap AND nos_code:830',
    'court': 'txed',
    'filed_after': '2023-01-01',
    'filed_before': '2023-12-31'
}
```

## 2. Bulk Extraction Patterns

### A. Using Enhanced CourtListenerService
```python
from services.courtlistener_service import CourtListenerService

async def extract_ip_subset():
    service = CourtListenerService()
    
    # Method 1: Get all IP cases from specific courts
    ip_cases = await service.get_ip_cases_bulk(
        courts=['txed', 'deld'],
        start_date='2023-01-01',
        limit=1000
    )
    
    # Method 2: Judge-specific extraction
    gilstrap_cases = await service.search_cases(
        query='judge:gilstrap',
        court='txed',
        filed_after='2023-01-01'
    )
```

### B. Streaming Large Datasets
```python
async def stream_large_subset():
    service = CourtListenerService()
    
    async for batch in service.stream_cases(
        court='txed',
        filed_after='2020-01-01',
        batch_size=100
    ):
        # Process batch through pipeline
        await process_batch_through_pipeline(batch)
```

## 3. Pipeline-Level Filtering

### A. Pre-Enhancement Filtering
```python
def filter_before_enhancement(documents):
    """Filter documents before expensive enhancement operations"""
    return [
        doc for doc in documents
        if doc.get('metadata', {}).get('nos_code') in IP_NOS_CODES
        and len(doc.get('content', '')) > 5000  # Substantial opinions only
    ]
```

### B. Post-Enhancement Filtering
```python
def filter_after_enhancement(enhanced_docs):
    """Filter based on enhancement results"""
    return [
        doc for doc in enhanced_docs
        if doc.get('citations_extracted', {}).get('count', 0) > 10  # Citation-rich
        and doc.get('judge_enhancement', {}).get('enhanced', False)  # Known judge
    ]
```

## 4. Database Query Patterns

### A. JSONB Queries for Subset Retrieval
```sql
-- Get all patent cases from specific judges
SELECT * FROM court_data.opinions_unified
WHERE court_info->>'court_id' = 'txed'
AND judge_info->>'full_name' ILIKE '%gilstrap%'
AND citations->>'count'::int > 20;

-- Get cases with specific legal concepts
SELECT * FROM court_data.opinions_unified
WHERE structured_elements->'legal_analysis'->'concepts' @> '["patent infringement"]';
```

### B. Indexed Queries for Performance
```sql
-- Create indexes for common queries
CREATE INDEX idx_court_id ON court_data.opinions_unified((court_info->>'court_id'));
CREATE INDEX idx_judge_name ON court_data.opinions_unified((judge_info->>'full_name'));
CREATE INDEX idx_citation_count ON court_data.opinions_unified(((citations->>'count')::int));
```

## 5. Complete Pipeline Example

```python
async def extract_patent_litigation_subset():
    """Extract patent litigation cases from top districts"""
    
    # 1. Define subset parameters
    PATENT_COURTS = ['txed', 'deld', 'cand', 'nysd', 'ilnd']
    START_DATE = '2022-01-01'
    
    # 2. Initialize services
    cl_service = CourtListenerService()
    pipeline = OptimizedElevenStagePipeline()
    
    # 3. Extract from each court
    for court in PATENT_COURTS:
        print(f"Processing {court}...")
        
        # 4. Fetch patent cases
        cases = await cl_service.search_cases(
            query='nos_code:830',  # Patent cases
            court=court,
            filed_after=START_DATE,
            order_by='-date_filed'
        )
        
        # 5. Filter for substantial opinions
        filtered_cases = [
            case for case in cases
            if len(case.get('plain_text', '')) > 5000
        ]
        
        # 6. Process through enhancement pipeline
        if filtered_cases:
            results = await pipeline.process_batch(
                documents=filtered_cases,
                source='courtlistener'
            )
            
            print(f"Processed {results['documents_processed']} from {court}")
```

## 6. Optimization Strategies

### A. Chunking Strategy
```python
# Process in optimal chunks to balance memory and API limits
OPTIMAL_CHUNK_SIZE = 50  # Based on document size

async def process_large_subset(total_documents):
    for i in range(0, total_documents, OPTIMAL_CHUNK_SIZE):
        chunk = await fetch_chunk(offset=i, limit=OPTIMAL_CHUNK_SIZE)
        await process_chunk(chunk)
```

### B. Parallel Processing
```python
import asyncio

async def parallel_court_extraction(courts):
    """Extract from multiple courts in parallel"""
    tasks = [
        extract_court_subset(court) 
        for court in courts
    ]
    results = await asyncio.gather(*tasks)
    return results
```

### C. Checkpoint/Resume Pattern
```python
def save_checkpoint(last_processed_id):
    with open('extraction_checkpoint.json', 'w') as f:
        json.dump({'last_id': last_processed_id}, f)

def load_checkpoint():
    try:
        with open('extraction_checkpoint.json', 'r') as f:
            return json.load(f).get('last_id')
    except FileNotFoundError:
        return None
```

## 7. Monitoring and Validation

### A. Extraction Metrics
```python
class ExtractionMetrics:
    def __init__(self):
        self.courts_processed = {}
        self.total_documents = 0
        self.enhancement_success_rate = 0
        self.api_calls = 0
        self.rate_limit_hits = 0
    
    def log_metrics(self):
        print(f"Total documents: {self.total_documents}")
        print(f"Success rate: {self.enhancement_success_rate:.2%}")
        print(f"API efficiency: {self.total_documents / max(1, self.api_calls):.2f} docs/call")
```

### B. Quality Validation
```python
def validate_subset_quality(documents):
    """Ensure subset meets quality criteria"""
    return all([
        len(doc.get('content', '')) > 1000,
        doc.get('court_id') is not None,
        doc.get('date_filed') is not None
    ])
```

## Best Practices

1. **Always filter at the API level first** - This reduces data transfer and processing overhead
2. **Use indexed fields** for database queries (court_id, date_filed, judge names)
3. **Implement checkpointing** for large extractions to handle interruptions
4. **Monitor rate limits** and implement exponential backoff
5. **Validate data quality** before expensive enhancement operations
6. **Use streaming** for large result sets to avoid memory issues
7. **Batch similar operations** to maximize efficiency

## Common Subset Patterns

1. **Recent High-Impact Cases**: Filed within last 30 days with > 50 docket entries
2. **Circuit-Specific**: All cases from Federal Circuit courts
3. **Judge Collections**: All cases from specific judges known for certain case types
4. **Time-Bounded**: Specific year or quarter for trend analysis
5. **Citation-Rich**: Opinions with > 20 citations for precedent analysis
6. **Multi-Party**: Cases with > 5 parties for complex litigation analysis

This approach ensures efficient, scalable extraction of specific legal data subsets while maintaining data quality and system performance.