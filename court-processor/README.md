# Court Processor Pipeline

An 11-stage document processing pipeline for US court documents, optimized for intellectual property cases. Part of the Aletheia legal data platform.

## 🚀 Quick Start

```bash
# Run pipeline with default settings (10 documents)
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py

# Process 50 documents with PDF extraction
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py 50 --extract-pdfs

# Process only unprocessed documents
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py 20 --unprocessed

# Force reprocess all documents
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py --force
```

## 📊 Current Status

**Production Ready** with recent improvements to citation extraction, judge identification, and PDF integration.

### Performance Summary
- **Court Opinions**: ✅ Excellent (78% completeness)
- **RECAP Dockets**: ✅ Fixed (100% court resolution)
- **Citation Extraction**: ✅ Fixed (now shows total count)
- **Judge Identification**: ✅ Improved (removed photo dependency)
- **PDF Extraction**: ✅ NEW - Integrated and working
- **Storage**: ✅ 100% reliability

### Recent Fixes (July 2025)
- ✅ Fixed citation extraction rate display (was showing 5400%)
- ✅ Fixed judge extraction (removed judge-pics dependency)
- ✅ Fixed RECAP court resolution (now uses court_id field)
- ✅ Added force reprocessing option
- ✅ Added unprocessed-only filtering
- ✅ Integrated PDF content extraction

See [PIPELINE_CAPABILITIES.md](./PIPELINE_CAPABILITIES.md) for detailed metrics.

## 🎯 Key Features

- **Dual API System**: Separate endpoints for opinion search (broad) and RECAP dockets (specific)
- **11-Stage Enhancement Pipeline**: Court resolution, citation extraction, judge identification, and more
- **PDF Content Extraction**: Automatic extraction from PDFs when text is missing
- **IP Court Focus**: Optimized for patent, trademark, and copyright cases
- **Multiple Data Sources**: CourtListener API, RECAP Archive, PDF documents
- **Async Processing**: Efficient batch processing with comprehensive error handling
- **Quality Metrics**: Real-time reporting of processing completeness and quality

## 🌐 API Endpoints

The court processor provides a unified RESTful API running on port 8090:

### Opinion Search API
- `POST /search/opinions` - Broad search for published opinions
- Free access to complete CourtListener database
- Supports keyword search, date ranges, court filters

### RECAP Docket API  
- `POST /recap/docket` - Retrieve specific dockets by number
- Checks free RECAP archive first, then PACER if needed
- Supports document downloads and webhook notifications

### Processing Pipeline API
- `POST /process/batch` - Process documents through 11-stage pipeline
- `POST /process/single` - Process individual documents
- `GET /pipeline/status` - Check pipeline status and metrics

See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for complete API reference.

## 📁 Project Structure

```
court-processor/
├── api/
│   ├── unified_api.py                       # Main API server (port 8090)
│   └── webhook_server.py                    # RECAP webhook handler
├── eleven_stage_pipeline_robust_complete.py # Main 11-stage pipeline
├── court_processor_orchestrator.py          # Workflow orchestration
├── scripts/
│   ├── run_pipeline.py                      # Main runner script
│   └── utilities/                           # Helper scripts
├── services/                                # Service modules
│   ├── courtlistener_service.py            # API client
│   ├── document_ingestion_service.py       # Document fetching
│   ├── unified_document_processor.py       # Unified processing
│   ├── recap_docket_service.py             # RECAP docket handling
│   └── recap/                              # RECAP integration
├── integrate_pdf_to_pipeline.py            # PDF extraction module
├── pdf_processor.py                        # PDF processing utilities
├── docs/                                   # Archived documentation
└── archive/                                # Historical implementations
```

## 🔧 Configuration

Environment variables (in parent `.env`):
```env
COURTLISTENER_API_TOKEN=your-token-here
PACER_USERNAME=your-username  # Optional - see PACER_INTEGRATION_STATUS.md
PACER_PASSWORD=your-password  # Optional - see PACER_INTEGRATION_STATUS.md
```

## 💻 Usage Examples

### Basic Pipeline Run
```bash
# Process 10 documents (default)
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py

# Process 50 documents
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py 50
```

### Advanced Options
```bash
# Extract PDFs when content is missing
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py 20 --extract-pdfs

# Only process new documents
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py --unprocessed

# Force reprocess (ignore hash checks)
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py --force

# Combine options
docker exec aletheia-court-processor-1 python scripts/run_pipeline.py 100 --extract-pdfs --unprocessed
```

## 📈 Pipeline Stages

1. **Document Retrieval** - Fetch from database + optional PDF extraction
2. **Court Resolution** - Identify and validate courts
3. **Citation Extraction** - Find legal citations using eyecite
4. **Citation Validation** - Verify citation format
5. **Reporter Normalization** - Standardize citations
6. **Judge Enhancement** - Extract judge information
7. **Document Structure** - Analyze organization
8. **Keyword Extraction** - Find legal terms
9. **Metadata Assembly** - Combine enhancements
10. **Storage** - Save to PostgreSQL
11. **Verification** - Quality metrics

## 🚧 Known Limitations

- **PACER Direct Access**: Credential issue (but RECAP has 14M+ documents)
- **Judge Extraction**: Limited success rate (patterns need improvement)
- **RECAP Dockets**: Metadata only (no document text)

## 🔄 Recent Updates (July 2025)

- **Unified API**: Consolidated all endpoints into single API service on port 8090
- **Separated Data Flows**: Clear distinction between opinion search (broad) and RECAP dockets (specific)
- **PDF Integration**: Automatic content extraction from court PDFs
- **Fixed Citation Display**: Shows total count instead of incorrect percentage
- **Fixed Judge Extraction**: Removed photo database dependency
- **Fixed RECAP Processing**: Now properly resolves courts for dockets
- **Added Processing Options**: Force reprocess and unprocessed-only flags
- **Improved Error Handling**: Better validation and error reporting

## 📖 Documentation

### Current Documentation
- [PIPELINE_CAPABILITIES.md](./PIPELINE_CAPABILITIES.md) - Detailed capabilities and metrics
- [PACER_INTEGRATION_STATUS.md](./PACER_INTEGRATION_STATUS.md) - PACER/RECAP API status
- [RECAP_VS_OPINIONS.md](./RECAP_VS_OPINIONS.md) - Document type differences

### Archived Documentation
All historical documentation has been moved to the `docs/` directory for reference.

## 🤝 Contributing

This is part of the larger Aletheia project. Focus areas for contribution:
- Improve judge name extraction patterns
- Add patent/trademark number extraction
- Enhance document structure analysis
- Add more IP-specific metadata extraction

## 📝 License

Part of Aletheia-v0.1 - see parent repository for license details.