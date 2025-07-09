#!/bin/bash
set -e

echo "=== Safe Container Migration Script ==="
echo ""

# Function to backup data before migration
backup_data() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_dir="backups/migration_${timestamp}"
    
    echo "Creating backup directory: $backup_dir"
    mkdir -p "$backup_dir"
    
    # Backup n8n workflows
    echo "Backing up n8n data..."
    if docker ps | grep -q "n8n"; then
        docker exec $(docker ps -q -f name=n8n) sh -c 'cd /home/node/.n8n && tar czf - .' > "$backup_dir/n8n_backup.tar.gz" || echo "Warning: n8n backup failed"
    fi
    
    # Backup database
    echo "Backing up PostgreSQL database..."
    if docker ps | grep -q "db"; then
        docker exec $(docker ps -q -f name=db) pg_dumpall -U ${DB_USER:-your_db_user} > "$backup_dir/postgres_backup.sql" || echo "Warning: Database backup failed"
    fi
    
    # List local files that are already preserved
    echo ""
    echo "Local files already preserved:"
    echo "- Court PDFs: ./court-data/pdfs ($(find ./court-data/pdfs -type f 2>/dev/null | wc -l) files)"
    echo "- Court Logs: ./court-data/logs ($(find ./court-data/logs -type f 2>/dev/null | wc -l) files)"
    echo "- n8n Local Files: ./n8n/local-files ($(find ./n8n/local-files -type f 2>/dev/null | wc -l) files)"
    
    echo ""
    echo "Backup completed in: $backup_dir"
}

# Function to verify volume data
verify_volumes() {
    echo ""
    echo "Verifying Docker volumes..."
    
    for volume in postgres_data n8n_data; do
        if docker volume inspect "aletheia-v01_${volume}" &>/dev/null; then
            echo "✓ Found volume: aletheia-v01_${volume}"
            size=$(docker run --rm -v "aletheia-v01_${volume}:/data" alpine du -sh /data 2>/dev/null | awk '{print $1}')
            echo "  Size: ${size:-unknown}"
        fi
        
        if docker volume inspect "aletheia_${volume}" &>/dev/null; then
            echo "✓ Found volume: aletheia_${volume}"
            size=$(docker run --rm -v "aletheia_${volume}:/data" alpine du -sh /data 2>/dev/null | awk '{print $1}')
            echo "  Size: ${size:-unknown}"
        fi
    done
}

# Function to migrate volumes if needed
migrate_volumes() {
    echo ""
    echo "Checking if volume migration is needed..."
    
    # Check if we need to migrate from old volume names to new ones
    for volume in postgres_data n8n_data; do
        old_volume="aletheia-v01_${volume}"
        new_volume="aletheia_${volume}"
        
        if docker volume inspect "$old_volume" &>/dev/null && ! docker volume inspect "$new_volume" &>/dev/null; then
            echo "Migrating volume: $old_volume → $new_volume"
            docker volume create "$new_volume"
            docker run --rm -v "$old_volume:/source" -v "$new_volume:/dest" alpine sh -c "cp -av /source/* /dest/"
            echo "✓ Migration complete for $volume"
        elif docker volume inspect "$old_volume" &>/dev/null && docker volume inspect "$new_volume" &>/dev/null; then
            echo "⚠️  Both $old_volume and $new_volume exist. Using existing $new_volume"
        fi
    done
}

# Function to stop containers safely
stop_containers_safely() {
    echo ""
    echo "Stopping containers safely..."
    
    # Stop containers but don't remove them yet
    docker-compose stop
    
    # List what will be preserved
    echo ""
    echo "The following data will be preserved:"
    echo "✓ PostgreSQL database (in Docker volume)"
    echo "✓ n8n workflows and credentials (in Docker volume)"
    echo "✓ Court PDFs and logs (in local directories)"
    echo "✓ n8n local files (in local directory)"
}

# Main execution
echo "This script will safely migrate containers while preserving all data."
echo ""
read -p "Do you want to create a backup first? (recommended) [Y/n]: " backup_choice

if [[ "$backup_choice" != "n" ]] && [[ "$backup_choice" != "N" ]]; then
    backup_data
fi

verify_volumes
migrate_volumes
stop_containers_safely

echo ""
echo "=== Next Steps ==="
echo "1. Review the volume information above"
echo "2. Run 'docker-compose up -d' to start with new container names"
echo "3. Verify all data is intact"
echo ""
echo "To manually inspect volumes:"
echo "  docker run --rm -v aletheia_postgres_data:/data alpine ls -la /data"
echo "  docker run --rm -v aletheia_n8n_data:/data alpine ls -la /data"
echo ""
echo "To restore from backup if needed:"
echo "  See backups/ directory for recovery files"