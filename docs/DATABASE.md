# Database Schema

This document describes the PostgreSQL database schema used by Aletheia.

## Overview

Aletheia uses PostgreSQL as its primary data store. The court-processor service uses a simplified single-table design:

- **`public.court_documents`** - Main table for all court documents (485 documents as of Aug 2025)

## Quick Access

```bash
# Access database shell
./dev db shell

# View court_documents table structure
\d public.court_documents

# Count documents
SELECT COUNT(*) FROM public.court_documents;

# View document types
SELECT DISTINCT document_type FROM public.court_documents;
```

## Active Schema

### `public.court_documents`

The primary table used by the court-processor API and CLI.

| Column | Type | Constraints | Default | Description |
|--------|------|-------------|---------|-------------|
| `id` | integer | PRIMARY KEY | auto-increment | Unique identifier |
| `case_number` | varchar(255) | - | - | Case identifier (e.g., "2:17-CV-00141-JRG") |
| `document_type` | varchar(100) | - | - | Type: 'opinion', '020lead', 'opinion_doctor', 'docket' |
| `file_path` | text | - | - | Path to original file (if applicable) |
| `content` | text | - | - | Full document content (HTML/XML format) |
| `metadata` | jsonb | - | - | Flexible metadata storage |
| `processed` | boolean | - | false | Processing status flag |
| `created_at` | timestamp | - | CURRENT_TIMESTAMP | Record creation time |
| `updated_at` | timestamp | - | CURRENT_TIMESTAMP | Last update time |
| `case_name` | varchar(500) | - | - | Human-readable case name |

**Indexes:**
- Primary key on `id`
- B-tree index on `case_number`
- B-tree index on `document_type`
- B-tree index on `processed`
- GIN index on `metadata` for JSONB queries

### Document Types

| Type | Description | Count* |
|------|-------------|--------|
| `opinion` | Generic court opinion | 273 |
| `020lead` | CourtListener lead opinion (main opinion of the court) | 210 |
| `opinion_doctor` | Enhanced/processed opinion | 2 |
| `docket` | Docket entry | 0 |

*Counts as of August 2025

### Metadata Structure

The `metadata` JSONB field typically contains:

```json
{
  "judge_name": "Rodney Gilstrap",
  "court_id": "txed",
  "date_filed": "2019-06-14",
  "cl_opinion_id": "1967",
  "cl_cluster_id": 7336453,
  "citations": ["767 F.3d 1308", "664 F.3d 467"],
  "source": "courtlistener_standalone",
  "type": "020lead"
}
```

## Usage Examples

### Query by Judge

```sql
SELECT * FROM public.court_documents
WHERE metadata->>'judge_name' = 'Gilstrap'
ORDER BY (metadata->>'date_filed')::date DESC;
```

### Find Long Documents

```sql
SELECT id, case_number, LENGTH(content) as content_length
FROM public.court_documents
WHERE document_type = '020lead'
AND LENGTH(content) > 50000
ORDER BY LENGTH(content) DESC;
```

### Get Document Statistics

```sql
SELECT 
  document_type,
  COUNT(*) as count,
  AVG(LENGTH(content)) as avg_length,
  MAX(LENGTH(content)) as max_length
FROM public.court_documents
GROUP BY document_type;
```

### Search by Court

```sql
SELECT * FROM public.court_documents
WHERE metadata->>'court_id' = 'txed'
LIMIT 10;
```

## API Access

The court-processor API provides REST endpoints for this data:

```bash
# Get document text
curl http://localhost:8104/text/420

# Search documents
curl "http://localhost:8104/search?judge=Gilstrap&type=020lead"

# List documents
curl http://localhost:8104/list
```

## Data Statistics (August 2025)

- **Total Documents**: 485
- **Document Types**: opinion (273), 020lead (210), opinion_doctor (2)
- **Top Courts**: txed (72), ded (44), mdd (16)
- **Date Range**: 1996-05-02 to 2025-07-22
- **Largest Document**: 119,432 characters
- **Documents > 50K chars**: 19

## Archived Schemas

Multiple legacy schemas exist but are NOT in active use:

- `court_data.opinions` - Original design (archived)
- `court_data.cl_*` tables - CourtListener integration (never populated)
- `court_data.opinions_unified` - Unification attempt (partial data)

These schemas are preserved in `court-processor/archived/database_schemas/` for reference but should not be used for new development.

## Performance Considerations

1. **Single Table Design**: Simplified queries and maintenance
2. **JSONB Metadata**: Flexible storage without schema changes
3. **Indexed Lookups**: Fast queries on case_number and document_type
4. **Text Storage**: Efficient for documents up to 120KB+

## Security

- Database credentials stored in environment variables
- Application uses least-privilege database user
- No direct external database access
- Prepared statements prevent SQL injection

## Future Considerations

The current simple schema works well for 485 documents but may need enhancement for scale:

- [ ] Full-text search indexes for content field
- [ ] Partitioning if document count exceeds 100K
- [ ] Separate metadata tables if JSONB queries become slow
- [ ] Migration to `court_data.opinions_unified` if consolidation needed

## Connection Details

```bash
# From Docker containers
postgresql://aletheia:aletheia123@db:5432/aletheia

# From host machine
postgresql://aletheia:aletheia123@localhost:8200/aletheia
```