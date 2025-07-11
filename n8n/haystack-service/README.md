# Haystack Service

This directory contains the Elasticsearch-based document processing service for the Data Compose project, providing advanced search and retrieval capabilities for legal documents from multiple sources including CourtListener.

## Current Implementation

**Active Service**: `haystack_service.py`

This implementation provides all necessary features using direct Elasticsearch client for better performance and reliability. It supports hierarchical document structures, semantic search, and seamless integration with CourtListener data.

## Files

- `haystack_service.py` - Main API service
- `haystack_service_full.py.bak` - Alternative implementation with full Haystack library (archived)
- `elasticsearch_setup.py` - Creates and configures the Elasticsearch index
- `test_integration.py` - Integration tests for the service
- `requirements-minimal.txt` - Python dependencies for the simple implementation
- `requirements.txt` - Full dependencies (includes problematic elasticsearch-haystack)
- `requirements-setup.txt` - Dependencies just for index setup
- `Dockerfile` - Container configuration

## Features

1. **Document Ingestion**
   - Batch processing
   - Automatic embedding generation
   - Hierarchy tracking (parent-child relationships)

2. **Search Capabilities**
   - BM25 (keyword) search
   - Vector (semantic) search
   - Hybrid search (combines both)

3. **Document Hierarchy**
   - Track document relationships
   - Support for recursive summarization workflows
   - Maintain provenance from summaries to sources

## API Endpoints

### Implemented Endpoints ✅
- `GET /health` - Service health check
- `POST /ingest` - Ingest documents with metadata and hierarchy
- `POST /search` - Multi-modal search (BM25/Vector/Hybrid)
- `POST /hierarchy` - Get document relationships
- `POST /import_from_node` - Import documents from n8n workflows
- `GET /get_final_summary/{workflow_id}` - Retrieve workflow's final summary
- `GET /get_complete_tree/{workflow_id}` - Get full hierarchical tree
- `GET /get_document_with_context/{document_id}` - Get document with navigation context
- `GET /docs` - Interactive API documentation

### Not Implemented ❌
- `POST /batch_hierarchy` - Batch hierarchy operations (defined in n8n node but missing from service)

## Quick Start

```bash
# Build and run with Docker Compose (from project root)
docker-compose -f docker-compose.yml -f n8n/docker-compose.haystack.yml up -d

# Check service health
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs
```

## Testing

```bash
# Run integration tests (requires requests library)
python3 test_integration.py

# Or use curl for manual testing
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '[{"content": "Test document", "metadata": {"source": "test.pdf"}, "document_type": "source_document", "hierarchy_level": 0}]'
```

## Technical Details

- **Embedding Model**: BAAI/bge-small-en-v1.5 (384 dimensions)
- **Elasticsearch Index**: `judicial_documents`
- **Vector Similarity**: Cosine similarity with HNSW index
- **BM25 Analyzer**: Custom English analyzer for legal documents

## Why Two Implementations?

The current implementation (`haystack_service.py`) uses direct Elasticsearch client for:
   - Better performance and control
   - Fewer dependencies
   - More reliable operation
   - All required features

An alternative implementation using the full Haystack 2.x library is archived as `haystack_service_full.py.bak` but is not recommended due to dependency complexity.

The simple implementation provides all needed functionality without the complexity and dependency issues of the full Haystack library.

## Integration with CourtListener

The Haystack service seamlessly integrates with CourtListener data through the following pipeline:

1. **Data Import**: CourtListener opinions are loaded from PostgreSQL using `ingest_to_haystack.py`
2. **Metadata Enrichment**: Court metadata (case name, docket number, judge, etc.) is preserved
3. **Vector Indexing**: Documents are embedded and indexed for semantic search
4. **Hybrid Search**: Supports filtering by court, date, patent status, and other metadata

### Example: Ingesting CourtListener Data

```python
# From court-processor/courtlistener_integration/ingest_to_haystack.py
python ingest_to_haystack.py --limit 100

# The script will:
# 1. Query PostgreSQL for unindexed CourtListener opinions
# 2. Format documents with full metadata
# 3. Send to Haystack /ingest endpoint
# 4. Mark documents as indexed in PostgreSQL
```

### Search Examples

```bash
# Search for patent cases in Delaware
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "patent infringement",
    "filters": {
      "metadata.court": "ded",
      "metadata.is_patent_case": true
    },
    "use_hybrid": true
  }'

# Find opinions by specific judge
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "summary judgment",
    "filters": {
      "metadata.assigned_to": "Judge Smith"
    }
  }'
```

## n8n Integration

The service is fully integrated with n8n through a custom node (`n8n-nodes-haystack`) that provides:
- Document import from workflows
- Search operations with filtering
- Hierarchy navigation
- Tree visualization support

See the [n8n Custom Nodes documentation](../CLAUDE.md) for details on using the Haystack node in workflows.