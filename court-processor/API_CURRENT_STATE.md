# Court Processor API - Current State

## Active APIs

### 1. Simplified Database API (PRIMARY)
- **File**: `simplified_api.py`
- **Port**: 8104
- **Purpose**: Direct database access for full-text court opinions
- **Status**: ✅ Active and recommended

#### Key Endpoints:
- `GET /text/{id}` - Direct plain text access
- `GET /documents/{id}` - Document with metadata
- `GET /search` - Search with filters
- `GET /bulk/judge/{name}` - Bulk retrieval by judge
- `GET /list` - List available documents

#### Example Usage:
```bash
# Get text directly
curl http://localhost:8104/text/420

# Bulk retrieve all Gilstrap documents
curl http://localhost:8104/bulk/judge/Gilstrap

# Search with pagination
curl "http://localhost:8104/search?judge=Gilstrap&limit=10&offset=20"
```

### 2. RECAP Webhook Server
- **File**: `api/webhook_server.py`
- **Port**: 5000 (via Docker)
- **Purpose**: Handle RECAP webhooks from CourtListener
- **Status**: ✅ Active (used by docker-compose)

## Database Access

- **PostgreSQL Port**: 8200
- **Database**: aletheia
- **Credentials**: See .env file

## CLI Tool

- **File**: `court_processor`
- **Purpose**: Command-line interface for data processing
- **Usage**: `./court_processor [command] [options]`

## Archived APIs

The following APIs have been moved to `ARCHIVED_OLD_CODE/`:
- standalone_database_api.py (replaced by simplified_api.py)
- api/unified_api.py
- api/court_processor_api.py
- api/database_search_endpoint.py
- api/flp_api.py

## Docker Services

Active services in docker-compose.yml:
- `court-processor` - Main processing service
- `recap-webhook` - RECAP webhook handler

## Quick Start

1. **Start the simplified API**:
```bash
python simplified_api.py
```

2. **Start Docker services**:
```bash
docker-compose up -d
```

3. **Access the API**:
- Health check: http://localhost:8104/
- Documentation: http://localhost:8104/docs

## Migration Notes

If migrating from old API (port 8103), see `API_MIGRATION_GUIDE.md`

## Performance

- Handles 37 documents (2MB+ text) efficiently
- Direct text access eliminates JSON parsing overhead
- Optimized bulk retrieval endpoints