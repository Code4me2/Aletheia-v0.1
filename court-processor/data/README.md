# Court Processor Sample Data

This directory contains a backup of 485 court documents for development and testing.

## Contents

- **court_documents_backup.sql.gz** - Compressed SQL backup (3.1MB compressed, 11MB uncompressed)
  - 485 court documents from public.court_documents table
  - Document types: opinion (273), 020lead (210), opinion_doctor (2)
  - Date range: 1996-05-02 to 2025-07-22
  - Largest document: 119,432 characters

## Restoration

### Quick Restore (Recommended)
```bash
./dev db restore-court-data
```

### Manual Restore
```bash
# From project root
gunzip -c court-processor/data/court_documents_backup.sql.gz | \
  docker exec -i aletheia_development-db-1 psql -U aletheia -d aletheia
```

### Alternative Script
```bash
# From court-processor/data/
./restore_data.sh
```

## Data Statistics

- **Total Size**: ~9.5MB of text content
- **Average Document**: ~20KB
- **Documents > 50K chars**: 19
- **Top Courts**: txed (72), ded (44), mdd (16)

## Integration with Setup

The `./dev up` command automatically restores this data when:
- Starting services for the first time (empty database)
- The backup file is present
- The database becomes ready

This ensures new users immediately have sample data available.

## Creating a New Backup

To update this backup with current database content:

```bash
# Export current data
docker exec aletheia_development-db-1 pg_dump -U aletheia -d aletheia \
  -t public.court_documents --data-only --inserts > \
  court-processor/data/court_documents_backup.sql

# Compress it
gzip -f court-processor/data/court_documents_backup.sql
```

## Notes

- This data is for development/testing only
- Contains public court opinions from CourtListener
- No sensitive or private information included