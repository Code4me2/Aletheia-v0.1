# Haystack Service CLI Guide

## Quick Start

```bash
# From the haystack-service directory
./cli start --standalone    # Start services
./cli load test            # Load test data
./cli search "legal"       # Test search
./cli stop                 # Stop services
```

## Installation

The CLI tool requires Python 3.7+ and the following packages:
```bash
# Install from requirements file
pip install -r cli-requirements.txt

# Or install manually
pip install click requests elasticsearch psycopg2-binary
```

Note: The `elasticsearch` package is only needed for the `console` command and direct Elasticsearch operations.

## CLI Commands

### Service Management

#### Start Services
```bash
# Start with default settings (unified mode)
./cli start

# Start in standalone mode (no PostgreSQL)
./cli start --standalone

# Rebuild and start
./cli start --build
```

#### Stop Services
```bash
./cli stop
```

#### Check Status
```bash
./cli status
```

#### View Logs
```bash
# Last 100 lines
./cli logs

# Follow logs
./cli logs -f

# Last 50 lines
./cli logs -n 50
```

### Data Management

#### Load Data
```bash
# Load test data
./cli load test --limit 100

# Load from PostgreSQL
./cli load postgres --limit 500
./cli load postgres --query "SELECT * FROM court_data.opinions WHERE court_id = 'ca9'"

# Load from JSON file
./cli load file --file datasets/my-docs.json
```

#### Clear Data
```bash
# Clear all documents (will prompt for confirmation)
./cli clear
```

### Search Operations

#### Basic Search
```bash
# Hybrid search (default)
./cli search "constitutional rights"

# Vector search only
./cli search "legal precedent" --type vector

# BM25 search only
./cli search "contract law" --type bm25

# Limit results
./cli search "patent" --limit 10

# With filters
./cli search "patent" --filter court=cafc --filter year=2023
```

### Elasticsearch Operations

#### List Indices
```bash
./cli es indices
```

#### Index Statistics
```bash
./cli es stats
```

#### Raw Query
```bash
# Execute raw Elasticsearch query
./cli es query '{"query": {"match_all": {}}, "size": 1}'

# More complex query
./cli es query '{
  "query": {
    "bool": {
      "must": [
        {"match": {"content": "patent"}},
        {"term": {"metadata.court": "cafc"}}
      ]
    }
  }
}'
```

### Development Tools

#### Interactive Console
```bash
# Start Python console with pre-loaded clients
./cli console

# In console:
>>> results = search("legal precedent")
>>> es.indices.get_alias()
>>> doc = get_doc("doc-id-123")
```

#### Quick Test
```bash
# Run basic functionality test
./cli test
```

## Environment Variables

Configure the CLI behavior with environment variables:

```bash
# PostgreSQL connection (for data loading)
export POSTGRES_HOST=localhost
export POSTGRES_DB=n8n
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=password

# Service configuration
export HAYSTACK_MODE=standalone  # or "unified"
export ELASTICSEARCH_INDEX=legal-documents-rag
```

## Examples

### Complete Development Workflow
```bash
# 1. Start services in standalone mode
./cli start --standalone

# 2. Check everything is healthy
./cli status

# 3. Load test data
./cli load test --limit 100

# 4. Test different search types
./cli search "contract breach" --type bm25
./cli search "legal implications" --type vector
./cli search "constitutional rights" --type hybrid

# 5. Check index statistics
./cli es stats

# 6. Interactive exploration
./cli console

# 7. Clean up
./cli clear
./cli stop
```

### Loading Real Data from PostgreSQL
```bash
# Start services
./cli start

# Load specific court opinions
./cli load postgres --query "
  SELECT id, plain_text, court_id, case_name, date_filed 
  FROM court_data.opinions 
  WHERE court_id IN ('scotus', 'ca9', 'ca2')
  AND date_filed > '2020-01-01'
  LIMIT 1000
"

# Search the loaded data
./cli search "first amendment" --filter court=scotus
```

### Debugging Search Quality
```bash
# Start console for detailed analysis
./cli console

>>> # Compare search strategies
>>> hybrid = search("patent infringement", "hybrid")
>>> vector = search("patent infringement", "vector") 
>>> bm25 = search("patent infringement", "bm25")
>>> 
>>> # Analyze scores
>>> for r in hybrid['results'][:3]:
...     print(f"Score: {r['score']:.3f}, Content: {r['content'][:50]}...")
```

## Troubleshooting

### Service Won't Start
```bash
# Check if ports are in use
lsof -i :8000  # Haystack API
lsof -i :9200  # Elasticsearch

# Check Docker status
docker ps -a | grep -E "haystack|elasticsearch"

# Force restart
./cli stop
docker-compose -f ../docker-compose.haystack.yml down
./cli start
```

### Search Returns No Results
```bash
# Check if documents are indexed
./cli es stats

# Verify document structure
./cli es query '{"query": {"match_all": {}}, "size": 1}'

# Test with simple query
./cli search "*"
```

### Connection Errors
```bash
# Verify services are running
./cli status

# Check Docker network
docker network ls
docker network inspect data_compose_backend
```

## API Endpoints

The CLI interacts with these Haystack API endpoints:

- `GET /health` - Service health check
- `POST /ingest` - Document ingestion
- `POST /search` - Document search
- `GET /get_document_with_context/{id}` - Get specific document

For direct API usage, see the [Haystack README](README.md).

## Next Steps

- Explore the [interactive console](#interactive-console) for advanced usage
- Check [datasets/](datasets/) for example data files
- Read the [API implementation](haystack_service_rag.py) for deeper understanding