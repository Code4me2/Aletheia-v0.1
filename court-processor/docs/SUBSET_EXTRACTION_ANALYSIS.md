# CourtListener API Subset Extraction Methods - Comprehensive Analysis

## Overview
The court-processor pipeline provides multiple levels of data filtering and subset extraction through the CourtListener API integration. This analysis covers all available methods for extracting specific subsets of legal documents.

## 1. API-Level Filtering (Primary Layer)

### 1.1 Court-Based Filtering
The most fundamental filtering occurs at the court level:

```python
# Single court filtering
params = {
    'court': 'txed',  # Eastern District of Texas
}

# Multiple courts
params = {
    'court__in': 'cafc,txed,deld,cand,nysd,ilnd'  # IP-heavy venues
}

# Nested court filtering for opinions
params = {
    'cluster__docket__court': 'scotus',  # Supreme Court opinions
}
```

**Predefined Court Collections:**
- `IP_COURTS['federal_circuit']`: ['cafc', 'uscfc', 'cit']
- `IP_COURTS['district_heavy_ip']`: ['txed', 'deld', 'cand', 'nysd', 'ilnd']
- `IP_COURTS['all_federal_district']`: 'FD' (jurisdiction code)

### 1.2 Date Range Filtering
Temporal filtering with multiple operators:

```python
# Date filed after
params = {
    'date_filed__gte': '2020-01-01',  # Documents filed on or after
}

# Date range
params = {
    'date_filed__range': '2020-01-01,2025-12-31',  # Full range
}

# Combined date filtering
params = {
    'date_filed__gte': '2024-01-01',
    'date_filed__lte': '2024-12-31',
}
```

### 1.3 Nature of Suit Filtering (Case Type)
IP-specific case type filtering:

```python
# IP Nature of Suit codes
IP_NATURE_OF_SUIT = {
    '820': 'Copyright',
    '830': 'Patent',
    '835': 'Patent - Abbreviated New Drug Application',
    '840': 'Trademark'
}

# Filter by nature of suit
params = {
    'nature_of_suit__in': '820,830,840',  # Copyright, Patent, Trademark
}
```

### 1.4 Judge-Specific Filtering
Extract documents by specific judges:

```python
# Search query for specific judge
params = {
    'q': 'judge:gilstrap',  # Judge Gilstrap documents
    'type': 'o',  # Opinion documents
    'court': 'txed'  # Combined with court filter
}
```

### 1.5 Document Type Filtering
Filter by document types:

```python
# Search types
search_types = {
    'o': 'Case law opinions',
    'r': 'RECAP dockets with documents',
    'rd': 'RECAP documents (flat)',
    'd': 'Dockets only',
    'p': 'People/Judges',
    'oa': 'Oral arguments'
}

params = {
    'type': 'r',  # RECAP documents
    'document_type': 'opinion'  # Specific document type
}
```

## 2. Pagination and Batch Control

### 2.1 Page Size Control
```python
params = {
    'page_size': 100,  # Max 100 per page
}
```

### 2.2 Cursor-Based Pagination
The pipeline implements robust cursor-based pagination:

```python
# Extract cursor from next URL
def _extract_cursor_from_url(self, url: str) -> Optional[str]:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    return params.get('cursor', [None])[0]
```

### 2.3 Maximum Result Limits
Control total documents fetched:

```python
async def fetch_opinions(self, 
                        court_id: Optional[str] = None,
                        date_filed_after: Optional[str] = None,
                        max_results: int = 100) -> List[Dict]:
```

## 3. Multi-Stage Filtering Pipeline

### 3.1 Stage-Based Document Selection
The eleven-stage pipeline allows filtering at each processing stage:

1. **Document Retrieval Stage**: Initial database query filtering
2. **Court Resolution Stage**: Validate and enhance court information
3. **Citation Extraction Stage**: Filter documents with specific citation patterns
4. **Judge Enhancement Stage**: Filter by enhanced judge information
5. **Legal Enhancement Stage**: Apply legal concept filters

### 3.2 Database-Level Filtering
PostgreSQL queries with JSONB filtering:

```python
# Filter by judge in metadata
cursor.execute("""
    SELECT * FROM court_documents
    WHERE metadata->>'judge_name' ILIKE %s
    AND metadata->>'court_id' = %s
    AND metadata->>'date_filed' >= %s
""", ('%gilstrap%', 'txed', '2020-01-01'))

# Filter by document characteristics
cursor.execute("""
    SELECT * FROM court_documents
    WHERE 
        content IS NOT NULL
        AND LENGTH(content) > 1000
        AND metadata->>'document_type' = 'opinion'
        AND processed = true
""")
```

### 3.3 Content-Based Filtering
Full-text search capabilities:

```python
# PostgreSQL full-text search
cursor.execute("""
    SELECT * FROM court_documents
    WHERE to_tsvector('english', content) @@ to_tsquery('patent & infringement')
""")

# CourtListener search API
params = {
    'q': 'patent infringement "claim construction"',
    'type': 'o',
    'court': 'cafc'
}
```

## 4. Specialized Subset Extraction Methods

### 4.1 IP Case Extraction
```python
async def fetch_ip_cases_bulk(self,
                            start_date: str,
                            end_date: Optional[str] = None,
                            include_documents: bool = False) -> AsyncIterator[Dict]:
    # Stage 1: Federal Circuit courts
    federal_dockets = await self.fetch_recap_dockets(
        court_ids=self.IP_COURTS['federal_circuit'],
        date_filed_after=start_date,
        max_results=1000
    )
    
    # Stage 2: District courts with IP nature of suit
    district_dockets = await self.fetch_recap_dockets(
        court_ids=self.IP_COURTS['district_heavy_ip'],
        date_filed_after=start_date,
        nature_of_suit=list(self.IP_NATURE_OF_SUIT.keys()),
        max_results=5000
    )
```

### 4.2 Recent Case Extraction
```python
async def get_recent_patent_cases(days_back: int = 30) -> List[Dict]:
    start_date = (date.today() - timedelta(days=days_back)).isoformat()
    
    results = await service.fetch_recap_dockets(
        court_ids=['txed', 'deld', 'cand'],
        date_filed_after=start_date,
        nature_of_suit=['830', '835'],  # Patent cases
        max_results=500
    )
```

### 4.3 Comprehensive Judge-Specific Extraction
The Gilstrap processor demonstrates comprehensive filtering:

```python
# Fetch all Judge Gilstrap documents from 2020-2025
fetch_result = await self.fetch_all_available_gilstrap_documents(
    max_documents=2000  # Large number to ensure date range coverage
)

# With automatic duplicate detection
def is_document_duplicate(self, meta: Dict[str, Any]) -> bool:
    cursor.execute("""
        SELECT id FROM court_documents 
        WHERE case_number = %s AND document_type = %s
    """, (meta.get('case_name'), meta.get('type', 'opinion')))
    return cursor.fetchone() is not None
```

## 5. Advanced Filtering Combinations

### 5.1 Complex Query Construction
```python
# Multi-dimensional filtering
params = {
    'q': 'judge:gilstrap AND ("patent infringement" OR "claim construction")',
    'court__in': 'txed,cafc',
    'date_filed__gte': '2020-01-01',
    'nature_of_suit__in': '830,835',
    'type': 'o',
    'page_size': 100
}
```

### 5.2 Progressive Enhancement Filtering
Documents can be filtered based on enhancement results:

```python
# Filter documents that have been successfully enhanced
enhanced_documents = [
    doc for doc in documents 
    if doc.get('court_enhancement', {}).get('resolved')
    and doc.get('citations_extracted', {}).get('count', 0) > 0
    and doc.get('judge_enhancement', {}).get('enhanced')
]
```

### 5.3 Haystack Integration Filtering
Filter documents suitable for RAG ingestion:

```python
# Prepare documents with minimum content requirements
haystack_suitable = [
    doc for doc in documents
    if len(doc.get('content', '')) > 500  # Minimum content length
    and doc.get('meta', {}).get('court_id')  # Has court information
    and doc.get('meta', {}).get('date_filed')  # Has date information
]
```

## 6. Performance Optimization Strategies

### 6.1 Batch Processing
```python
# Process in batches to manage memory
batch_size = 50
for i in range(0, len(documents), batch_size):
    batch = documents[i:i+batch_size]
    result = await process_batch(batch)
```

### 6.2 Rate Limiting
```python
# Automatic rate limit handling
if self.rate_limit_remaining < 100:
    logger.warning(f"Rate limit low: {self.rate_limit_remaining} remaining")
    await asyncio.sleep(1)
```

### 6.3 Checkpoint-Based Resume
```python
# Save progress for large extractions
paginator.save_checkpoint('extraction_checkpoint.json', page, {
    'total_processed': total_documents,
    'last_court': current_court,
    'last_date': last_processed_date
})

# Resume from checkpoint
resume_page = paginator.resume_from_checkpoint('extraction_checkpoint.json')
```

## 7. Practical Usage Examples

### 7.1 Extract All Patent Cases from Texas in 2024
```python
results = await service.fetch_recap_dockets(
    court_ids=['txed'],
    nature_of_suit=['830', '835'],
    date_filed__gte='2024-01-01',
    date_filed__lte='2024-12-31',
    max_results=1000
)
```

### 7.2 Extract Federal Circuit Appeals with Specific Judges
```python
params = {
    'q': '(judge:moore OR judge:newman) AND "patent eligibility"',
    'court': 'cafc',
    'type': 'o',
    'date_filed__gte': '2023-01-01'
}
```

### 7.3 Extract High-Value IP Litigation
```python
# Combine multiple signals for high-value cases
params = {
    'court__in': 'txed,deld,cand',  # Key venues
    'nature_of_suit': '830',  # Patent
    'q': '"preliminary injunction" OR "permanent injunction" OR "willful infringement"',
    'date_filed__gte': '2022-01-01'
}
```

## Conclusion

The court-processor pipeline provides comprehensive subset extraction capabilities through:

1. **API-level filtering** with court, date, case type, and judge parameters
2. **Multi-stage pipeline filtering** allowing refinement at each processing step
3. **Database-level filtering** using PostgreSQL's powerful JSONB queries
4. **Content-based filtering** through full-text search
5. **Performance optimizations** including pagination, rate limiting, and checkpointing

These methods can be combined to extract highly specific subsets of legal documents for analysis, making the pipeline suitable for targeted legal research and analysis tasks.