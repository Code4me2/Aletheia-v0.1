# Free Law Project Integration - Unified Architecture

## Overview

This integration adds Free Law Project tools to the existing court-processor system, enhancing documents with:
- Court name standardization (Courts-DB)
- Advanced PDF processing (Doctor)
- Citation extraction and normalization (Eyecite, Reporters-DB)
- Bad redaction detection (X-ray)
- Judge photo lookup (Judge-pics)

## How It Fits With Existing Architecture

### Database Integration

The FLP integration works with the **existing `court_data` schema**:

```sql
-- Existing tables used:
court_data.opinions      -- Main opinions table (enhanced with FLP metadata)
court_data.judges        -- Extended with photo_url and judge_pics_id columns

-- New supporting tables:
court_data.courts_reference       -- Courts-DB standardization cache
court_data.normalized_reporters   -- Reporters-DB normalization cache
```

### Data Flow

1. **New Documents**: 
   - Court-processor scrapes document → 
   - Calls `/integrate/new-document` endpoint →
   - FLP tools enhance document →
   - Enhanced data saved to `opinions` table with FLP metadata in JSONB

2. **Existing Documents**:
   - Call `/enhance/opinion` with opinion ID →
   - FLP tools process stored document →
   - Updates `metadata` JSONB field with `flp_enhancements`

### Integration Points

1. **With Juriscraper Pipeline**:
   ```python
   # In existing scraper code:
   async def process_scraped_opinion(pdf_path, metadata):
       # Call FLP API for enhancement
       response = await http_client.post(
           "http://court-processor:8090/integrate/new-document",
           params={
               "pdf_path": pdf_path,
               "case_name": metadata['case_name'],
               "court_string": metadata['court'],
               # ... other fields
           }
       )
       
       enhanced_data = response.json()
       
       # Save to database with enhancements
       save_opinion_to_db(
           text_content=enhanced_data['text_content'],
           metadata={**metadata, **enhanced_data['metadata']}
       )
   ```

2. **With CourtListener Integration**:
   ```python
   # After importing CourtListener opinions:
   unenhanced_opinions = get_opinions_without_flp_processing()
   
   # Batch enhance
   await http_client.post(
       "http://court-processor:8090/enhance/batch",
       json={"opinion_ids": [op.id for op in unenhanced_opinions]}
   )
   ```

3. **With n8n Workflows**:
   - n8n can call FLP API endpoints directly
   - Citation extraction for document analysis
   - Court standardization for search improvement

## Metadata Structure

Enhanced opinions have this metadata structure:

```json
{
  "existing_metadata": "...",
  "flp_enhancements": {
    "processed_at": "2025-07-14T10:30:00Z",
    "court_standardized": "ca9",
    "citations_found": 5,
    "citations": [
      {
        "text": "123 F.3d 456",
        "normalized_reporter": "F.3d",
        "reporter_full_name": "Federal Reporter, Third Series",
        "volume": 123,
        "page": 456
      }
    ],
    "has_bad_redactions": false,
    "judge_photo_url": "https://judge-pics.com/photos/123.jpg",
    "page_count": 25,
    "doctor_results": {
      "extracted_by_ocr": false,
      "extraction_method": "pdftotext"
    }
  }
}
```

## API Endpoints

### Enhancement Operations
- `POST /enhance/opinion` - Enhance single existing opinion
- `POST /enhance/batch` - Enhance multiple opinions
- `GET /enhance/pending` - List opinions needing enhancement
- `POST /integrate/new-document` - Process new document with FLP tools

### FLP Tools
- `POST /tools/court/resolve` - Standardize court name
- `GET /tools/court/list` - List all standardized courts
- `POST /tools/citations/extract` - Extract citations from text
- `POST /tools/reporter/normalize` - Normalize reporter abbreviation

### Statistics
- `GET /stats/enhancement` - Enhancement coverage statistics

## Deployment

The FLP API runs alongside the existing court-processor:

```yaml
# In docker-compose.yml
court-processor:
  # ... existing config ...
  environment:
    # ... existing vars ...
    DOCTOR_URL: http://doctor:5050
  ports:
    - "8090:8090"  # FLP API port
```

## Usage Examples

### 1. Enhance Existing Opinion
```bash
curl -X POST http://localhost:8090/enhance/opinion \
  -H "Content-Type: application/json" \
  -d '{"opinion_id": 12345}'
```

### 2. Extract Citations
```bash
curl -X POST http://localhost:8090/tools/citations/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "See Smith v. Jones, 123 F.3d 456 (9th Cir. 2020)"}'
```

### 3. Check Enhancement Stats
```bash
curl http://localhost:8090/stats/enhancement
```

## Benefits

1. **No Schema Changes**: Works with existing `opinions` table
2. **Backward Compatible**: Doesn't break existing functionality
3. **Progressive Enhancement**: Can process documents incrementally
4. **Unified Data**: All data in one place, no need to join multiple tables
5. **n8n Compatible**: REST API works with n8n HTTP nodes

## Next Steps

1. Update existing scrapers to call FLP enhancement API
2. Run batch enhancement on historical opinions
3. Create n8n workflows for citation analysis
4. Set up monitoring for enhancement coverage