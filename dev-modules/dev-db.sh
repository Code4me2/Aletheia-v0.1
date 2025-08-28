#!/bin/bash

# ============================================================================
# Dev CLI Database Module
# ============================================================================
# This module contains commands for managing the PostgreSQL database

# Handle database commands
handle_db_command() {
    local cmd="$1"
    shift
    
    case "$cmd" in
        schema)
            db_schema "$@"
            ;;
        shell)
            db_shell "$@"
            ;;
        backup)
            db_backup "$@"
            ;;
        restore)
            db_restore "$@"
            ;;
        restore-court-data)
            db_restore_court_data "$@"
            ;;
        *)
            if [ "$OUTPUT_FORMAT" = "json" ]; then
                echo '{"status":"error","message":"Unknown database command"}'
            else
                echo "Usage: ./dev db [schema|shell|backup|restore|restore-court-data]"
                echo "  schema [--detailed]  - Show database schema"
                echo "  shell               - Open PostgreSQL shell"
                echo "  backup              - Create database backup"
                echo "  restore <file>      - Restore from backup"
                echo "  restore-court-data  - Restore court processor sample data"
            fi
            return $EXIT_CONFIG_ERROR
            ;;
    esac
}

# Show database schema
db_schema() {
    local detailed="$1"
    
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        if ! check_service_running "db" true; then
            echo '{"status":"error","message":"Database is not running"}'
            return $EXIT_SERVICE_UNAVAILABLE
        fi
        
        # Get table count
        table_count=$($DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -t -c \
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'" 2>/dev/null | tr -d ' ')
        
        echo "{\"status\":\"success\",\"tables\":$table_count}"
    else
        print_header "Database Schema"
        
        if ! check_service_running "db"; then
            return $EXIT_SERVICE_UNAVAILABLE
        fi
        
        echo -e "${CYAN}Schemas:${NC}"
        $DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -c "\\dn" 2>/dev/null
        
        echo -e "${CYAN}Tables in court_data schema:${NC}"
        $DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -c "\\dt court_data.*" 2>/dev/null
        
        if [ "$detailed" = "--detailed" ]; then
            echo ""
            echo -e "${CYAN}Table structures:${NC}"
            for table in opinions_unified judges cl_opinions cl_dockets; do
                echo ""
                echo -e "${YELLOW}Table: court_data.$table${NC}"
                $DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -c "\\d court_data.$table" 2>/dev/null | head -20
            done
        fi
    fi
}

# Open database shell
db_shell() {
    check_requirements
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        echo '{"status":"error","message":"Shell mode not available in JSON output"}'
        return $EXIT_CONFIG_ERROR
    fi
    
    echo -e "${BLUE}Opening database shell...${NC}"
    $DOCKER_COMPOSE exec db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}"
}

# Create database backup
db_backup() {
    check_requirements
    
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_dir="backups"
    mkdir -p "$backup_dir"
    
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        if $DOCKER_COMPOSE exec -T db pg_dump -U "${DB_USER:-aletheia}" "${DB_NAME:-aletheia}" > "$backup_dir/db_backup_${timestamp}.sql" 2>/dev/null; then
            size=$(du -h "$backup_dir/db_backup_${timestamp}.sql" | cut -f1)
            echo "{\"status\":\"success\",\"file\":\"$backup_dir/db_backup_${timestamp}.sql\",\"size\":\"$size\"}"
        else
            echo '{"status":"error","message":"Database backup failed"}'
            return $EXIT_RESOURCE_ERROR
        fi
    else
        echo -e "${BLUE}Creating database backup...${NC}"
        if $DOCKER_COMPOSE exec -T db pg_dump -U "${DB_USER:-aletheia}" "${DB_NAME:-aletheia}" > "$backup_dir/db_backup_${timestamp}.sql" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} Database backed up to $backup_dir/db_backup_${timestamp}.sql"
            size=$(du -h "$backup_dir/db_backup_${timestamp}.sql" | cut -f1)
            echo "  Size: $size"
        else
            echo -e "${RED}✗${NC} Database backup failed"
            return $EXIT_RESOURCE_ERROR
        fi
    fi
}

# Restore database from backup
db_restore() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        if [ "$OUTPUT_FORMAT" = "json" ]; then
            # List available backups in JSON
            backups_json="["
            first=true
            for file in backups/*.sql; do
                if [ -f "$file" ]; then
                    if [ "$first" = true ]; then
                        first=false
                    else
                        backups_json="${backups_json},"
                    fi
                    size=$(du -h "$file" | cut -f1)
                    backups_json="${backups_json}{\"file\":\"$file\",\"size\":\"$size\"}"
                fi
            done
            backups_json="${backups_json}]"
            echo "{\"status\":\"error\",\"message\":\"Backup file required\",\"available_backups\":$backups_json}"
        else
            echo "Usage: ./dev db restore <backup_file>"
            echo "Available backups:"
            ls -la backups/*.sql 2>/dev/null || echo "No backups found"
        fi
        return $EXIT_CONFIG_ERROR
    fi
    
    if [ ! -f "$backup_file" ]; then
        if [ "$OUTPUT_FORMAT" = "json" ]; then
            echo "{\"status\":\"error\",\"message\":\"Backup file not found\",\"file\":\"$backup_file\"}"
        else
            echo -e "${RED}Backup file not found: $backup_file${NC}"
        fi
        return $EXIT_CONFIG_ERROR
    fi
    
    if confirm_operation "WARNING: This will replace the current database!" "N"; then
        if [ "$OUTPUT_FORMAT" = "json" ]; then
            if $DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" < "$backup_file"; then
                echo '{"status":"success","message":"Database restored"}'
            else
                echo '{"status":"error","message":"Database restore failed"}'
                return $EXIT_RESOURCE_ERROR
            fi
        else
            echo -e "${BLUE}Restoring database...${NC}"
            $DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" < "$backup_file"
            echo -e "${GREEN}✓${NC} Database restored"
        fi
    fi
}

# Restore court processor sample data
db_restore_court_data() {
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        # Check if backup exists
        if [ ! -f court-processor/data/court_documents_backup.sql.gz ]; then
            echo '{"status":"error","message":"Court data backup not found"}'
            return $EXIT_CONFIG_ERROR
        fi
        
        # Check if database is running
        if ! $DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -c "SELECT 1" &>/dev/null; then
            echo '{"status":"error","message":"Database is not running or not ready"}'
            return $EXIT_SERVICE_UNAVAILABLE
        fi
        
        # Check existing data
        EXISTING_COUNT=$($DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -t -c \
            "SELECT COUNT(*) FROM public.court_documents" 2>/dev/null || echo "0")
        EXISTING_COUNT=$(echo $EXISTING_COUNT | tr -d ' ')
        
        if [ "$EXISTING_COUNT" -gt "0" ]; then
            # In JSON mode, we proceed with replacement
            $DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -c \
                "TRUNCATE TABLE public.court_documents RESTART IDENTITY CASCADE;" &>/dev/null
        fi
        
        # Restore the data
        if gunzip -c court-processor/data/court_documents_backup.sql.gz | \
           $DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" &>/dev/null; then
            NEW_COUNT=$($DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -t -c \
                "SELECT COUNT(*) FROM public.court_documents" 2>/dev/null | tr -d ' ')
            echo "{\"status\":\"success\",\"documents_restored\":$NEW_COUNT}"
        else
            echo '{"status":"error","message":"Failed to restore court data"}'
            return $EXIT_RESOURCE_ERROR
        fi
    else
        print_header "Court Processor Data Restoration"
        
        # Check if backup exists
        if [ ! -f court-processor/data/court_documents_backup.sql.gz ]; then
            echo -e "${RED}✗${NC} Court data backup not found"
            echo "  Expected location: court-processor/data/court_documents_backup.sql.gz"
            return $EXIT_CONFIG_ERROR
        fi
        
        # Check if database is running
        if ! $DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -c "SELECT 1" &>/dev/null; then
            echo -e "${RED}✗${NC} Database is not running or not ready"
            echo "  Run './dev up' first to start services"
            return $EXIT_SERVICE_UNAVAILABLE
        fi
        
        # Check existing data
        EXISTING_COUNT=$($DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -t -c \
            "SELECT COUNT(*) FROM public.court_documents" 2>/dev/null || echo "0")
        EXISTING_COUNT=$(echo $EXISTING_COUNT | tr -d ' ')
        
        if [ "$EXISTING_COUNT" -gt "0" ]; then
            echo -e "${YELLOW}⚠${NC} Table already contains $EXISTING_COUNT documents"
            read -p "Replace existing data? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Restoration cancelled"
                return $EXIT_USER_CANCELLED
            fi
            echo -e "${BLUE}Clearing existing data...${NC}"
            $DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -c \
                "TRUNCATE TABLE public.court_documents RESTART IDENTITY CASCADE;"
        fi
        
        # Restore the data
        echo -e "${BLUE}Importing court documents (485 documents, ~9.5MB)...${NC}"
        gunzip -c court-processor/data/court_documents_backup.sql.gz | \
            $DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}"
        
        # Verify restoration
        NEW_COUNT=$($DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -t -c \
            "SELECT COUNT(*) FROM public.court_documents")
        NEW_COUNT=$(echo $NEW_COUNT | tr -d ' ')
        
        echo ""
        echo -e "${GREEN}✓ Successfully restored $NEW_COUNT court documents${NC}"
        echo ""
        echo -e "${CYAN}Document types:${NC}"
        $DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -c \
            "SELECT document_type, COUNT(*) as count FROM public.court_documents GROUP BY document_type ORDER BY count DESC;"
    fi
}

# Export functions
export -f handle_db_command
export -f db_schema
export -f db_shell
export -f db_backup
export -f db_restore
export -f db_restore_court_data