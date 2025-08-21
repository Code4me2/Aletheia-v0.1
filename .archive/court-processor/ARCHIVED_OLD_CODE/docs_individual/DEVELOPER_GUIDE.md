# Court Processor - Developer Guide

## Quick Overview

This is a court document processing pipeline that:
1. Fetches US court documents from CourtListener API
2. Enhances them with metadata (court info, citations, judges)
3. Stores them in PostgreSQL and indexes in Elasticsearch

## Key Files You Need to Know

### Core Implementation
- **`eleven_stage_pipeline_robust_complete.py`** - The main pipeline (11 stages)
- **`court_processor_orchestrator.py`** - Manages pipeline runs and history
- **`pdf_processor.py`** - Extracts text from PDFs using OCR

### API
- **`api/unified_api.py`** - REST API on port 8090
  - `/search/opinions` - Search court opinions
  - `/recap/docket` - Get RECAP docket info
  - `/process/batch` - Trigger pipeline processing

### Services
- **`services/courtlistener_service.py`** - Fetches documents from CourtListener
- **`services/document_ingestion_service.py`** - Stores documents in PostgreSQL
- **`services/service_config.py`** - Docker service URLs (no localhost!)

## How to Run

Everything runs in Docker. From the parent directory:

```bash
# Run the pipeline
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py 10

# Test the API
curl http://localhost:8090/

# Check logs
docker logs aletheia-court-processor-1
```

## Important Notes

1. **Docker Only**: All services use Docker networking. No localhost configurations.
2. **One Pipeline**: Use `eleven_stage_pipeline_robust_complete.py` - ignore files in `archive/`
3. **Database**: PostgreSQL with two schemas:
   - `public.court_documents` - Raw documents from CourtListener
   - `court_data.opinions_unified` - Enhanced documents after pipeline
4. **Search**: Documents are indexed in Elasticsearch via Haystack service

## Common Tasks

### Process New Documents
```bash
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py 50 --unprocessed
```

### Force Reprocess Everything
```bash
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py --force
```

### Extract PDFs
```bash
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py 20 --extract-pdfs
```

## Troubleshooting

- **Import errors**: Make sure you're running inside Docker container
- **Service connection errors**: Check if all containers are running: `docker ps`
- **No data**: Verify CourtListener API token is set in parent `.env`

## Testing

Run tests inside the container:
```bash
docker exec aletheia-court-processor-1 python -m pytest tests/
```

## Architecture

```
CourtListener API
      ↓
PostgreSQL (court_documents)
      ↓
11-Stage Pipeline
      ↓
PostgreSQL (opinions_unified)
      ↓
Elasticsearch (via Haystack)
```

For more details, see:
- [README.md](./README.md) - Full documentation
- [FIRST_TIME_SETUP.md](./FIRST_TIME_SETUP.md) - Quick start guide
- [PIPELINE_CAPABILITIES.md](./PIPELINE_CAPABILITIES.md) - What the pipeline can do