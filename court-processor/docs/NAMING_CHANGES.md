# Naming Standardization Plan

## Proposed Changes

### Main Files (Root Level)
- `simplified_api.py` → `api.py` (it's THE api, not a simplified version)
- `court_processor` → `cli.py` (standard Python CLI naming)
- `pipeline.py` → `processor.py` (clearer purpose)
- `pipeline_exceptions.py` → `exceptions.py` (standard naming)
- `pipeline_validators.py` → `validators.py` (remove redundant prefix)
- `judge_extractor.py` → `extractors/judge.py` (group extractors)
- `pdf_processor.py` → `extractors/pdf.py` (group extractors)
- `document_type_detector.py` → `extractors/document_type.py`
- `error_reporter.py` → `utils/reporter.py` (utility function)

### Documentation
- `ACTIVE_SCHEMA.sql` → `schema.sql` (it's THE schema)
- `CONSOLIDATED_DOCS.md` → `docs/ANALYSIS.md`
- `REORGANIZATION_PLAN.md` → `docs/REORGANIZATION.md`

### Services Directory
- `courtlistener_service.py` → `courtlistener.py` (remove redundant suffix)
- `document_ingestion_service.py` → `ingestion.py` (clearer, shorter)
- `service_config.py` → `config.py` (remove redundant prefix)

### Reorganize Structure
```
court-processor/
├── README.md
├── schema.sql              # Database schema
├── requirements.txt
├── Dockerfile
├── entrypoint.sh
│
├── api.py                  # REST API server
├── cli.py                  # Command-line interface
├── processor.py            # Document processing pipeline
├── exceptions.py           # Custom exceptions
├── validators.py           # Validation logic
│
├── extractors/             # Extraction modules
│   ├── __init__.py
│   ├── judge.py           # Judge extraction
│   ├── pdf.py             # PDF processing
│   └── document_type.py   # Document type detection
│
├── services/              # External service integrations
│   ├── __init__.py
│   ├── database.py       # Database connection
│   ├── courtlistener.py  # CourtListener API
│   ├── ingestion.py      # Document ingestion
│   └── config.py         # Service configuration
│
├── utils/                 # Utility functions
│   ├── __init__.py
│   ├── configuration.py  # App configuration
│   ├── validation.py     # Data validation
│   └── reporter.py       # Error reporting
│
├── config/               # Configuration files
│   └── courts.yaml      # Court definitions
│
├── tests/               # Test suite
│   └── ...
│
├── docs/                # Documentation
│   ├── ANALYSIS.md     # System analysis
│   ├── REORGANIZATION.md
│   └── API.md          # API documentation
│
└── archived/           # Legacy code
```

## Benefits of These Changes

1. **Clarity**: `api.py` is clearer than `simplified_api.py`
2. **Standards**: `cli.py` follows Python conventions
3. **Organization**: Extractors grouped together
4. **Simplicity**: Removed redundant words like "service", "pipeline"
5. **Hierarchy**: Clear separation of concerns

## Implementation Order

1. Create new directories (extractors/, docs/)
2. Move and rename files
3. Update imports in all files
4. Update Dockerfile and entrypoint.sh
5. Update documentation
6. Test everything works