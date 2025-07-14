# FLP Supplemental Integration Documentation

## Overview

The FLP Supplemental Integration enhances existing court data with Free Law Project tools without duplicating functionality or breaking existing systems. It works with both Juriscraper and CourtListener data sources.

## Architecture Principles

1. **Non-Destructive**: Never overwrites existing data
2. **Supplemental**: Only adds missing information
3. **Cached**: Stores results to avoid repeated processing
4. **Source-Aware**: Handles both Juriscraper and CourtListener data appropriately

## Database Schema

### New Tables

```sql
-- Court standardization mapping
court_data.court_standardization
  - original_code (PK)
  - flp_court_id
  - court_name
  - confidence
  - created_at

-- Citation normalization cache  
court_data.citation_normalization
  - original (PK)
  - normalized
  - reporter_full_name
  - reporter_metadata
  - created_at

-- Bad redaction findings
court_data.redaction_issues
  - document_id (PK)
  - document_type
  - has_bad_redactions
  - redaction_details
  - checked_at
```

### Modified Tables

```sql
-- Extended judges table
court_data.judges
  + photo_url
  + judge_pics_id
  + flp_metadata
```

### Metadata Structure

Enhancements are stored in the existing `metadata` JSONB field:

```json
{
  "existing_metadata": "...",
  "flp_supplemental": {
    "enhanced_at": "2025-07-14T12:00:00Z",
    "enhancements": {
      "text_extracted": true,
      "court_standardization": {
        "original": "ca9",
        "flp_court_id": "ca9",
        "court_name": "United States Court of Appeals for the Ninth Circuit"
      },
      "citations": {
        "citations_found": 5,
        "citations": [
          {
            "text": "123 F.3d 456",
            "reporter_normalized": "F.3d",
            "reporter_full_name": "Federal Reporter, Third Series"
          }
        ]
      },
      "redaction_check": {
        "checked": true,
        "has_bad_redactions": false
      },
      "judge": {
        "enhanced": true,
        "photo_url": "https://...",
        "judge_pics_id": 123
      }
    }
  }
}
```

## API Usage

### Single Opinion Enhancement

```bash
# Enhance a Juriscraper opinion
curl -X POST http://localhost:8090/enhance/opinion \
  -H "Content-Type: application/json" \
  -d '{
    "opinion_id": 12345,
    "source": "opinions"
  }'

# Enhance a CourtListener opinion
curl -X POST http://localhost:8090/enhance/opinion \
  -H "Content-Type: application/json" \
  -d '{
    "opinion_id": 67890,
    "source": "cl_opinions"
  }'
```

### Batch Enhancement

```bash
# Enhance up to 500 opinions from both sources
curl -X POST http://localhost:8090/enhance/batch \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 500,
    "source": "both"
  }'
```

### Check Enhancement Status

```bash
# Get overall statistics
curl http://localhost:8090/stats

# Get pending opinions
curl "http://localhost:8090/pending?source=both&limit=100"

# Monitor progress
curl http://localhost:8090/monitor/progress
```

## Enhancement Process

### 1. Text Extraction
- **Check**: Does the opinion have text content?
- **Action**: If missing, extract using Doctor service
- **Storage**: Update `text_content` (Juriscraper) or `plain_text` (CourtListener)

### 2. Court Standardization
- **Check**: Is the court code standardized?
- **Action**: Resolve using Courts-DB
- **Storage**: Cache in `court_standardization` table

### 3. Citation Enhancement
- **Check**: Are citations extracted and normalized?
- **Action**: Extract with Eyecite, normalize with Reporters-DB
- **Storage**: Store in metadata, respecting existing `opinions_cited`

### 4. Redaction Check
- **Check**: Has PDF been checked for bad redactions?
- **Action**: Analyze with X-Ray
- **Storage**: Cache results in `redaction_issues` table

### 5. Judge Photos
- **Check**: Does judge have a photo?
- **Action**: Search Judge-pics database
- **Storage**: Update `judges` table

## Integration with Existing Systems

### With Juriscraper Pipeline

```python
# In existing scraper
def process_scraped_opinion(pdf_path, metadata):
    # Save to database as normal
    opinion_id = save_opinion(pdf_path, metadata)
    
    # Trigger FLP enhancement
    requests.post(
        "http://court-processor:8090/enhance/opinion",
        json={"opinion_id": opinion_id, "source": "opinions"}
    )
```

### With CourtListener Import

```python
# After importing CourtListener data
def post_import_enhancement():
    # Trigger batch enhancement for new imports
    requests.post(
        "http://court-processor:8090/enhance/batch",
        json={"source": "cl_opinions", "limit": 1000}
    )
```

### With n8n Workflows

Create HTTP Request nodes to call:
- `/enhance/opinion` - Enhance specific documents
- `/stats` - Monitor enhancement coverage
- `/tools/extract-text` - Extract text from PDFs

## Docker Configuration

Add to `docker-compose.yml`:

```yaml
court-processor:
  environment:
    # Existing vars...
    DOCTOR_URL: http://doctor:5050
    FLP_API_PORT: 8090
```

## Performance Considerations

1. **Rate Limiting**: 
   - Batch processing limited to 5 concurrent operations
   - Doctor service has 16 workers configured

2. **Caching**:
   - Court standardizations cached indefinitely
   - Reporter normalizations cached indefinitely
   - Redaction checks cached (can be re-run if needed)

3. **Selective Enhancement**:
   - Only processes what's missing
   - Skips opinions with complete data

## Monitoring

### Key Metrics

1. **Coverage**: Percentage of opinions enhanced
2. **Text Extraction**: Number of PDFs processed
3. **Bad Redactions**: Count of problematic documents
4. **Judge Photos**: Coverage of judge portraits

### Example Monitoring Query

```sql
-- Enhancement coverage by month
SELECT 
    DATE_TRUNC('month', case_date) as month,
    COUNT(*) as total_opinions,
    COUNT(*) FILTER (WHERE metadata->>'flp_supplemental' IS NOT NULL) as enhanced,
    COUNT(*) FILTER (WHERE text_content IS NULL) as missing_text
FROM court_data.opinions
GROUP BY month
ORDER BY month DESC;
```

## Troubleshooting

### Common Issues

1. **Doctor Service Unavailable**
   - Check Docker logs: `docker-compose logs doctor`
   - Verify port 5050 is accessible

2. **Slow Enhancement**
   - Reduce batch size
   - Check Doctor service memory usage

3. **Missing Enhancements**
   - Verify opinion has required data (PDF path, etc.)
   - Check logs for specific errors

### Debug Commands

```bash
# Check Doctor service health
curl http://localhost:5050/

# View enhancement logs
docker-compose logs -f court-processor | grep FLP

# Check specific opinion metadata
psql -U postgres -d datacompose -c "
  SELECT metadata->'flp_supplemental' 
  FROM court_data.opinions 
  WHERE id = 12345
"
```

## Future Enhancements

1. **Scheduled Processing**: Automatic daily enhancement runs
2. **Quality Metrics**: Track enhancement quality/accuracy
3. **Webhook Integration**: Notify n8n when enhancements complete
4. **Citation Graph**: Build citation network visualization