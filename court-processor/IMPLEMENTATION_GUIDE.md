# FLP Supplemental Integration - Implementation Guide

## Quick Start

### 1. Apply Database Migrations

```bash
# Connect to database
docker-compose exec db psql -U postgres -d datacompose

# Run the migration
\i /scripts/add_flp_supplemental_tables.sql
```

### 2. Rebuild and Start Services

```bash
# Stop existing services
docker-compose down

# Rebuild court-processor with new dependencies
docker-compose build court-processor

# Start all services including Doctor
docker-compose up -d
```

### 3. Verify Services

```bash
# Check Doctor service
curl http://localhost:5050/

# Check FLP API
curl http://localhost:8090/health

# View logs
docker-compose logs -f court-processor
```

### 4. Test Enhancement

```bash
# Enhance a single opinion
curl -X POST http://localhost:8090/enhance/opinion \
  -H "Content-Type: application/json" \
  -d '{"opinion_id": 1, "source": "opinions"}'

# Check statistics
curl http://localhost:8090/stats
```

## Integration Points

### For Existing Scrapers

Add to your scraper after saving an opinion:

```python
import requests

def enhance_opinion(opinion_id, source='opinions'):
    try:
        response = requests.post(
            'http://court-processor:8090/enhance/opinion',
            json={'opinion_id': opinion_id, 'source': source}
        )
        return response.json()
    except Exception as e:
        logger.error(f"Enhancement failed: {e}")
```

### For Batch Processing

Run periodic enhancements:

```python
# Enhance all pending opinions
response = requests.post(
    'http://court-processor:8090/enhance/batch',
    json={'limit': 500, 'source': 'both'}
)
```

### For n8n Integration

1. Import the workflow from `n8n_workflows/flp_enhancement_workflow.json`
2. Set up a schedule trigger (e.g., hourly)
3. Monitor results in n8n execution history

## Monitoring

### Check Enhancement Coverage

```sql
-- In PostgreSQL
SELECT * FROM court_data.flp_enhancement_status;
```

### View Recent Enhancements

```bash
curl http://localhost:8090/monitor/progress
```

### Check for Issues

```bash
# Opinions with bad redactions
curl http://localhost:8090/stats | jq '.redactions'

# Opinions missing text
curl http://localhost:8090/pending?limit=10
```

## Troubleshooting

### Common Issues

1. **Doctor service not starting**
   ```bash
   docker-compose logs doctor
   # Check memory limits - Doctor needs 1-2GB
   ```

2. **API not accessible**
   ```bash
   docker-compose ps court-processor
   # Should show port 8090 mapped
   ```

3. **Database connection errors**
   ```bash
   # Check environment variables
   docker-compose exec court-processor env | grep DB_
   ```

### Performance Tuning

1. **Adjust Doctor workers**
   ```yaml
   # In docker-compose.yml
   environment:
     - DOCTOR_WORKERS=8  # Reduce if memory constrained
   ```

2. **Batch size for enhancement**
   ```python
   # Smaller batches for limited resources
   response = requests.post('/enhance/batch', json={'limit': 50})
   ```

3. **Rate limiting**
   ```python
   # Add delay between requests
   import time
   time.sleep(1)  # 1 second between enhancements
   ```

## Next Steps

1. **Monitor Enhancement Progress**
   - Set up daily reports
   - Track coverage percentages
   - Identify problem documents

2. **Optimize Processing**
   - Prioritize recent opinions
   - Skip documents with known issues
   - Cache frequently accessed data

3. **Extend Integration**
   - Add webhook notifications
   - Create custom n8n nodes
   - Build citation network visualization