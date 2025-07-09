# PostgreSQL Database Schema Report - Aletheia v0.1

## Database Overview
- **Database Name**: your_db_name
- **Database User**: your_db_user
- **Primary Schema**: court_data
- **Date Generated**: 2025-07-08

## Schema Summary
The database contains two schemas:
1. **court_data** - Contains all application tables, views, and functions
2. **public** - Empty (no tables)

## Tables in court_data Schema

### 1. judges
Stores information about judges in the court system.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NOT NULL | nextval('court_data.judges_id_seq') | Primary key |
| name | varchar(255) | NOT NULL | - | Judge's full name |
| court | varchar(100) | NULL | - | Court affiliation |
| created_at | timestamp | NULL | CURRENT_TIMESTAMP | Record creation time |
| updated_at | timestamp | NULL | CURRENT_TIMESTAMP | Last update time |

**Indexes:**
- `judges_pkey` - PRIMARY KEY on (id)
- `judges_name_key` - UNIQUE CONSTRAINT on (name)
- `idx_judges_name` - B-tree index on (name)
- `idx_judges_court` - B-tree index on (court)

**Triggers:**
- `update_judges_updated_at` - Updates the updated_at timestamp on row modification

**Referenced by:**
- `opinions.judge_id` via foreign key constraint

### 2. opinions
Stores court opinions with full text content and metadata.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NOT NULL | nextval('court_data.opinions_id_seq') | Primary key |
| judge_id | integer | NULL | - | Foreign key to judges table |
| case_name | text | NULL | - | Name of the case |
| case_date | date | NOT NULL | - | Date of the court decision |
| docket_number | varchar(100) | NULL | - | Court docket number |
| court_code | varchar(50) | NULL | - | Court identifier code |
| pdf_url | text | NULL | - | URL to the PDF document |
| pdf_path | varchar(500) | NULL | - | Local path to stored PDF |
| text_content | text | NOT NULL | - | Full text content of the opinion |
| metadata | jsonb | NULL | '{}' | Additional metadata in JSON format |
| pdf_metadata | jsonb | NULL | '{}' | PDF-specific metadata |
| processing_status | varchar(50) | NULL | 'completed' | Current processing status |
| processing_error | text | NULL | - | Error details if processing failed |
| vector_indexed | boolean | NULL | false | Whether vector indexing is complete |
| hierarchical_doc_id | integer | NULL | - | ID for hierarchical document processing |
| scraped_at | timestamp | NULL | CURRENT_TIMESTAMP | When the opinion was scraped |
| created_at | timestamp | NULL | CURRENT_TIMESTAMP | Record creation time |
| updated_at | timestamp | NULL | CURRENT_TIMESTAMP | Last update time |

**Indexes:**
- `opinions_pkey` - PRIMARY KEY on (id)
- `unique_opinion` - UNIQUE CONSTRAINT on (court_code, docket_number, case_date)
- `idx_opinions_court` - B-tree index on (court_code)
- `idx_opinions_date` - B-tree index on (case_date DESC)
- `idx_opinions_docket` - B-tree index on (docket_number)
- `idx_opinions_judge_date` - Composite B-tree index on (judge_id, case_date DESC)
- `idx_opinions_text_search` - GIN index for full-text search on text_content
- `idx_opinions_vector` - Partial B-tree index on (vector_indexed) WHERE vector_indexed = false

**Foreign Keys:**
- `opinions_judge_id_fkey` - References court_data.judges(id)

**Triggers:**
- `update_opinions_updated_at` - Updates the updated_at timestamp on row modification

### 3. processing_log
Tracks court opinion processing runs and statistics.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NOT NULL | nextval('court_data.processing_log_id_seq') | Primary key |
| court_code | varchar(50) | NULL | - | Court being processed |
| run_date | date | NULL | - | Date of processing run |
| opinions_found | integer | NULL | 0 | Number of opinions discovered |
| opinions_processed | integer | NULL | 0 | Number successfully processed |
| errors_count | integer | NULL | 0 | Number of errors encountered |
| error_details | jsonb | NULL | - | Detailed error information in JSON |
| started_at | timestamp | NULL | CURRENT_TIMESTAMP | Processing start time |
| completed_at | timestamp | NULL | - | Processing completion time |
| status | varchar(50) | NULL | 'running' | Current status of the run |

**Indexes:**
- `processing_log_pkey` - PRIMARY KEY on (id)

## Views

### court_data.judge_stats
Aggregated statistics for each judge including opinion counts and indexing status.

**Columns:**
- `id` - Judge ID
- `name` - Judge name
- `court` - Court affiliation
- `opinion_count` - Total number of opinions
- `earliest_opinion` - Date of earliest opinion
- `latest_opinion` - Date of most recent opinion
- `pending_indexing` - Count of opinions pending vector indexing

**View Definition:**
```sql
SELECT j.id,
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

## Functions

### 1. court_data.get_or_create_judge
Retrieves an existing judge ID or creates a new judge record if not found.

**Parameters:**
- `p_judge_name` varchar - Name of the judge
- `p_court` varchar - Court affiliation

**Returns:** integer - Judge ID

**Logic:**
1. Searches for existing judge by name
2. If not found, creates new judge record
3. Uses ON CONFLICT to handle race conditions
4. Returns the judge ID

### 2. court_data.update_updated_at_column
Trigger function that automatically updates the `updated_at` timestamp.

**Type:** Trigger function
**Returns:** trigger

**Usage:**
Applied to both `judges` and `opinions` tables to maintain accurate update timestamps.

## Sequences

| Schema | Sequence Name | Table | Column |
|--------|---------------|--------|---------|
| court_data | judges_id_seq | judges | id |
| court_data | opinions_id_seq | opinions | id |
| court_data | processing_log_id_seq | processing_log | id |

## Key Features

### 1. Text Search Capability
The `opinions` table includes a GIN index on `text_content` for efficient full-text search using PostgreSQL's built-in text search capabilities.

### 2. Vector Indexing Support
The schema includes support for vector indexing with:
- `vector_indexed` boolean flag
- Partial index to quickly find un-indexed documents
- `hierarchical_doc_id` for document hierarchy processing

### 3. JSON Metadata Storage
Both `opinions` and `processing_log` tables use JSONB columns for flexible metadata storage:
- `metadata` - General metadata
- `pdf_metadata` - PDF-specific information
- `error_details` - Structured error logging

### 4. Automatic Timestamps
All main tables include automatic timestamp management:
- `created_at` - Set on insert
- `updated_at` - Updated via trigger on any modification

### 5. Data Integrity
- Unique constraint on opinions prevents duplicate entries
- Foreign key constraint maintains referential integrity between judges and opinions
- NOT NULL constraints on critical fields ensure data quality

## Performance Considerations

1. **Indexes for Common Queries:**
   - Judge lookups by name or court
   - Opinion searches by date, court, or docket number
   - Full-text search on opinion content
   - Efficient filtering of un-indexed documents

2. **Composite Indexes:**
   - `idx_opinions_judge_date` optimizes queries filtering by judge and date range

3. **Partial Indexes:**
   - `idx_opinions_vector` efficiently identifies documents pending vector indexing

## Schema Design Patterns

1. **Soft Updates:** Using `updated_at` triggers for audit trails
2. **JSON Flexibility:** JSONB columns for evolving metadata requirements
3. **Status Tracking:** Processing status fields for workflow management
4. **Error Handling:** Structured error logging in processing_log table
5. **Unique Constraints:** Natural keys prevent duplicate data entry