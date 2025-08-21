#!/bin/bash

# Restore court documents database backup
# Usage: ./restore_court_documents.sh

set -e

echo "Court Documents Database Restore Script"
echo "======================================="

# Check if backup file exists
if [ ! -f "court_documents_complete.sql.gz" ]; then
    echo "Error: court_documents_complete.sql.gz not found!"
    echo "Please ensure the backup file is in the current directory."
    exit 1
fi

# Decompress the backup
echo "Decompressing backup..."
gunzip -k court_documents_complete.sql.gz

# Get database credentials from .env or use defaults
DB_USER=${DB_USER:-aletheia}
DB_NAME=${DB_NAME:-aletheia}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-8200}

echo "Database configuration:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"

# Check if running in Docker or locally
if [ -f /.dockerenv ]; then
    # Inside Docker
    psql -U $DB_USER -d $DB_NAME -f court_documents_complete.sql
else
    # On host machine - use Docker exec
    if docker ps | grep -q aletheia_development-db-1; then
        echo "Restoring via Docker container..."
        docker exec -i aletheia_development-db-1 psql -U $DB_USER -d $DB_NAME < court_documents_complete.sql
    else
        echo "Restoring to local PostgreSQL..."
        psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f court_documents_complete.sql
    fi
fi

# Clean up decompressed file
rm court_documents_complete.sql

echo "Restore complete!"
echo "Verifying restore..."

# Verify the restore
if [ -f /.dockerenv ]; then
    COUNT=$(psql -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM court_documents;")
else
    if docker ps | grep -q aletheia_development-db-1; then
        COUNT=$(docker exec aletheia_development-db-1 psql -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM court_documents;")
    else
        COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM court_documents;")
    fi
fi

echo "Total documents restored: $COUNT"