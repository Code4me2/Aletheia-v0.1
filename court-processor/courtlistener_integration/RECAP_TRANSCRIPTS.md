# CourtListener RECAP & Transcript Integration

This integration provides infrastructure for downloading and processing RECAP documents, with special focus on court transcripts. 

## IMPORTANT: API Access Requirements

**As of July 2025, RECAP document access requires special permissions from CourtListener/Free Law Project.**

With basic API access, you can:
- ✅ Search for documents mentioning transcripts (Search API)
- ✅ Access court information (Courts API)
- ✅ Limited access to docket metadata (Dockets API)
- ❌ Cannot access RECAP documents (requires special permissions)
- ❌ Cannot access docket entries (requires special permissions)
- ❌ Cannot download actual transcript PDFs

To get RECAP access:
1. Contact Free Law Project via their [contact form](https://www.courtlistener.com/contact/) or [GitHub Discussions](https://github.com/freelawproject/courtlistener/discussions)
2. Explain your use case (research, analysis, etc.)
3. Reference your existing API token

## Current Capabilities (with basic access)

### 1. Search API Support
- Search 8.4M+ documents for transcript references
- Find opinions that quote transcript excerpts
- Filter by court, date, and keywords
- No document download required

### 2. Transcript Detection (when RECAP access is granted)
The system is built to automatically identify transcripts using:
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

### 3. Infrastructure Ready
All code is ready for when RECAP access is granted:
- Bulk download scripts
- Database schema for transcript storage
- Automatic categorization
- Integration with FLP tools

## Usage

### With Basic API Access (Currently Available)

#### Search for Transcript References
```bash
cd court-processor/courtlistener_integration
python3 search_transcripts.py
```

This script searches for opinions mentioning transcripts and can find:
- Patent case transcripts
- Trademark depositions
- Hearing transcripts
- Trial proceedings

#### Test API Access
```bash
python3 test_recap_api.py
```

This will show which endpoints you have access to.

### With RECAP Access (Requires Permission)

Once you have RECAP permissions, these scripts will work:

```bash
# Test RECAP access
./run_transcript_test.sh

# Download transcripts for specific courts
python3 bulk_download_enhanced.py \
    --courts ded txed cand \
    --transcripts-only \
    --days 365

# Full download with all documents
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