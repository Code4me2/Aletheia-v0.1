# CourtListener RECAP & Transcript Integration

This enhanced integration adds support for downloading and processing RECAP documents, with special focus on court transcripts and extended human dialogue.

## New Capabilities

### 1. RECAP Document Support
- Download actual court filings (PDFs, documents)
- Access to motions, briefs, orders, and **transcripts**
- Full text extraction when available
- Automatic transcript detection

### 2. Transcript Detection
The system automatically identifies transcripts using:
- Description keywords (transcript, hearing, deposition, etc.)
- Document type classification
- Specialized transcript_type detection:
  - `deposition` - Deposition transcripts
  - `trial` - Trial transcripts
  - `hearing` - Motion hearings and other proceedings
  - `oral_argument` - Appellate oral arguments
  - `sentencing` - Sentencing hearings
  - `status_conference` - Status conferences
  - `other` - Other transcript types

### 3. Audio Recording Support
- Download oral argument recordings
- Link audio to related transcripts
- Track duration and judge information

## Usage

### Quick Test (Transcripts Only)
```bash
cd court-processor/courtlistener_integration
./run_transcript_test.sh
```

### Full Download with RECAP
```bash
# Download everything for Delaware (last 2 years)
python3 bulk_download_enhanced.py --courts ded --days 730

# Download only transcripts for multiple courts
python3 bulk_download_enhanced.py \
    --courts ded txed cand \
    --transcripts-only \
    --days 365

# High-priority courts with all RECAP documents
python3 bulk_download_enhanced.py \
    --high-priority-only \
    --days 180
```

### Loading into Database
```bash
# Load RECAP data
python3 load_recap_to_postgres.py --court ded

# View transcript statistics
psql $DATABASE_URL -c "SELECT * FROM court_data.recap_stats;"

# Query transcripts
psql $DATABASE_URL -c "
SELECT 
    case_name,
    description,
    transcript_type,
    page_count,
    text_length
FROM court_data.transcript_documents
WHERE transcript_type = 'deposition'
LIMIT 10;
"
```

## Database Schema

### New Tables
1. **cl_recap_documents** - Stores all RECAP documents
   - Automatic transcript detection
   - Full text storage
   - OCR status tracking

2. **cl_audio** - Audio recordings
   - Oral arguments
   - Links to transcripts

3. **transcript_documents** (view) - Easy access to all transcripts

### Key Queries

```sql
-- Find all deposition transcripts
SELECT * FROM court_data.cl_recap_documents
WHERE transcript_type = 'deposition';

-- Find transcripts with full text
SELECT * FROM court_data.transcript_documents
WHERE text_length > 1000;

-- Link audio to transcripts
SELECT 
    a.case_name,
    a.duration,
    t.description as transcript_desc
FROM court_data.cl_audio a
LEFT JOIN court_data.cl_recap_documents t
    ON a.transcript_document_id = t.id;
```

## API Endpoints Used

- `/recap/` - RECAP dockets
- `/recap-documents/` - Individual documents
- `/docket-entries/` - Docket entry listings
- `/audio/` - Audio recordings

## Rate Limiting

The system respects CourtListener's rate limits:
- 5,000 requests per hour (unauthenticated)
- Built-in rate limiter prevents exceeding limits
- Automatic retry with backoff

## Data Volume Estimates

For a typical district court (2 years):
- ~5,000-10,000 dockets
- ~50,000-100,000 docket entries
- ~100,000-200,000 RECAP documents
- ~5-10% are transcripts
- ~500-2,000 transcript documents per court

## Next Steps

1. **Text Extraction**: Implement PDF text extraction for documents without plain_text
2. **Vector Indexing**: Add embeddings for semantic search
3. **Transcript Analysis**: Build specialized NLP for legal transcripts
4. **Audio Transcription**: Convert audio recordings to text

## Troubleshooting

### No transcripts found
- Some courts may not have many digitized transcripts
- Try courts with high case volume (txed, cand, nysd)
- Check descriptions with: `description__icontains=transcript`

### Rate limit errors
- Reduce concurrent downloads
- Check your API token is valid
- Wait 1 hour between large downloads

### Database errors
- Ensure RECAP schema is created: `psql $DATABASE_URL -f scripts/add_recap_schema.sql`
- Check PostgreSQL logs for constraint violations
- Verify foreign key relationships exist