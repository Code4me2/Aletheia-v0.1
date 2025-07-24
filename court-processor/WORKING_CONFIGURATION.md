# Court Processor Working Configuration

## Summary of Fixes Applied

### 1. Database Connection
- **Issue**: Pipeline tried to connect to hostname `db` which resolved to external IP when running outside Docker
- **Fix**: Run court processor inside Docker container `aletheia-court-processor-1` where it can access the database via Docker network

### 2. Database Schema
- **Issue**: Missing `case_name` column in `court_documents` table
- **Fix**: Added column with: `ALTER TABLE court_documents ADD COLUMN IF NOT EXISTS case_name TEXT;`

### 3. RECAP API Field Mapping
- **Issue**: RECAP search results use different field names than expected (e.g., `caseName` vs `case_name`, `docketNumber` vs `case_number`)
- **Fix**: Updated `_process_recap_result()` in `document_ingestion_service.py` to use correct field names and store documents even without text content (metadata is valuable)

### 4. Missing Dependencies
- **Issue**: Pipeline couldn't find `pipeline_exceptions.py`, `pipeline_validators.py`, `error_reporter.py`, and `integrate_pdf_to_pipeline.py`
- **Fix**: Copied files from archive folders to root directory and into Docker container

## Current Status

✅ **Working Features:**
- Document ingestion from CourtListener API (both RECAP and opinions)
- RECAP availability checking (saves money by avoiding unnecessary purchases)
- Document storage with comprehensive metadata
- IP-focused search using nature of suit codes (820, 830, 835, 840)
- Delaware court document retrieval
- Full 11-stage pipeline processing
- Error handling and validation
- Report generation

⚠️ **Known Limitations:**
- PACER login still fails (credential issue) - but most documents are already in RECAP
- Low completeness scores (19.2%) for RECAP dockets - this is expected as they contain primarily metadata
- Database connections can timeout during long processing runs

## Running the Pipeline

### Quick Test
```bash
# Run debug ingestion (5 documents)
docker exec aletheia-court-processor-1 python debug_ingestion.py
```

### Full Delaware Ingestion
```bash
# Run full Delaware court ingestion
docker exec aletheia-court-processor-1 python run_delaware_ingestion.py
```

### Custom Configuration
```python
# Edit run_delaware_ingestion.py to customize:
config = {
    'ingestion': {
        'court_ids': ['ded', 'debankr'],  # Courts to search
        'document_types': ['opinions'],     # Document types
        'max_per_court': 50,               # Max documents per court
        'lookback_days': 30,               # Date range
        'nature_of_suit': ['820', '830', '835', '840'],  # IP codes
        'search_type': 'r'                 # 'r' for RECAP, 'o' for opinions
    }
}
```

## Database Queries

### Check Recent Ingestions
```sql
-- Inside container
docker exec aletheia-db-1 psql -U aletheia -d aletheia -c "
SELECT case_number, case_name, document_type, 
       metadata->>'court_id' as court_id, 
       metadata->>'date_filed' as date_filed,
       created_at
FROM court_documents 
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC 
LIMIT 10;"
```

### Check Delaware Documents
```sql
docker exec aletheia-db-1 psql -U aletheia -d aletheia -c "
SELECT COUNT(*) as total,
       COUNT(CASE WHEN metadata->>'court_id' = 'ded' THEN 1 END) as delaware_district,
       COUNT(CASE WHEN metadata->>'court_id' = 'debankr' THEN 1 END) as delaware_bankruptcy
FROM court_documents
WHERE metadata->>'court_id' IN ('ded', 'debankr');"
```

## Next Steps

1. **PDF Content Extraction**: Implement downloading and extracting text from RECAP documents marked as available
2. **Enhanced Metadata Processing**: Improve extraction of judge names, case parties, and other metadata
3. **PACER Integration**: Resolve credential issues to enable direct document purchases
4. **Performance Optimization**: Address database connection timeouts during long runs
5. **Monitoring**: Add health checks and progress tracking for long-running ingestions

## Environment Variables

Ensure these are set in the parent `.env` file:
```env
COURTLISTENER_API_TOKEN=your-token-here
PACER_USERNAME=your-username
PACER_PASSWORD=your-password
DB_USER=aletheia
DB_PASSWORD=aletheia123
DB_NAME=aletheia
```

## Architecture Notes

- Court processor runs as a Docker service connected to the main Aletheia stack
- Uses PostgreSQL database shared with other services
- Ingestion and processing are separate phases for flexibility
- Pipeline stages are modular and can be individually debugged
- Error handling preserves partial results rather than failing completely