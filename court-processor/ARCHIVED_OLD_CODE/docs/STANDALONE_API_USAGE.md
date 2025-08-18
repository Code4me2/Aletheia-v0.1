# Standalone Database API for Full-Text Court Opinions

## Overview

The standalone API provides direct access to the court documents database, returning **COMPLETE, UNTRUNCATED** opinion text (typically 10-40KB per document) with all metadata.

## Key Features

- **Full Content**: Returns complete legal opinions, not truncated or summarized
- **Direct Database Access**: Queries PostgreSQL directly on port 8200
- **No External Dependencies**: Doesn't rely on court-processor container
- **Simple Deployment**: Single Python script that runs independently

## Running the API

```bash
# Start the API on port 8103
cd court-processor
python standalone_database_api.py

# Or run in background
python standalone_database_api.py > api.log 2>&1 &
```

## API Endpoints

### 1. Health Check
```bash
curl http://localhost:8103/
```

### 2. Test Endpoint (Sample Gilstrap Opinion)
```bash
curl http://localhost:8103/test
```

Returns one full Gilstrap opinion to verify the system is working.

### 3. Search Documents
```bash
curl -X POST http://localhost:8103/search \
  -H "Content-Type: application/json" \
  -d '{
    "document_type": "020lead",
    "judge_name": "Gilstrap",
    "min_content_length": 10000,
    "limit": 10
  }'
```

**Parameters:**
- `document_type`: "020lead" (full opinions), "opinion", "opinion_doctor", or "all"
- `judge_name`: Partial match on judge name
- `court_id`: Court identifier (e.g., "txed")
- `min_content_length`: Filter out documents below this size (default: 5000)
- `limit`: Maximum documents to return (1-100, default: 10)
- `offset`: For pagination
- `include_plain_text`: Extract plain text from HTML/XML (default: true)

### 4. Get Single Document
```bash
curl http://localhost:8103/document/420
```

Returns a single document by ID with full content.

### 5. Database Statistics
```bash
curl http://localhost:8103/statistics
```

Returns statistics about document types, judges, and content lengths.

## Example: Retrieving Full Legal Opinions

```python
import requests

# Search for Gilstrap opinions
response = requests.post('http://localhost:8103/search', json={
    'document_type': '020lead',
    'judge_name': 'Gilstrap',
    'min_content_length': 10000,
    'limit': 5
})

data = response.json()
for doc in data['documents']:
    print(f"Case: {doc['case_number']}")
    print(f"Content length: {doc['content']['plain_text_length']:,} characters")
    
    # Access full text
    full_text = doc['content']['plain_text']
    print(f"First 500 chars: {full_text[:500]}")
```

## Document Types

- **020lead**: Full court opinions with complete text (10-40KB average)
  - Source: CourtListener standalone processor
  - Best for: Legal research, full text analysis
  
- **opinion**: Standard opinions (variable completeness)
  
- **opinion_doctor**: Pipeline-processed opinions with metadata

## Port Configuration

The API uses the centralized port system:
- **Default Port**: 8103 (in the 8100-8199 application services range)
- **Database Port**: 8200 (PostgreSQL exposed port)

Environment variables:
```bash
export COURT_DB_API_PORT=8103  # API port
export DB_PORT=8200            # Database port
export DB_HOST=localhost       # Database host
export DB_NAME=aletheia        # Database name
export DB_USER=aletheia        # Database user
export DB_PASSWORD=aletheia123 # Database password
```

## Content Verification

The API returns both raw HTML/XML and extracted plain text:

```json
{
  "content": {
    "raw": "<opinion>...</opinion>",     // Full HTML/XML
    "length": 42180,                     // Raw content length
    "plain_text": "RODNEY GILSTRAP...",  // Full extracted text
    "plain_text_length": 31137           // Plain text length
  }
}
```

## Current Database Statistics

As of testing:
- **Total 020lead documents**: 39
- **Average content length**: 30-40KB
- **Judges with most documents**: Gilstrap (37), Albright (2)
- **All documents contain full opinion text**

## Advantages Over Unified API

1. **Actually Works**: Returns full content, not empty fields
2. **Simple**: Single file, no complex dependencies
3. **Direct Access**: Queries database directly
4. **Exposed Port**: Accessible from outside Docker network
5. **Fast**: No intermediate processing layers

## Integration with Frontend

The API can be easily integrated with any frontend:

```javascript
// JavaScript example
async function getGilstrapOpinions() {
    const response = await fetch('http://localhost:8103/search', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            document_type: '020lead',
            judge_name: 'Gilstrap',
            limit: 10
        })
    });
    
    const data = await response.json();
    // Each document has full content in data.documents[i].content.plain_text
    return data.documents;
}
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8103
lsof -i :8103

# Kill existing process
kill <PID>
```

### Database Connection Issues
- Ensure PostgreSQL is running on port 8200
- Check credentials in environment variables
- Verify Docker container `aletheia_development-db-1` is healthy

### No Results
- Check that 020lead documents exist in database
- Verify judge name spelling (case-insensitive partial match)
- Lower or remove `min_content_length` filter