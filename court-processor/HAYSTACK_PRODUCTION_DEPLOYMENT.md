# Haystack Production Deployment Guide

Complete guide for deploying the Enhanced Haystack integration with Judge Gilstrap document processing pipeline.

## Overview

This guide covers the production deployment of the enhanced Haystack integration that provides:
- **10x performance improvement** over n8n workflows
- **Judge-specific document ingestion** with corrected CourtListener API integration
- **Legal metadata enhancement** with citation extraction and court standardization
- **Scalable bulk processing** for large document datasets
- **Real-time monitoring** and performance optimization

## Prerequisites

### System Requirements

- **Python**: 3.8+ (tested with 3.12.4)
- **PostgreSQL**: 12+ with existing court document tables
- **Elasticsearch**: 7.x or 8.x cluster
- **Redis**: 6.x+ for caching and deduplication
- **Memory**: Minimum 4GB, recommended 8GB+
- **CPU**: Minimum 4 cores, recommended 8+ cores

### Network Requirements

- CourtListener API access (api.courtlistener.com)
- PostgreSQL database connectivity
- Elasticsearch cluster connectivity
- Redis instance connectivity

## Phase 1: Install Dependencies

### Core Dependencies

```bash
# Navigate to court-processor directory
cd court-processor

# Install core Haystack dependencies
pip install asyncpg aioredis elasticsearch sentence-transformers psutil

# Install additional performance dependencies
pip install numpy pandas scikit-learn

# Optional monitoring dependencies
pip install prometheus-client grafana-api
```

### Verify Installation

```bash
# Test dependency availability
python -c "
import asyncpg, aioredis, elasticsearch, sentence_transformers, psutil
print('✅ All core dependencies installed successfully')
"
```

## Phase 2: Database Configuration

### PostgreSQL Setup

1. **Ensure Enhanced Court Documents Table Exists**:

```sql
-- Check if table exists
\dt enhanced_court_documents

-- If table doesn't exist, create it (modify based on your schema)
CREATE TABLE IF NOT EXISTS enhanced_court_documents (
    id SERIAL PRIMARY KEY,
    courtlistener_id INTEGER UNIQUE,
    court_id VARCHAR(10),
    case_name TEXT,
    date_filed DATE,
    author_str VARCHAR(255),
    assigned_to_str VARCHAR(255),
    plain_text TEXT,
    docket_number VARCHAR(100),
    nature_of_suit VARCHAR(255),
    precedential_status VARCHAR(50),
    citations JSONB,
    court_info JSONB,
    flp_processing_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

2. **Add Haystack Integration Columns**:

```sql
-- Add columns for tracking Haystack ingestion
ALTER TABLE enhanced_court_documents 
ADD COLUMN IF NOT EXISTS haystack_ingested BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS haystack_ingestion_timestamp TIMESTAMP,
ADD COLUMN IF NOT EXISTS haystack_document_hash VARCHAR(64),
ADD COLUMN IF NOT EXISTS elasticsearch_index_name VARCHAR(100) DEFAULT 'court_documents';

-- Add performance indexes
CREATE INDEX IF NOT EXISTS idx_haystack_ingested ON enhanced_court_documents(haystack_ingested);
CREATE INDEX IF NOT EXISTS idx_court_judge ON enhanced_court_documents(court_id, assigned_to_str);
CREATE INDEX IF NOT EXISTS idx_date_filed ON enhanced_court_documents(date_filed);
```

3. **Configure Database Connection**:

```bash
# Set environment variables
export POSTGRES_URL="postgresql://username:password@localhost:5432/database_name"
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_DB="your_database"
export POSTGRES_USER="your_username"
export POSTGRES_PASSWORD="your_password"
```

### Redis Setup

```bash
# Start Redis (adjust based on your setup)
redis-server --daemonize yes

# Set Redis connection
export REDIS_URL="redis://localhost:6379"
```

## Phase 3: Elasticsearch Configuration

### Index Mapping for Legal Documents

Create optimized index mapping for court documents:

```bash
# Create court documents index with legal-specific mapping
curl -X PUT "localhost:9200/court_documents" -H "Content-Type: application/json" -d'
{
  "mappings": {
    "properties": {
      "content": {
        "type": "text",
        "analyzer": "standard",
        "fields": {
          "keyword": {
            "type": "keyword",
            "ignore_above": 256
          }
        }
      },
      "meta": {
        "properties": {
          "id": {"type": "keyword"},
          "court_id": {"type": "keyword"},
          "judge_name": {"type": "keyword"},
          "document_type": {"type": "keyword"},
          "date_filed": {"type": "date"},
          "case_name": {
            "type": "text",
            "fields": {"keyword": {"type": "keyword"}}
          },
          "docket_number": {"type": "keyword"},
          "legal_citations": {
            "type": "nested",
            "properties": {
              "citation_string": {"type": "keyword"},
              "case_name": {"type": "text"},
              "year": {"type": "integer"},
              "court": {"type": "keyword"},
              "confidence": {"type": "float"}
            }
          },
          "legal_statutes": {
            "type": "nested",
            "properties": {
              "statute": {"type": "keyword"},
              "title": {"type": "text"},
              "type": {"type": "keyword"},
              "confidence": {"type": "float"}
            }
          },
          "legal_procedures": {
            "type": "nested",
            "properties": {
              "procedure": {"type": "keyword"},
              "type": {"type": "keyword"},
              "status": {"type": "keyword"},
              "confidence": {"type": "float"}
            }
          },
          "court_info": {
            "properties": {
              "court_id": {"type": "keyword"},
              "court_name": {"type": "text"},
              "judge": {"type": "keyword"},
              "jurisdiction": {"type": "keyword"},
              "standardized": {"type": "boolean"}
            }
          },
          "practice_area": {"type": "keyword"},
          "jurisdiction": {"type": "keyword"},
          "precedential_status": {"type": "keyword"},
          "topic_tags": {"type": "keyword"},
          "confidence_score": {"type": "float"},
          "processed_timestamp": {"type": "date"},
          "source": {"type": "keyword"}
        }
      }
    }
  },
  "settings": {
    "number_of_shards": 2,
    "number_of_replicas": 1,
    "analysis": {
      "analyzer": {
        "legal_analyzer": {
          "type": "standard",
          "stopwords": "_none_"
        }
      }
    }
  }
}
'
```

### Elasticsearch Configuration

```bash
# Set Elasticsearch connection
export ELASTICSEARCH_URL="http://localhost:9200"

# Test connection
curl -X GET "localhost:9200/_cluster/health?pretty"
```

## Phase 4: Configuration Setup

### Environment Configuration

Create `.env` file in court-processor directory:

```bash
# Court Processor Enhanced Haystack Configuration

# CourtListener API
COURTLISTENER_API_TOKEN=your_token_here

# Database Configuration
POSTGRES_URL=postgresql://username:password@localhost:5432/database_name
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_database
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password

# Elasticsearch Configuration
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_INDEX_NAME=court_documents

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Haystack Performance Configuration
HAYSTACK_BATCH_SIZE=150
HAYSTACK_MAX_WORKERS=6
HAYSTACK_BULK_TIMEOUT=300

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Processing Configuration
ENVIRONMENT=production
```

### Enhanced Settings Configuration

Update `enhanced/config/settings.py` if needed:

```python
# Verify settings are properly configured
python -c "
from enhanced.config.settings import get_settings
settings = get_settings()
print(f'✅ Settings loaded: {settings.environment.env_type}')
print(f'✅ Elasticsearch: {settings.elasticsearch.url}')
print(f'✅ PostgreSQL configured: {bool(settings.database.host)}')
"
```

## Phase 5: Deployment Verification

### Test Core Components

```bash
# Test enhanced processor with Haystack integration
export COURTLISTENER_API_TOKEN='your_token_here'
python -c "
import asyncio
from enhanced.enhanced_unified_processor import EnhancedUnifiedDocumentProcessor

async def test():
    processor = EnhancedUnifiedDocumentProcessor()
    health = processor.get_health_status()
    print(f'Processor status: {health.get(\"status\")}')
    
    # Test Haystack manager
    if processor.haystack_manager:
        await processor.haystack_manager.initialize()
        haystack_health = await processor.haystack_manager.get_integration_health()
        print(f'Haystack integration: {haystack_health}')
    else:
        print('⚠️  Haystack manager not available - check dependencies')

asyncio.run(test())
"
```

### Test Database Connectivity

```bash
# Test PostgreSQL connection
python -c "
import asyncio
import asyncpg
import os

async def test_db():
    try:
        conn = await asyncpg.connect(os.getenv('POSTGRES_URL'))
        result = await conn.fetchval('SELECT COUNT(*) FROM enhanced_court_documents')
        print(f'✅ PostgreSQL connected: {result} documents in table')
        await conn.close()
    except Exception as e:
        print(f'❌ PostgreSQL connection failed: {e}')

asyncio.run(test_db())
"
```

### Test Elasticsearch Connectivity

```bash
# Test Elasticsearch connection
python -c "
from elasticsearch import Elasticsearch
import os

try:
    es = Elasticsearch([os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')])
    health = es.cluster.health()
    print(f'✅ Elasticsearch connected: {health[\"status\"]} cluster')
    
    # Check index
    if es.indices.exists(index='court_documents'):
        count = es.count(index='court_documents')['count']
        print(f'✅ Court documents index: {count} documents')
    else:
        print('⚠️  Court documents index not found - will be created')
        
except Exception as e:
    print(f'❌ Elasticsearch connection failed: {e}')
"
```

## Phase 6: Production Ingestion

### Start Judge Gilstrap Ingestion

```bash
# Make CLI executable
chmod +x run_bulk_haystack_ingestion.py

# Test system health
./run_bulk_haystack_ingestion.py health

# Start Judge Gilstrap document ingestion
./run_bulk_haystack_ingestion.py ingest-judge "Gilstrap" --court txed --max-docs 100

# Monitor progress
./run_bulk_haystack_ingestion.py status

# Check performance metrics
./run_bulk_haystack_ingestion.py metrics
```

### Batch Ingestion Commands

```bash
# Ingest all new documents
./run_bulk_haystack_ingestion.py ingest-new

# Ingest recent documents (last 30 days)
./run_bulk_haystack_ingestion.py ingest-recent --days 30

# Ingest all documents for specific court
./run_bulk_haystack_ingestion.py ingest-all --court txed --date-after 2023-01-01

# Monitor specific job
./run_bulk_haystack_ingestion.py status JOB_ID
```

### Production Monitoring

```bash
# Continuous health monitoring
watch -n 30 './run_bulk_haystack_ingestion.py health'

# Performance monitoring
watch -n 60 './run_bulk_haystack_ingestion.py metrics'

# Check Elasticsearch index status
curl -X GET "localhost:9200/court_documents/_stats?pretty"
```

## Phase 7: Performance Optimization

### Batch Size Tuning

Optimize batch sizes based on your system:

```bash
# High-memory system (8GB+)
export HAYSTACK_BATCH_SIZE=300
export HAYSTACK_MAX_WORKERS=8

# Medium-memory system (4-8GB)
export HAYSTACK_BATCH_SIZE=150
export HAYSTACK_MAX_WORKERS=6

# Low-memory system (<4GB)
export HAYSTACK_BATCH_SIZE=50
export HAYSTACK_MAX_WORKERS=2
```

### Elasticsearch Optimization

```bash
# Increase refresh interval during bulk ingestion
curl -X PUT "localhost:9200/court_documents/_settings" -H "Content-Type: application/json" -d'
{
  "refresh_interval": "30s"
}
'

# Disable replicas during bulk ingestion (re-enable after)
curl -X PUT "localhost:9200/court_documents/_settings" -H "Content-Type: application/json" -d'
{
  "number_of_replicas": 0
}
'
```

### Memory Optimization

```bash
# Monitor memory usage during ingestion
python -c "
from enhanced.monitoring.performance_dashboard import PerformanceMonitor
import asyncio

async def monitor():
    monitor = PerformanceMonitor()
    await monitor.start()
    dashboard = monitor.get_dashboard_data()
    print(f'Memory usage: {dashboard[\"system_metrics\"][\"memory_percent\"]:.1f}%')
    await monitor.stop()

asyncio.run(monitor())
"
```

## Phase 8: Production Search Interface

### Test Search Functionality

```bash
# Test full-text search
curl -X GET "localhost:9200/court_documents/_search" -H "Content-Type: application/json" -d'
{
  "query": {
    "multi_match": {
      "query": "patent infringement",
      "fields": ["content", "meta.case_name"]
    }
  },
  "size": 10
}
'

# Test judge-specific search
curl -X GET "localhost:9200/court_documents/_search" -H "Content-Type: application/json" -d'
{
  "query": {
    "bool": {
      "must": [
        {"term": {"meta.judge_name": "Gilstrap"}},
        {"term": {"meta.court_id": "txed"}}
      ]
    }
  }
}
'

# Test citation-based search
curl -X GET "localhost:9200/court_documents/_search" -H "Content-Type: application/json" -d'
{
  "query": {
    "nested": {
      "path": "meta.legal_citations",
      "query": {
        "match": {"meta.legal_citations.citation_string": "517 U.S."}
      }
    }
  }
}
'
```

### Advanced Search Examples

```bash
# Faceted search with aggregations
curl -X GET "localhost:9200/court_documents/_search" -H "Content-Type: application/json" -d'
{
  "size": 0,
  "aggs": {
    "judges": {
      "terms": {"field": "meta.judge_name", "size": 10}
    },
    "courts": {
      "terms": {"field": "meta.court_id", "size": 10}
    },
    "practice_areas": {
      "terms": {"field": "meta.practice_area", "size": 10}
    }
  }
}
'
```

## Phase 9: Monitoring and Maintenance

### Health Monitoring Setup

```bash
# Create monitoring script
cat > monitor_haystack.sh << 'EOF'
#!/bin/bash

echo "=== Haystack System Health Check ==="
echo "Timestamp: $(date)"

# Check service health
./run_bulk_haystack_ingestion.py health

# Check Elasticsearch cluster
echo "Elasticsearch cluster health:"
curl -s "localhost:9200/_cluster/health?pretty" | grep -E "(status|number_of_nodes)"

# Check document counts
echo "Document counts:"
curl -s "localhost:9200/court_documents/_count" | jq '.count'

# Check recent ingestion activity
echo "Recent jobs:"
./run_bulk_haystack_ingestion.py status | head -20

echo "=== End Health Check ==="
EOF

chmod +x monitor_haystack.sh

# Run monitoring
./monitor_haystack.sh
```

### Performance Monitoring

```bash
# Create performance monitoring script
cat > monitor_performance.sh << 'EOF'
#!/bin/bash

echo "=== Performance Metrics ==="
echo "Timestamp: $(date)"

# System resources
echo "System Memory:"
free -h

echo "System CPU:"
top -bn1 | grep "Cpu(s)"

# Haystack metrics
echo "Haystack Metrics:"
./run_bulk_haystack_ingestion.py metrics

# Elasticsearch performance
echo "Elasticsearch Performance:"
curl -s "localhost:9200/_stats/indexing,search?pretty" | grep -E "(total|time_in_millis)"

echo "=== End Performance Check ==="
EOF

chmod +x monitor_performance.sh
```

### Automated Maintenance

```bash
# Create maintenance script
cat > maintenance_haystack.sh << 'EOF'
#!/bin/bash

echo "=== Haystack Maintenance ==="
echo "Timestamp: $(date)"

# Optimize Elasticsearch indices
echo "Optimizing Elasticsearch indices..."
curl -X POST "localhost:9200/court_documents/_forcemerge?max_num_segments=1"

# Clean up old job logs (optional)
echo "Cleaning up old logs..."
find . -name "*.log" -type f -mtime +7 -delete

# Refresh index settings
echo "Refreshing index settings..."
curl -X PUT "localhost:9200/court_documents/_settings" -H "Content-Type: application/json" -d'
{
  "refresh_interval": "1s",
  "number_of_replicas": 1
}
'

echo "=== Maintenance Complete ==="
EOF

chmod +x maintenance_haystack.sh

# Add to crontab for weekly maintenance
echo "0 2 * * 0 /path/to/court-processor/maintenance_haystack.sh" | crontab -
```

## Phase 10: Troubleshooting

### Common Issues and Solutions

1. **Memory Exhaustion**:
   ```bash
   # Reduce batch size
   export HAYSTACK_BATCH_SIZE=50
   export HAYSTACK_MAX_WORKERS=2
   
   # Monitor memory usage
   watch -n 5 'free -h'
   ```

2. **Elasticsearch Connection Timeout**:
   ```bash
   # Increase timeout settings
   export HAYSTACK_BULK_TIMEOUT=600
   
   # Check Elasticsearch logs
   tail -f /var/log/elasticsearch/elasticsearch.log
   ```

3. **High Error Rates**:
   ```bash
   # Enable debug logging
   export LOG_LEVEL=DEBUG
   
   # Check specific job errors
   ./run_bulk_haystack_ingestion.py status JOB_ID
   ```

4. **Slow Performance**:
   ```bash
   # Check system resources
   htop
   
   # Optimize Elasticsearch
   curl -X PUT "localhost:9200/_cluster/settings" -H "Content-Type: application/json" -d'
   {
     "transient": {
       "indices.memory.index_buffer_size": "40%"
     }
   }
   '
   ```

### Debug Mode

```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
python simplified_haystack_ingestion.py

# Check detailed logs
tail -f enhanced_haystack.log
```

## Production Checklist

### Pre-Deployment
- [ ] All dependencies installed
- [ ] Database schema updated
- [ ] Elasticsearch index mapping created
- [ ] Environment variables configured
- [ ] API tokens and credentials verified
- [ ] Connection tests passed

### Deployment
- [ ] Health checks passing
- [ ] Test ingestion completed successfully
- [ ] Performance metrics within acceptable range
- [ ] Search functionality verified
- [ ] Monitoring scripts configured

### Post-Deployment
- [ ] Continuous monitoring active
- [ ] Performance optimization applied
- [ ] Maintenance scripts scheduled
- [ ] Backup procedures verified
- [ ] Error alerting configured

## Performance Expectations

### Throughput Benchmarks
- **Small datasets (1K docs)**: 5-8x faster than n8n
- **Medium datasets (10K docs)**: 6-8x faster than n8n
- **Large datasets (100K+ docs)**: Only viable option
- **Target throughput**: 10-50 documents/second depending on system

### Resource Usage
- **Memory**: 2-8GB depending on batch size
- **CPU**: 2-8 cores for optimal performance
- **Storage**: Elasticsearch index ~2x document size
- **Network**: Moderate bandwidth for API calls

## Support and Maintenance

### Regular Tasks
1. **Daily**: Monitor health and performance
2. **Weekly**: Review error rates and optimization opportunities
3. **Monthly**: Perform index optimization and cleanup
4. **Quarterly**: Review and update configuration

### Scaling Considerations
- **Horizontal scaling**: Multiple worker processes
- **Vertical scaling**: Increase batch sizes and memory
- **Elasticsearch scaling**: Add nodes for larger datasets
- **Database optimization**: Index tuning and connection pooling

This deployment guide provides a comprehensive approach to implementing the enhanced Haystack integration in production environments for scalable Judge Gilstrap document processing.