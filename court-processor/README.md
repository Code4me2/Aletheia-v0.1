# Court Processor

Automated court document processing system with REST API and CLI interfaces for judiciary insights.

## Overview

The Court Processor manages legal documents from various courts, providing:
- **REST API** (Port 8104) for document retrieval and search
- **CLI Tool** for data management and analysis
- **485 documents** from federal courts (as of August 2025)
- **11-stage processing pipeline** for document enrichment

## Quick Start

### Using the API

The API runs automatically when the Docker container starts:

```bash
# Check API health
curl http://localhost:8104/

# Get document text
curl http://localhost:8104/text/420

# Search documents
curl "http://localhost:8104/search?judge=Gilstrap&type=020lead&limit=10"

# List recent documents  
curl http://localhost:8104/list
```

### Using the CLI

Run commands inside the Docker container:

```bash
# Check data status
docker exec aletheia_development-court-processor-1 python3 cli.py data status

# Export Judge Gilstrap's opinions
docker exec aletheia_development-court-processor-1 python3 cli.py data export \
  --judge "Gilstrap" \
  --type 020lead \
  --format json

# Analyze a judge
docker exec aletheia_development-court-processor-1 python3 cli.py analyze judge "Rodney Gilstrap"
```

## API Endpoints

| Endpoint | Description | Example |
|----------|-------------|---------|
| `GET /` | Health check | `curl http://localhost:8104/` |
| `GET /text/{id}` | Get plain text | `curl http://localhost:8104/text/420` |
| `GET /documents/{id}` | Get full document | `curl http://localhost:8104/documents/420` |
| `GET /search` | Search with filters | `curl "http://localhost:8104/search?judge=Gilstrap"` |
| `GET /list` | List documents | `curl http://localhost:8104/list?limit=10` |
| `GET /bulk/judge/{name}` | Bulk retrieve by judge | `curl http://localhost:8104/bulk/judge/Gilstrap` |

## CLI Commands

### Data Management
- `data status` - Check data quality metrics
- `data list` - List documents with filters
- `data export` - Export documents in various formats
- `data fix` - Fix data quality issues

### Analysis
- `analyze judge [name]` - Analyze judicial patterns
- `analyze court [id]` - Analyze court trends

### Collection
- `collect court [id]` - Collect documents from a court
- `collect judge [name]` - Collect documents by judge

### Processing
- `pipeline run` - Run document enhancement pipeline

## Database Schema

The service uses a single table: `public.court_documents`

See [ACTIVE_SCHEMA.sql](ACTIVE_SCHEMA.sql) for full schema details.

**Key Fields:**
- `id` - Primary key
- `case_number` - Case identifier
- `document_type` - Type of document (opinion, 020lead, etc.)
- `content` - Full document text (HTML/XML)
- `metadata` - JSON metadata (judge, court, dates, etc.)

**Document Types:**
- `opinion` - Generic court opinion
- `020lead` - Lead opinion (main court opinion)
- `opinion_doctor` - Enhanced/processed opinion
- `docket` - Docket entry

## Current Data Status

As of August 2025:
- **Total Documents**: 485
- **Judge Attribution**: 55.9%
- **Courts Covered**: txed (72), ded (44), mdd (16)
- **Date Range**: 1996-2025

## Configuration

Environment variables (set in parent `.env`):
```bash
DATABASE_URL=postgresql://user:pass@db:5432/aletheia
COURT_PROCESSOR_PORT=8104
COURTLISTENER_API_TOKEN=your-token  # For data collection
```

## Architecture

```
court-processor/
├── api.py                # REST API server
├── cli.py                # Command-line interface
├── processor.py          # Document processing pipeline
├── schema.sql            # Database schema
├── extractors/           # Extraction modules
│   ├── judge.py         # Judge extraction
│   ├── pdf.py           # PDF processing
│   └── document_type.py # Document type detection
├── services/             # External integrations
│   ├── database.py      # Database connections
│   ├── courtlistener.py # CourtListener API
│   └── ingestion.py     # Document ingestion
├── utils/                # Utility functions
│   ├── configuration.py # App configuration
│   ├── validation.py    # Data validation
│   └── reporter.py      # Error reporting
└── archived/             # Legacy/unused code
```

## Docker Integration

The court-processor runs as service `aletheia_development-court-processor-1`:
- Auto-starts API on container launch
- Exposes port 8104
- Connects to PostgreSQL database container
- Logs to `/data/logs/api.log`

## Development

### Running Locally

```bash
# Set environment
export DATABASE_URL="postgresql://aletheia:aletheia123@localhost:8200/aletheia"

# Run API
python api.py

# Run CLI
python cli.py --help
```

### Testing

```bash
# Test API health
curl http://localhost:8104/

# Run CLI command
docker exec aletheia_development-court-processor-1 python3 cli.py data status
```

## Troubleshooting

### API Connection Issues
- Ensure Docker container is running: `./dev status`
- Check logs: `docker logs aletheia_development-court-processor-1`
- Verify port 8104 is accessible

### Database Connection Issues
- Database runs in separate container
- Check database is running: `docker ps | grep db`
- Verify DATABASE_URL environment variable

### CLI Issues
- Must run inside Docker container
- Use `docker exec` prefix for all commands
- Check database connectivity with `data status`

## Additional Documentation

- [docs/ANALYSIS.md](docs/ANALYSIS.md) - Detailed system analysis
- [schema.sql](schema.sql) - Database schema
- [docs/REORGANIZATION.md](docs/REORGANIZATION.md) - Code organization strategy

## Legacy Code

Archived components are preserved in `archived/` directory:
- Database schemas for potential future migration
- RECAP integration services
- Utility scripts for data import/export

These are not currently in use but retained for reference.