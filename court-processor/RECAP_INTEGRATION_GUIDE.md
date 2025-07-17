# RECAP Integration Guide

## ⚠️ Important: API Access Requirements

**As of July 2025, RECAP document access requires special permissions from CourtListener.**

This guide describes the full capabilities of the RECAP integration, but most features require RECAP API permissions. With basic API access, you can only use the Search API to find documents mentioning transcripts.

To request RECAP access:
1. Contact Free Law Project via their [contact form](https://www.courtlistener.com/contact/)
2. Explain your research/use case
3. Reference your existing API token

## Overview

Our RECAP integration (when permissions are granted) provides comprehensive access to federal court documents through CourtListener's API, with special focus on:
- Intellectual Property (IP) cases
- Court transcripts and proceedings
- Bulk document processing
- Efficient pagination strategies

## Architecture

```
CourtListener RECAP API
         ↓
   RECAPProcessor
         ↓
 Document Enhancement
    ├── FLP Tools (citations, judges)
    ├── Unstructured.io (parsing)
    └── Legal Enhancer (transcripts)
         ↓
    PostgreSQL
```

## What Works with Basic Access

With a basic API token (no RECAP permissions), you can:

### Search API
```bash
# Search for transcript references
python3 courtlistener_integration/search_transcripts.py
```
- Search 8.4M+ documents
- Find opinions quoting transcripts
- Filter by court, date, keywords
- Get metadata and snippets

### Courts API
- Access information about 3,352 jurisdictions
- Get court metadata and identifiers

## Full Features (Requires RECAP Permissions)

### 1. Full RECAP Support
- **Opinions API**: Traditional CourtListener opinions
- **Dockets API**: Complete docket sheets with entries
- **Documents API**: Individual document metadata
- **Search API**: Full-text search across RECAP

### 2. IP Case Specialization
```python
# Automatically identifies and processes IP cases
- Patent (Nature of Suit: 830, 835)
- Trademark (840)
- Copyright (820)
- Key venues: EDTX, DDEL, NDCA, CAFC
```

### 3. Transcript Detection & Enhancement
- Automatic transcript identification
- Speaker extraction
- Objection/ruling tracking
- Examination phase detection

### 4. Efficient Bulk Processing
- Cursor pagination for large datasets
- Rate limit management
- Deduplication across sources

## API Endpoints

### Base URL: `http://localhost:8091`

### 1. Process Specific Docket
```bash
POST /recap/process-docket
{
  "docket_id": 12345,
  "include_documents": true
}

# Returns processed docket with all documents
```

### 2. Search and Process
```bash
POST /recap/search-and-process
{
  "query": "patent infringement Apple",
  "court_ids": ["txed", "deld"],
  "max_results": 100
}
```

### 3. Bulk IP Cases
```bash
POST /recap/ip-cases-batch
{
  "start_date": "2024-01-01",
  "courts": ["txed", "deld", "cand"],
  "transcripts_only": false
}
```

### 4. Recent Transcripts
```bash
GET /recap/recent-transcripts?days_back=30&courts=txed,cafc
```

### 5. Get Court Lists
```bash
GET /recap/courts
# Returns IP-focused court lists

GET /recap/nature-of-suit
# Returns IP-related case type codes
```

## Usage Examples

### Example 1: Process Recent Patent Cases
```python
import requests

# Get patent cases from Eastern District of Texas
response = requests.post('http://localhost:8091/recap/ip-cases-batch', json={
    'start_date': '2024-01-01',
    'courts': ['txed'],
    'nature_of_suit': ['830']  # Patent cases only
})

result = response.json()
print(f"Processed {result['stats']['dockets_processed']} patent dockets")
print(f"Found {result['recap_summary']['transcripts_found']} transcripts")
```

### Example 2: Search for Specific Technology
```python
# Search for AI patent cases
response = requests.post('http://localhost:8091/recap/search-and-process', json={
    'query': '"artificial intelligence" OR "machine learning" AND patent',
    'court_ids': ['txed', 'deld', 'cand'],
    'max_results': 50
})

results = response.json()
for doc in results['processed_documents']:
    print(f"{doc['case_name']} - {doc['court']}")
```

### Example 3: Find and Process Transcripts
```python
# Get recent oral argument transcripts
response = requests.get('http://localhost:8091/recap/recent-transcripts', params={
    'days_back': 30,
    'courts': 'cafc'  # Federal Circuit
})

transcripts = response.json()['transcripts']
for transcript in transcripts:
    # Process individual transcript
    docket_response = requests.post('http://localhost:8091/recap/process-docket', json={
        'docket_id': transcript['docket_id']
    })
```

## Data Coverage & Limitations

### What's Available
- ✅ **Metadata**: Complete for all federal cases
- ✅ **Free Documents**: Previously purchased and uploaded to RECAP
- ✅ **Docket Sheets**: Full docket entry listings
- ✅ **Search**: Full-text search of available documents

### What's Limited
- ❌ **Sealed Documents**: Never available
- ❌ **Recent Filings**: May have delay (depends on user uploads)
- ❌ **Complete PDFs**: Only if someone previously purchased
- ❌ **State Courts**: Federal courts only

### Coverage by Court
Best coverage in high-volume IP courts:
1. **EDTX** (E.D. Texas): ~80% document availability
2. **DDEL** (D. Delaware): ~75% availability
3. **NDCA** (N.D. California): ~70% availability
4. **CAFC** (Fed. Circuit): ~85% availability

## SQL Queries for RECAP Data

### Find Processed Transcripts
```sql
-- Get all processed transcripts with speaker data
SELECT 
  o.case_name,
  o.court_id,
  o.date_filed,
  COUNT(DISTINCT elem->'legal_metadata'->>'speaker') as speaker_count,
  COUNT(CASE WHEN elem->'legal_metadata'->>'event' = 'objection' THEN 1 END) as objection_count
FROM court_data.opinions_unified o,
  jsonb_array_elements(o.structured_elements->'structured_elements') elem
WHERE o.type = 'transcript'
  AND o.source = 'recap'
GROUP BY o.id, o.case_name, o.court_id, o.date_filed;
```

### Analyze IP Case Distribution
```sql
-- IP cases by court and type
SELECT 
  court_id,
  nature_of_suit,
  COUNT(*) as case_count,
  COUNT(DISTINCT docket_number) as unique_dockets
FROM court_data.opinions_unified
WHERE source = 'recap'
  AND nature_of_suit IN ('820', '830', '835', '840')
GROUP BY court_id, nature_of_suit
ORDER BY case_count DESC;
```

### Track Document Availability
```sql
-- RECAP document availability stats
SELECT 
  court_id,
  COUNT(*) as total_documents,
  COUNT(CASE WHEN is_available THEN 1 END) as available_docs,
  ROUND(100.0 * COUNT(CASE WHEN is_available THEN 1 END) / COUNT(*), 2) as availability_pct
FROM court_data.opinions_unified
WHERE source = 'recap'
GROUP BY court_id
ORDER BY total_documents DESC;
```

## Performance Optimization

### 1. Cursor Pagination
```python
# For large result sets (>10,000 documents)
params = {
    'court__in': 'txed,deld',
    'nature_of_suit': '830',
    'page_size': 100
}

while True:
    response = requests.get(url, params=params)
    data = response.json()
    
    # Process results
    process_documents(data['results'])
    
    # Continue with cursor
    if not data.get('next'):
        break
    params['cursor'] = extract_cursor(data['next'])
```

### 2. Batch Processing Strategy
- Process dockets in batches of 50-100
- Use async requests for document fetching
- Cache metadata locally
- Check document availability before downloading

### 3. Rate Limit Management
- Authenticated: 5,000 requests/hour
- Monitor `X-RateLimit-Remaining` header
- Implement exponential backoff
- Use bulk data for initial seeding

## Troubleshooting

### Common Issues

1. **Missing Documents**
   - Check `is_available` flag
   - Document may not be uploaded to RECAP
   - Try searching for alternate versions

2. **Rate Limiting**
   - Reduce concurrent requests
   - Add delays between batches
   - Use cursor pagination

3. **Transcript Detection**
   - Check document description
   - Look for "hearing", "argument", "proceedings"
   - May need manual classification

### Debug Queries

```python
# Check RECAP stats
response = requests.get('http://localhost:8091/recap/stats')
print(response.json())

# Test specific docket
response = requests.post('http://localhost:8091/recap/process-docket', json={
    'docket_id': 12345,
    'include_documents': False  # Metadata only
})
```

## Integration with Existing Pipeline

The RECAP processor extends our unified pipeline:

1. **Fetch from RECAP** → Get docket and document data
2. **Detect Document Type** → Identify transcripts, orders, briefs
3. **Apply Legal Enhancement** → Extract speakers, rulings, sections
4. **FLP Processing** → Add citations and judge info
5. **Unstructured.io** → Parse document structure
6. **Store in PostgreSQL** → With RECAP-specific metadata

## Future Enhancements

1. **Real-time Monitoring**
   - Webhook for new filings
   - RSS feed integration
   - Daily change detection

2. **Enhanced Transcript Analysis**
   - Speaking time analytics
   - Objection success rates
   - Judge intervention patterns

3. **Bulk Export**
   - Generate datasets by criteria
   - Export to research formats
   - Citation network analysis

4. **PACER Integration**
   - Direct PACER fetching for missing docs
   - Cost estimation
   - Automated purchasing workflow