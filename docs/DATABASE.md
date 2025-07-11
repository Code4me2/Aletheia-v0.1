# Database Schema

This document describes the PostgreSQL database schema used by Aletheia v0.1.

## Overview

Aletheia uses PostgreSQL as its primary data store with multiple schemas for different components:

- **`public`** - Default PostgreSQL schema (currently unused)
- **`court_data`** - Court opinion processing and storage

## Court Data Schema

The `court_data` schema contains tables for managing court opinions and judicial data.

### Tables

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

#### `opinions`

Stores court opinions with full text content and metadata.

| Column | Type | Constraints | Default | Description |
|--------|------|-------------|---------|-------------|
| `id` | integer | PRIMARY KEY | auto-increment | Unique identifier |
| `judge_id` | integer | FOREIGN KEY | - | References `judges.id` |
| `case_name` | text | - | - | Name of the case |
| `case_date` | date | NOT NULL | - | Date of the court decision |
| `docket_number` | varchar(100) | - | - | Court docket number |
| `court_code` | varchar(50) | - | - | Court identifier code |
| `pdf_url` | text | - | - | URL to the PDF document |
| `pdf_path` | varchar(500) | - | - | Local path to stored PDF |
| `text_content` | text | NOT NULL | - | Full text content |
| `metadata` | jsonb | - | '{}' | Additional metadata |
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