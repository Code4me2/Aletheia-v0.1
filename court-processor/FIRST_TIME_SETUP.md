# Court Processor - First Time Setup Guide

## What is This?

The court-processor is an 11-stage document processing pipeline for US court documents, optimized for intellectual property cases. It fetches documents from CourtListener, enhances them with metadata, and indexes them for search.

## Quick Start

```bash
# Run the pipeline (from parent directory)
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py 10

# Check API health
curl http://localhost:8090/
```

## Key Files

### Core Pipeline
- **`eleven_stage_pipeline_robust_complete.py`** - The MAIN pipeline implementation
- `court_processor_orchestrator.py` - Workflow orchestration
- `pdf_processor.py` - PDF text extraction and OCR

### API
- `api/unified_api.py` - REST API on port 8090
- Endpoints: `/search/opinions`, `/recap/docket`, `/process/batch`

### Configuration
- Environment variables in parent `.env`
- Docker paths use `/app`
- Service configuration in `services/service_config.py`

## Directory Structure

```
court-processor/
├── api/              # API implementation
├── services/         # Service modules (database, CourtListener, etc.)
├── scripts/          # Executable scripts
│   ├── run_pipeline.py     # Main runner
│   └── utilities/          # Helper scripts
├── tests/            # Test files
├── data/             # Output data (gitignored)
└── docs/             # Historical documentation
```

## Common Confusions

1. **Which pipeline file?** → Use `eleven_stage_pipeline_robust_complete.py`
2. **Import errors?** → You're probably not in Docker. Use: `docker exec aletheia-court-processor-1 python ...`
3. **Where's the data?** → PostgreSQL + Elasticsearch (via Haystack)
4. **API not working?** → Check if container is running: `docker ps | grep court-processor`

## Data Flow

1. CourtListener API → PostgreSQL (`court_documents`)
2. Pipeline Enhancement → PostgreSQL (`court_data.opinions_unified`)
3. Haystack Integration → Elasticsearch (`legal-documents-rag` index)

## Dependencies

- PostgreSQL (database)
- Elasticsearch (search)
- Haystack (RAG service)
- Various Python packages (see requirements.txt)

## Testing

```bash
# Test complete flow
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py 5 --extract-pdfs

# Test API
curl -X POST http://localhost:8090/search/opinions \
  -H "Content-Type: application/json" \
  -d '{"court_ids": ["ded"], "max_results": 5}'
```

## Troubleshooting

- **Haystack errors**: Check if Elasticsearch is running: `docker ps | grep elasticsearch`
- **Import errors**: Make sure you're running inside Docker container
- **No data**: Check if CourtListener API token is set in `.env`

## Note on Code Organization

This codebase evolved rapidly and contains some experimental files. The core functionality is solid, but you may encounter:
- Multiple versions of similar functionality
- Mixed import patterns
- Test files that were recently moved to `tests/`

When in doubt, refer to `README.md` and `eleven_stage_pipeline_robust_complete.py`.