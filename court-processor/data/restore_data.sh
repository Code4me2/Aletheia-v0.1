#!/bin/bash

# Court Processor Data Restoration Script
# This script restores the court documents data into the database

set -e

echo "🔄 Restoring court processor data..."

# Check if we're in Docker or on host
if [ -f /.dockerenv ]; then
    # Inside Docker
    DB_HOST="db"
    DB_PORT="5432"
else
    # On host machine
    DB_HOST="localhost"
    DB_PORT="${POSTGRES_PORT:-8200}"
fi

DB_USER="${DB_USER:-aletheia}"
DB_NAME="${DB_NAME:-aletheia}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if backup file exists
if [ ! -f "$SCRIPT_DIR/court_documents_backup.sql.gz" ]; then
    echo "❌ Backup file not found: $SCRIPT_DIR/court_documents_backup.sql.gz"
    exit 1
fi

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
for i in {1..30}; do
    if PGPASSWORD="${DB_PASSWORD:-aletheia123}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" >/dev/null 2>&1; then
        echo "✅ Database is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Database connection timeout"
        exit 1
    fi
    sleep 1
done

# Check if table exists and has data
EXISTING_COUNT=$(PGPASSWORD="${DB_PASSWORD:-aletheia123}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM public.court_documents" 2>/dev/null || echo "0")
EXISTING_COUNT=$(echo $EXISTING_COUNT | tr -d ' ')

if [ "$EXISTING_COUNT" -gt "0" ]; then
    echo "⚠️  Table already contains $EXISTING_COUNT documents"
    read -p "Do you want to replace existing data? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping data restoration"
        exit 0
    fi
    echo "🗑️  Clearing existing data..."
    PGPASSWORD="${DB_PASSWORD:-aletheia123}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "TRUNCATE TABLE public.court_documents RESTART IDENTITY CASCADE;"
fi

# Restore the data
echo "📥 Importing court documents data..."
gunzip -c "$SCRIPT_DIR/court_documents_backup.sql.gz" | PGPASSWORD="${DB_PASSWORD:-aletheia123}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"

# Verify restoration
NEW_COUNT=$(PGPASSWORD="${DB_PASSWORD:-aletheia123}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM public.court_documents")
NEW_COUNT=$(echo $NEW_COUNT | tr -d ' ')

echo "✅ Successfully restored $NEW_COUNT court documents"
echo "📊 Document types:"
PGPASSWORD="${DB_PASSWORD:-aletheia123}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT document_type, COUNT(*) as count FROM public.court_documents GROUP BY document_type ORDER BY count DESC;"