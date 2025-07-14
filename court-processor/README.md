# Court Processor with Free Law Project Integration

A comprehensive court opinion processor that leverages Free Law Project tools to provide advanced legal document processing, supporting 200+ US courts with citation analysis, bad redaction detection, and judge information.

## Features

### Core Capabilities
- **200+ Court Support**: Automated scraping via Juriscraper (expanded from 4 courts)
- **Advanced PDF Processing**: OCR, text extraction, and thumbnail generation via Doctor
- **Court Standardization**: 700+ court name variations resolved via Courts-DB
- **Citation Analysis**: Extract and analyze legal citations with Eyecite
- **Bad Redaction Detection**: Identify improperly redacted sensitive information with X-Ray
- **Reporter Normalization**: Standardize legal reporter abbreviations with Reporters-DB
- **Judge Photos**: Retrieve judge portraits via Judge-pics
- **REST API**: Comprehensive API for all functionality
- **PostgreSQL Integration**: Enhanced schema for legal metadata
- **Scheduled Updates**: Automated court-specific scheduling

## Quick Start

### 1. Setup

```bash
# Copy this court-processor directory to your data-compose folder
cp -r court-processor /path/to/data-compose/

# Navigate to data-compose directory
cd /path/to/data-compose

# Copy the Docker override file
cp court-processor/docker-compose.override.yml .

# Create data directories
mkdir -p court-data/pdfs court-data/logs
```

### 2. Database Initialization

```bash
# Initialize the court data schema
docker-compose exec db psql -U postgres -d postgres -f /court-processor/scripts/init_db.sql

# Or run through the processor
docker-compose exec court_processor python processor.py --init-db
```

### 3. Start Processing

```bash
# Add court processor to your docker-compose
docker-compose up -d court_processor

# Check logs
docker-compose logs -f court_processor

# Manual scrape of a specific court
docker-compose exec court_processor python processor.py --court tax

# Process all configured courts
docker-compose exec court_processor python processor.py --all
```

## Configuration

### Courts

Edit `config/courts.yaml` to enable/disable courts:

```yaml
courts:
  tax:
    name: "United States Tax Court"
    active: true
    module: "tax"
```

### Scheduling

The cron schedule is defined in `scripts/court-schedule`:
- Tax Court: Daily at 2 AM (✅ Fully implemented)
- First Circuit: Daily at 3 AM (⚠️ Configuration only - implementation pending)
- DC Circuit: Daily at 4 AM (⚠️ Configuration only - implementation pending)
- Full run: Sundays at 5 AM

**Note**: Currently, only the Tax Court module is fully implemented. Other courts are configured but require the corresponding scraper modules to be developed.

## Database Schema

The processor creates a `court_data` schema with two main tables:

- **judges**: Stores unique judge names
- **opinions**: Stores opinion text and metadata, optimized for judge-based queries

## Integration with Data-Compose

### Using Opinions in n8n Workflows

1. Query opinions by judge:
```sql
SELECT * FROM court_data.opinions o
JOIN court_data.judges j ON o.judge_id = j.id
WHERE j.name = 'Judge Smith'
ORDER BY o.case_date DESC;
```

2. Get unindexed opinions for RAG:
```sql
SELECT * FROM court_data.opinions
WHERE vector_indexed = false
LIMIT 100;
```

3. Search opinions by text:
```sql
SELECT * FROM court_data.opinions
WHERE to_tsvector('english', text_content) @@ plainto_tsquery('constitutional');
```

### Creating n8n Workflow

Create a workflow that:
1. Queries new opinions from court_data
2. Sends them through Hierarchical Summarization
3. Indexes in Haystack
4. Updates vector_indexed flag

## Monitoring

Check processing status:
```bash
# View logs
tail -f court-data/logs/court-processor.log
tail -f court-data/logs/cron.log

# Check database
docker-compose exec db psql -U postgres -d postgres -c "SELECT * FROM court_data.processing_log ORDER BY started_at DESC LIMIT 10;"

# Judge statistics
docker-compose exec db psql -U postgres -d postgres -c "SELECT * FROM court_data.judge_stats ORDER BY opinion_count DESC LIMIT 20;"
```

## Troubleshooting

### No PDFs downloading
- Check court website accessibility
- Verify DATABASE_URL in environment
- Check logs for specific errors

### OCR not working
- Ensure Tesseract is installed in container
- Check available memory for OCR processing
- OCR can be disabled by setting OCR_ENABLED=false

### Database connection issues
- Verify DATABASE_URL matches data-compose settings
- Ensure court_processor is on the same Docker network
- Check PostgreSQL logs

## Security Notes

- PDFs are downloaded to isolated directory
- All judge names are normalized and sanitized
- Database connections use environment variables
- No external API exposure

## Future Enhancements

- Integration with Hierarchical Summarization node
- Automatic vector indexing
- Judge-specific alert rules
- More sophisticated scheduling options