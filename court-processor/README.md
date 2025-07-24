# Court Processor Pipeline

An 11-stage document processing pipeline for US court documents, optimized for intellectual property cases. Part of the Aletheia legal data platform.

## 🚀 Quick Start

```bash
# Run inside Docker container
docker exec aletheia-court-processor-1 python run_delaware_opinions.py

# Check results
docker exec aletheia-db-1 psql -U aletheia -d aletheia -c \
  "SELECT COUNT(*) FROM court_documents WHERE document_type='opinion'"
```

## 📊 Current Status

**Production Ready** for opinion processing with 78% completeness and 68% quality scores.

### Performance Summary
- **Court Opinions**: ✅ Excellent (78% completeness)
- **RECAP Dockets**: ⚠️ Limited (19% completeness - metadata only)  
- **Storage**: ✅ 100% reliability
- **API Integration**: ✅ CourtListener working, ❌ PACER credentials issue

See [PIPELINE_CAPABILITIES.md](./PIPELINE_CAPABILITIES.md) for detailed metrics.

## 🎯 Key Features

- **11-Stage Enhancement Pipeline**: Court resolution, citation extraction, judge identification, and more
- **IP Court Focus**: Optimized for patent, trademark, and copyright cases
- **Multiple Data Sources**: CourtListener API, RECAP Archive, local PDFs
- **Async Processing**: Efficient batch processing with comprehensive error handling
- **Quality Metrics**: Honest reporting of processing completeness and quality

## 📁 Project Structure

```
court-processor/
├── court_processor_orchestrator.py      # Main workflow controller
├── eleven_stage_pipeline_robust_complete.py  # 11-stage pipeline
├── services/                            # Service modules
│   ├── courtlistener_service.py        # API client
│   ├── document_ingestion_service.py   # Document fetching
│   └── recap/                          # RECAP integration
├── scripts/                            # Utility scripts
├── docs/                               # Documentation
└── archive/                            # Historical implementations
```

## 🔧 Configuration

Environment variables (in parent `.env`):
```env
COURTLISTENER_API_TOKEN=your-token-here
PACER_USERNAME=your-username  # Optional
PACER_PASSWORD=your-password  # Optional
```

## 💻 Usage Examples

### Ingest Delaware Patent Cases
```python
# See run_delaware_opinions.py
config = {
    'court_ids': ['ded'],
    'document_types': ['opinions'],
    'nature_of_suit': ['830'],  # Patent cases
    'lookback_days': 30
}
```

### Process Existing Documents
```bash
docker exec aletheia-court-processor-1 python eleven_stage_pipeline_robust_complete.py
```

## 📈 Pipeline Stages

1. **Document Retrieval** - Fetch from database
2. **Court Resolution** - Identify and validate courts
3. **Citation Extraction** - Find legal citations
4. **Citation Validation** - Verify citation format
5. **Reporter Normalization** - Standardize citations
6. **Judge Enhancement** - Extract judge information
7. **Document Structure** - Analyze organization
8. **Keyword Extraction** - Find legal terms
9. **Metadata Assembly** - Combine enhancements
10. **Storage** - Save to PostgreSQL
11. **Verification** - Quality metrics

## 🚧 Known Limitations

- **PACER Access**: Direct purchase not working (credential issue)
- **Judge Extraction**: Only 10% success rate  
- **RECAP Dockets**: No text content, only metadata
- **Connection Timeouts**: Long runs may timeout

## 🔄 Recent Updates

- Fixed database connection issues (run in Docker)
- Added court_id field mapping for opinions
- Improved RECAP field handling
- Added comprehensive performance metrics

## 📖 Documentation

- [WORKING_CONFIGURATION.md](./WORKING_CONFIGURATION.md) - Setup and fixes
- [PIPELINE_CAPABILITIES.md](./PIPELINE_CAPABILITIES.md) - Detailed capabilities
- [PACER_INTEGRATION_STATUS.md](./PACER_INTEGRATION_STATUS.md) - API status

## 🤝 Contributing

This is part of the larger Aletheia project. Focus areas for contribution:
- Improve judge name extraction patterns
- Integrate PDF extraction for RECAP documents
- Add more IP-specific extractions (patent numbers, etc.)

## 📝 License

Part of Aletheia-v0.1 - see parent repository for license details.