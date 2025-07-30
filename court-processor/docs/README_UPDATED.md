# Court Processor with Free Law Project Integration

A robust, production-ready court document processing pipeline that leverages Free Law Project tools to provide comprehensive legal document analysis, with integrated PDF extraction and eleven-stage enhancement pipeline.

## 🚀 Key Features

### Core Capabilities
- **Eleven-Stage Processing Pipeline**: Comprehensive document enhancement and validation
- **Automatic PDF Extraction**: Downloads and extracts text from PDFs when needed
- **200+ Court Support**: Full US court coverage via CourtListener API integration
- **Free Law Project Tools Integration**:
  - **Courts-DB**: Court identification and standardization (700+ variations)
  - **Eyecite**: Legal citation extraction and validation
  - **Reporters-DB**: Reporter abbreviation normalization
  - **Judge-pics**: Judge portrait retrieval
  - **Doctor**: Advanced PDF text extraction (Docker service)
  - **X-Ray**: Bad redaction detection
- **REST API**: FastAPI endpoints for all FLP functionality
- **PostgreSQL Integration**: Enhanced schema with JSONB metadata
- **Haystack Integration**: Document indexing for RAG applications
- **Comprehensive Testing**: Modular test suite with unit, integration, and E2E tests

## 📊 Current Status (July 2025)

- **Pipeline Completeness**: 95%+ (from initial 50%)
- **PDF Integration**: ✅ Fully functional
- **Test Coverage**: ✅ Comprehensive
- **Production Ready**: 80% (needs deployment configuration)
- **Performance**: Processes 50 documents in ~22 seconds

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Document Ingestion Service                     │
│  • CourtListener API integration                            │
│  • Automatic PDF download and extraction                    │
│  • Stores complete documents in PostgreSQL                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│           Eleven-Stage Processing Pipeline                    │
│  1. Document Retrieval      7. Keyword Extraction          │
│  2. Court Resolution        8. Metadata Assembly            │
│  3. Citation Extraction     9. Database Storage             │
│  4. Reporter Normalization  10. Haystack Indexing          │
│  5. Judge Enhancement       11. Pipeline Verification       │
│  6. Structure Analysis                                      │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL (or Docker)
- CourtListener API key (optional for testing)

### Installation

```bash
# Clone the repository
git clone [repository-url]
cd court-processor

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export COURTLISTENER_API_KEY='your-api-key'  # Optional
export DATABASE_URL='postgresql://user:pass@localhost/dbname'
```

### Basic Usage

#### 1. Complete Workflow (Recommended)
```python
from court_processor_orchestrator import CourtProcessorOrchestrator

# Run complete workflow: ingest → process → report
orchestrator = CourtProcessorOrchestrator()
results = await orchestrator.run_complete_workflow()
```

#### 2. Document Ingestion Only
```python
from services.document_ingestion_service import DocumentIngestionService

async with DocumentIngestionService() as service:
    # Ingest from CourtListener with automatic PDF extraction
    results = await service.ingest_from_courtlistener(
        court_ids=['txed', 'cafc', 'nysd'],
        date_after='2024-01-01',
        document_types=['opinions', 'recap']
    )
```

#### 3. Pipeline Processing Only
```python
from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline

pipeline = RobustElevenStagePipeline()
results = await pipeline.process_batch(
    limit=100,
    extract_pdfs=True  # Enable automatic PDF extraction
)
```

### Docker Deployment

```bash
# Using docker-compose with all services
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

# With Doctor service for enhanced PDF processing
docker-compose -f docker-compose.yml -f n8n/docker-compose.doctor.yml up -d
```

## 📁 Key Components

### Core Pipeline Files
- `eleven_stage_pipeline_robust_complete.py` - Main pipeline implementation
- `court_processor_orchestrator.py` - Workflow orchestration
- `services/document_ingestion_service.py` - Document acquisition and PDF extraction

### PDF Processing
- `pdf_processor.py` - PyMuPDF-based text extraction with OCR fallback
- `courtlistener_pdf_pipeline.py` - CourtListener PDF integration
- `integrate_pdf_to_pipeline.py` - Modular PDF extraction service

### FLP Integration
- `services/flp_integration.py` - Comprehensive FLP tools wrapper
- `enhanced_flp_pipeline.py` - Enhanced field mapping for different document types
- `flp_api.py` - FastAPI endpoints for all FLP tools

### Testing
- `tests/comprehensive_test_suite.py` - Modular test framework
- `test_suite.py` - Unified test runner with scoring

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python tests/comprehensive_test_suite.py

# Run with real API/DB
TEST_REAL_API=true TEST_REAL_DB=true python tests/comprehensive_test_suite.py

# Run specific test categories
python test_suite.py  # Unified scoring system
```

## 📊 Performance Metrics

Recent processing results (50 documents):
- **Processing Time**: 22.4 seconds
- **Citations Extracted**: 739
- **Document Types**: 60% opinions, 40% dockets
- **Completeness Score**: 37% average (44% for opinions)

## 🔧 Configuration

### Pipeline Configuration
```python
config = {
    'ingestion': {
        'court_ids': ['txed', 'cafc', 'nysd'],
        'document_types': ['opinions'],
        'max_per_court': 100
    },
    'processing': {
        'batch_size': 50,
        'extract_pdfs': True,
        'validate_strict': True
    }
}
```

### Environment Variables
```bash
COURTLISTENER_API_KEY=your-api-key
DATABASE_URL=postgresql://user:pass@host/db
DOCTOR_URL=http://doctor:5050  # If using Doctor service
LOG_LEVEL=INFO
```

## 📈 Database Schema

### Main Tables
- `court_documents`: Primary document storage with JSONB metadata
- `processed_documents_flp`: FLP-enhanced documents
- `courts_reference`: Court standardization data
- `judges`: Judge information with photos
- `normalized_reporters`: Citation reporter cache

### Example Queries
```sql
-- Find E.D. Texas cases
SELECT * FROM court_documents 
WHERE case_number LIKE '%TXED%' 
ORDER BY created_at DESC;

-- Find Judge Gilstrap cases
SELECT * FROM court_documents 
WHERE metadata->>'assigned_to' ILIKE '%gilstrap%';

-- Get documents needing PDF extraction
SELECT * FROM court_documents 
WHERE content IS NULL OR LENGTH(content) < 100;
```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection**: Ensure DATABASE_URL is correct
2. **PDF Extraction Fails**: Check if PyMuPDF is installed
3. **Low Completeness Scores**: Normal for dockets (limited text)
4. **API Rate Limits**: Add delays between requests

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚧 Known Limitations

1. **Court Resolution**: ~10% success rate (metadata often missing)
2. **RECAP Access**: Limited by API tier
3. **Processing Speed**: Sequential (could be parallelized)
4. **Judge Photos**: Requires exact name matches

## 🔮 Future Enhancements

- [ ] Concurrent document processing
- [ ] Enhanced court extraction from content
- [ ] Kubernetes deployment configuration
- [ ] Real-time processing webhooks
- [ ] Advanced citation graph analysis
- [ ] Machine learning for document classification

## 📝 License

[License information]

## 🤝 Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.

## 📞 Support

For issues or questions:
- Create an issue in the repository
- Check the comprehensive test suite for examples
- Review the design documentation in PIPELINE_PDF_INTEGRATION_DESIGN.md