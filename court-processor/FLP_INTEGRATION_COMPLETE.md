# Free Law Project Complete Integration Guide

## Overview

This document describes the complete integration of all Free Law Project tools into the Aletheia court processor, transforming it from a basic 4-court scraper to a comprehensive legal document processing system supporting 200+ courts.

## Integrated Tools

### 1. **Courts-DB** ✅
- **Purpose**: Standardize court identification
- **Features**: 
  - Resolves 700+ court name variations
  - Handles historical court names
  - Provides standardized court IDs
- **Example**: "S.D.N.Y.", "SDNY", "Southern District of New York" → `court_id: "nysd"`

### 2. **Doctor** ✅
- **Purpose**: Advanced document processing
- **Features**:
  - PDF text extraction with OCR
  - Bad redaction detection (X-Ray integration)
  - Thumbnail generation
  - Multiple format conversions
- **Replaces**: Basic PyMuPDF extraction

### 3. **Juriscraper** ✅
- **Purpose**: Automated court opinion scraping
- **Features**:
  - Supports 200+ US courts
  - Standardized data extraction
  - Date-based filtering
  - Automatic retry logic
- **Expands**: From 4 courts to 200+ courts

### 4. **Eyecite** ✅
- **Purpose**: Legal citation extraction and analysis
- **Features**:
  - Extracts all citation types (Full, Short, Id., Supra)
  - Resolves citation references
  - Builds citation graphs
  - Tracks most-cited cases
- **Enables**: Citation network analysis

### 5. **X-Ray** ✅
- **Purpose**: Bad redaction detection
- **Features**:
  - Detects improperly redacted text in PDFs
  - Identifies text hidden under black boxes
  - Provides page and location details
- **Integration**: Via Doctor service or standalone

### 6. **Reporters-DB** ✅
- **Purpose**: Legal reporter normalization
- **Features**:
  - Normalizes reporter abbreviations
  - Provides full reporter names
  - Handles hundreds of variations
- **Example**: "Fed. 3d" → "F.3d" (Federal Reporter, Third Series)

### 7. **Judge-pics** ✅
- **Purpose**: Judge portrait database
- **Features**:
  - Search judges by name and court
  - Retrieve judge photos
  - Store photo URLs for display
- **Enhances**: User interface with judge portraits

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Applications                        │
│                    (n8n, Web UI, CLI Tools)                      │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI REST API (Port 8090)                  │
│                         /courts/*                                 │
│                         /documents/*                              │
│                         /citations/*                              │
│                         /judges/*                                 │
│                         /reporters/*                              │
└───────────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┬─────────────────┐
        ▼                               ▼                 ▼
┌─────────────────┐           ┌─────────────────┐ ┌─────────────────┐
│   Courts-DB     │           │     Doctor      │ │  Juriscraper    │
│  (In-process)   │           │   (Container)   │ │  (In-process)   │
└─────────────────┘           └─────────────────┘ └─────────────────┘
        │                               │                 │
        ▼                               ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PostgreSQL Database                       │
│  • courts_reference     • processed_documents_flp                │
│  • judges               • normalized_reporters                   │
│  • extracted_citations  • scraping_status                        │
└─────────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Courts-DB
- `POST /courts/resolve` - Resolve court name to ID
- `GET /courts/all` - List all courts
- `POST /courts/search` - Search courts by name

### Document Processing
- `POST /documents/process` - Process document through Doctor
- `GET /doctor/health` - Check Doctor service health

### Court Scraping
- `POST /scrape/court` - Scrape specific court
- `GET /scrape/courts/available` - List scrapeable courts (200+)
- `GET /scrape/status` - View scraping status

### Citation Analysis
- `POST /citations/extract` - Extract citations from text
- `GET /citations/graph` - Build citation network graph
- `GET /citations/most-cited` - Get most cited cases

### Reporter Normalization
- `POST /reporters/normalize` - Normalize reporter abbreviation
- `GET /reporters/list` - List all reporters

### Judge Information
- `POST /judges/photo` - Get judge photo URL
- `GET /judges/list` - List judges with photos

### Bad Redaction Detection
- `POST /xray/check-redactions` - Check PDF for bad redactions

### Comprehensive Processing
- `POST /process/comprehensive` - Use all FLP tools on document

## Usage Examples

### 1. Resolve Court Name
```bash
curl -X POST http://localhost:8090/courts/resolve \
  -H "Content-Type: application/json" \
  -d '{"court_string": "S.D.N.Y."}'

# Response:
{
  "court_id": "nysd",
  "name": "Southern District of New York",
  "type": "federal district",
  "confidence": "high"
}
```

### 2. Process Document Comprehensively
```bash
curl -X POST http://localhost:8090/process/comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/data/pdfs/opinion.pdf",
    "case_name": "Smith v. Jones",
    "court_string": "S.D.N.Y.",
    "date_filed": "2024-01-15",
    "judges": ["Katherine Polk Failla"]
  }'

# Response:
{
  "status": "processing started",
  "tools": ["Courts-DB", "X-Ray", "Eyecite", "Reporters-DB", "Judge-pics"]
}
```

### 3. Extract and Analyze Citations
```bash
curl -X POST http://localhost:8090/citations/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "See Brown v. Board, 347 U.S. 483 (1954). Id. at 495."
  }'

# Response includes normalized citations with reporter information
```

### 4. Get Judge Photo
```bash
curl -X POST http://localhost:8090/judges/photo \
  -H "Content-Type: application/json" \
  -d '{
    "judge_name": "Sonia Sotomayor",
    "court": "Supreme Court"
  }'

# Response:
{
  "found": true,
  "judge_name": "Sonia Sotomayor",
  "photo_url": "https://...",
  "court": "Supreme Court of the United States"
}
```

## CLI Tools

### Test All Integrations
```bash
./court-processor/cli.py test all
```

### List Available Courts
```bash
./court-processor/cli.py list-courts
# Shows 200+ courts organized by type
```

### Scrape Specific Court
```bash
./court-processor/cli.py scrape ca9 --days 7
```

### Start Automated Scheduler
```bash
./court-processor/cli.py scheduler
```

## Database Schema

### Enhanced Tables
```sql
-- Courts reference (700+ courts)
court_data.courts_reference

-- Comprehensive document processing
court_data.processed_documents_flp
  - court_id (standardized)
  - has_bad_redactions
  - normalized_citations (JSONB)
  - judge_ids (JSONB)

-- Judge information with photos
court_data.judges
  - photo_url
  - judge_pics_id

-- Citation normalization cache
court_data.normalized_reporters

-- Extracted citations with relationships
court_data.extracted_citations
```

## Docker Services

```yaml
court-processor:
  environment:
    - PYTHONPATH=/app
    - DB credentials
  ports:
    - "8090:8080"  # API access

doctor:
  image: freelawproject/doctor:latest
  ports:
    - "5050:5050"  # Document processing
  memory: 2G      # For OCR operations
```

## Benefits Achieved

1. **Court Coverage**: 4 courts → 200+ courts
2. **Citation Analysis**: Basic regex → Full citation graph
3. **Document Processing**: Simple text → OCR + bad redaction detection
4. **Court Identification**: Manual YAML → 700+ court database
5. **Data Enrichment**: Text only → Judge photos, normalized citations
6. **Automation**: Manual updates → Scheduled scraping

## Integration with n8n

Create workflows that:
1. Trigger court scraping on schedule
2. Process uploaded documents comprehensively
3. Build citation networks for research
4. Alert on bad redactions
5. Enrich UI with judge photos

## Monitoring and Maintenance

### Health Checks
```bash
# Check all services
curl http://localhost:8090/health

# View statistics
curl http://localhost:8090/stats/overview
```

### Logs
```bash
# API logs
docker-compose logs -f court-processor

# Doctor logs
docker-compose logs -f doctor
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure all FLP packages are installed
   - Check Python path includes `/app`

2. **Doctor Connection**
   - Verify Doctor container is running
   - Check network connectivity between containers

3. **Court Not Found**
   - Court might use different abbreviation
   - Try searching with partial name

4. **No Judge Photo**
   - Not all judges have photos available
   - Try different name variations

## Future Enhancements

1. **Real-time Updates**: WebSocket for live scraping status
2. **ML Integration**: Automated judge name extraction
3. **Citation Prediction**: Suggest relevant citations
4. **Batch Processing**: Handle multiple documents efficiently
5. **Export Options**: Generate citation reports

## Conclusion

The Free Law Project integration transforms Aletheia's court processor into a comprehensive legal document processing system. With support for 200+ courts, advanced citation analysis, bad redaction detection, and judge information, it provides a solid foundation for legal research and document management applications.