# Database Schema

This document describes the PostgreSQL database schema used by Aletheia v0.1.

## Overview

Aletheia uses PostgreSQL as its primary data store with multiple schemas for different components:

- **`public`** - Default PostgreSQL schema (currently unused)
- **`court_data`** - Court opinion processing and storage (11 tables)

## Quick Access

```bash
# Access database shell
./dev db shell

# List all tables
\\dt court_data.*

# Describe a table
\\d court_data.opinions_unified
```

## Court Data Schema

The `court_data` schema contains tables for managing court opinions and judicial data.

### Main Tables

| Table Name | Purpose | Row Count* |
|------------|---------|------------|
| `opinions_unified` | Unified court opinions with full text | Primary data |
| `cl_opinions` | CourtListener opinions | Source data |
| `cl_dockets` | CourtListener docket information | Metadata |
| `cl_docket_entries` | Individual docket entries | Details |
| `judges` | Judge information | Reference |
| `judge_aliases` | Alternative judge names | Normalization |
| `courts_reference` | Court metadata | Reference |
| `cl_clusters` | Opinion clusters | Grouping |
| `normalized_reporters` | Reporter citations | Reference |
| `processed_documents_flp` | Processing status | Tracking |
| `transcript_opinions` | Transcript data | Alternative format |

*Note: Row counts vary based on data imports

### Key Tables Detail

#### `judges`

Stores information about judges in the court system.

| Column | Type | Constraints | Default | Description |
|--------|------|-------------|---------|-------------|
| `id` | integer | PRIMARY KEY | auto-increment | Unique identifier |
| `name` | varchar(255) | NOT NULL, UNIQUE | - | Judge's full name |
| `court` | varchar(100) | - | - | Court affiliation |
| `created_at` | timestamp | - | CURRENT_TIMESTAMP | Record creation time |
| `updated_at` | timestamp | - | CURRENT_TIMESTAMP | Last update time |

**Indexes:**
- Primary key on `id`
- Unique constraint on `name`
- B-tree index on `name`, `court`

#### `opinions_unified`

Primary table for unified court opinions with full text and metadata.

| Column | Type | Constraints | Default | Description |
|--------|------|-------------|---------|-------------|
| `id` | integer | PRIMARY KEY | auto-increment | Unique identifier |
| `cl_id` | integer | - | - | CourtListener ID reference |
| `court_id` | varchar(15) | - | - | Court identifier code |
| `docket_number` | varchar(500) | - | - | Court docket number |
| `case_name` | text | - | - | Name of the case |
| `date_filed` | date | - | - | Date opinion was filed |
| `author_str` | varchar(200) | - | - | Author judge name |
| `per_curiam` | boolean | - | false | Per curiam opinion flag |
| `type` | varchar(20) | - | - | Opinion type |
| `plain_text` | text | - | - | Full text content |
| `html` | text | - | - | HTML formatted content |
| `pdf_url` | text | - | - | URL to PDF document |
| `citations` | jsonb | - | '[]' | Citation references |
| `judge_info` | jsonb | - | '{}' | Judge metadata |
| `court_info` | jsonb | - | '{}' | Court metadata |
| `structured_elements` | jsonb | - | '{}' | Parsed document structure |
| `document_hash` | varchar(64) | NOT NULL | - | Document uniqueness hash |
| `pdf_metadata` | jsonb | - | '{}' | PDF-specific metadata |
| `processing_status` | varchar(50) | - | 'completed' | Processing status |
| `processing_error` | text | - | - | Error details if any |
| `vector_indexed` | boolean | - | false | Vector indexing status |
| `hierarchical_doc_id` | integer | - | - | Hierarchical document reference |
| `scraped_at` | timestamp | - | CURRENT_TIMESTAMP | Scraping timestamp |
| `created_at` | timestamp | - | CURRENT_TIMESTAMP | Record creation time |
| `updated_at` | timestamp | - | CURRENT_TIMESTAMP | Last update time |

**Indexes:**
- Primary key on `id`
- Unique constraint on `(court_code, docket_number, case_date)`
- Foreign key to `judges(id)`
- B-tree indexes on `court_code`, `case_date`, `docket_number`, `judge_id`
- GIN index for full-text search on `text_content`
- Partial index on `vector_indexed` for unprocessed documents

#### `processing_log`

Tracks court opinion processing runs and statistics.

| Column | Type | Constraints | Default | Description |
|--------|------|-------------|---------|-------------|
| `id` | integer | PRIMARY KEY | auto-increment | Unique identifier |
| `court_code` | varchar(50) | - | - | Court being processed |
| `run_date` | date | - | - | Date of processing run |
| `opinions_found` | integer | - | 0 | Number of opinions found |
| `opinions_processed` | integer | - | 0 | Number processed successfully |
| `errors_count` | integer | - | 0 | Number of errors |
| `error_details` | jsonb | - | - | Detailed error information |
| `started_at` | timestamp | - | CURRENT_TIMESTAMP | Processing start time |
| `completed_at` | timestamp | - | - | Processing completion time |
| `status` | varchar(50) | - | 'running' | Current status |

### Views

#### `judge_stats`

Provides aggregated statistics for each judge.

```sql
CREATE VIEW court_data.judge_stats AS
SELECT 
    j.id,
    j.name,
    j.court,
    count(o.id) AS opinion_count,
    min(o.case_date) AS earliest_opinion,
    max(o.case_date) AS latest_opinion,
    count(o.id) FILTER (WHERE o.vector_indexed = false) AS pending_indexing
FROM court_data.judges j
LEFT JOIN court_data.opinions o ON j.id = o.judge_id
GROUP BY j.id, j.name, j.court;
```

### Functions

#### `get_or_create_judge(name, court)`

Retrieves an existing judge ID or creates a new judge record.

**Parameters:**
- `p_judge_name` (varchar) - Name of the judge
- `p_court` (varchar) - Court affiliation

**Returns:** integer - Judge ID

#### `update_updated_at_column()`

Trigger function that automatically updates the `updated_at` timestamp on row modification.

### Sequences

| Sequence | Table | Column |
|----------|-------|---------|
| `judges_id_seq` | judges | id |
| `opinions_id_seq` | opinions | id |
| `processing_log_id_seq` | processing_log | id |

## Usage Examples

### Query Opinions by Judge

```sql
SELECT o.* 
FROM court_data.opinions o
JOIN court_data.judges j ON o.judge_id = j.id
WHERE j.name = 'Judge Smith'
ORDER BY o.case_date DESC;
```

### Find Unprocessed Documents

```sql
SELECT * FROM court_data.opinions
WHERE vector_indexed = false
LIMIT 100;
```

### Full-Text Search

```sql
SELECT * FROM court_data.opinions
WHERE to_tsvector('english', text_content) @@ plainto_tsquery('constitutional rights');
```

### Get Judge Statistics

```sql
SELECT * FROM court_data.judge_stats
ORDER BY opinion_count DESC
LIMIT 20;
```

## Database Initialization

To initialize the court data schema:

```bash
# Using the court processor
docker-compose exec court-processor python processor.py --init-db

# Or directly via SQL
docker-compose exec db psql -U your_db_user -d your_db_name -f /court-processor/scripts/init_db.sql
```

## Migration Strategy

When updating the schema:

1. Create migration scripts in `court-processor/scripts/migrations/`
2. Version migrations with timestamps (e.g., `202501_add_column.sql`)
3. Test migrations in development before production
4. Always backup before running migrations

## Performance Considerations

1. **Indexes**: The schema includes comprehensive indexes for common query patterns
2. **JSONB Storage**: Flexible metadata storage without schema rigidity
3. **Full-Text Search**: GIN indexes enable efficient text searching
4. **Partial Indexes**: Optimize queries for unprocessed documents

## Security

- All database credentials are stored in environment variables
- Application uses least-privilege database user
- No direct external database access
- Prepared statements prevent SQL injection

## Future Enhancements

- [ ] Partitioning for large opinion tables
- [ ] Read replicas for search operations
- [ ] Connection pooling optimization
- [ ] Automated backup procedures