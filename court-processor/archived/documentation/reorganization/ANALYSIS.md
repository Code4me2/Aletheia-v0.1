# Court Processor - Consolidated Documentation

## Overview

The Court Processor is a judiciary insights platform that collects, processes, and serves court documents through both a CLI and REST API. It currently manages **485 documents** from various courts, primarily focusing on opinions from judges like Rodney Gilstrap.

## System Architecture

### Database Schema Confusion

The system has **multiple overlapping database schemas** that are not all actively used:

1. **`public.court_documents`** - Actually used by the simplified API (port 8104)
   - Fields: id, case_number, document_type, content, metadata, created_at
   - Document types: `opinion`, `020lead`, `opinion_doctor`, `docket`

2. **`court_data.opinions`** - Original juriscraper schema (init_db.sql)
   - Judge-focused design with PDF storage
   - Not actively used by current API

3. **`court_data.cl_*` tables** - CourtListener integration (init_courtlistener_schema.sql)
   - cl_dockets, cl_opinions, cl_clusters, cl_docket_entries
   - Comprehensive PACER/RECAP support
   - Not actively used by current API

4. **`court_data.cl_recap_documents`** - RECAP document support (add_recap_schema.sql)
   - Transcript detection and audio support
   - Not actively used by current API

5. **`court_data.opinions_unified`** - Unified table (create_unified_opinions_table.sql)
   - Attempt to consolidate all sources
   - Not actively used by current API

### Document Types

**CourtListener Opinion Types** (found in metadata):
- `010combined` - Combined opinion
- `020lead` - Lead opinion (main opinion of the court)
- `030concurrence` - Concurring opinion
- `040dissent` - Dissenting opinion

The `020lead` type contains the main court opinions with substantial legal text (50KB+).

## Current Status

### Data Quality Metrics
- **Total Documents**: 485
- **Judge Attribution**: 55.9% (target: >95%)
- **Docket Numbers**: 9.5% (target: >90%)
- **Court IDs**: 33.6% (target: 100%)
- **Text Content**: 94.8% (target: >95%)

### Top Courts
- txed: 72 documents (E.D. Texas)
- ded: 44 documents (D. Delaware)
- mdd: 16 documents (D. Maryland)

## Access Methods

### 1. Simplified API (Port 8104)

**Base URL**: `http://localhost:8104`

**Endpoints**:
```bash
GET /                     # Health check
GET /text/{id}           # Get plain text directly
GET /documents/{id}      # Get full document with metadata
GET /search              # Search with filters (judge, type, min_length)
GET /list                # List documents
GET /bulk/judge/{name}   # Bulk retrieve by judge
```

**Example Usage**:
```bash
# Get document text
curl http://localhost:8104/text/420

# Search for Judge Gilstrap's 020lead opinions
curl "http://localhost:8104/search?judge=Gilstrap&type=020lead&limit=10"

# List recent documents
curl "http://localhost:8104/list?limit=5"
```

### 2. CLI Tool (court_processor)

**Must run inside Docker container** or with proper DATABASE_URL set.

**Main Commands**:
```bash
# Data Management
./court_processor data status              # Check data quality
./court_processor data list --type all     # List documents
./court_processor data export              # Export with various filters
./court_processor data fix                 # Fix quality issues

# Analysis
./court_processor analyze judge "Rodney Gilstrap"

# Collection
./court_processor collect court txed --years 2020-2025

# Pipeline Processing
./court_processor pipeline run --limit 50
```

**Export Examples**:
```bash
# Export Judge Gilstrap's substantial opinions
docker exec aletheia_development-court-processor-1 ./court_processor data export \
  --judge "Gilstrap" \
  --type 020lead \
  --min-content-length 50000 \
  --format json \
  --full-content

# Export all opinions as CSV
docker exec aletheia_development-court-processor-1 ./court_processor data export \
  --type opinion \
  --format csv \
  --output opinions.csv
```

## Key Issues

### 1. Database Schema Fragmentation
- **5+ different schemas** exist but only `public.court_documents` is actively used
- No clear migration path between schemas
- Metadata stored as JSONB makes querying inconsistent

### 2. Document Type Confusion
- CourtListener types (010combined, 020lead, etc.) mixed with generic types (opinion, order)
- No clear documentation on what each type represents
- Type detection happens at multiple levels (pipeline, API)

### 3. Missing Integration Points
- Database connection defaults don't match Docker networking
- API can't connect to DB without proper Docker setup
- CLI requires Docker execution but documentation suggests local usage

### 4. Data Quality Issues
- Low judge attribution (55.9%)
- Missing docket numbers (90.5% missing)
- Inconsistent court IDs

## Recommendations

### Immediate Actions
1. **Choose ONE primary schema** and migrate all data to it
2. **Document the chosen schema** clearly with field descriptions
3. **Fix database connection strings** to work both in Docker and locally
4. **Create data dictionary** for document types

### Schema Consolidation Strategy
Recommend using `court_data.opinions_unified` as the target schema because:
- It combines CourtListener and juriscraper fields
- Has proper indexing for search
- Supports FLP enhancements
- Uses JSONB for flexibility

### Migration Path
1. Export current data from `public.court_documents`
2. Transform to unified schema format
3. Import into `court_data.opinions_unified`
4. Update API to use new schema
5. Archive old schemas

## Environment Configuration

Required environment variables:
```bash
DATABASE_URL=postgresql://aletheia:aletheia123@db:5432/aletheia  # Docker
DATABASE_URL=postgresql://aletheia:aletheia123@localhost:8200/aletheia  # Local

COURTLISTENER_API_TOKEN=your-token  # For data collection
COURT_PROCESSOR_PORT=8104           # API port
```

## Docker Services

The court-processor runs as part of the Aletheia stack:
- Container: `aletheia_development-court-processor-1`
- Port: 8104
- Health check: `/` endpoint
- Auto-starts simplified_api.py on container launch

## Summary

The court-processor has solid functionality but suffers from:
1. **Schema sprawl** - too many database schemas, only one actively used
2. **Poor documentation** - document types and schemas undocumented
3. **Integration issues** - database connections problematic between Docker/local

The system works but needs consolidation to be maintainable by future developers.