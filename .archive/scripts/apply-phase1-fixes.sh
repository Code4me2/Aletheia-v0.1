#!/bin/bash
set -e

echo "=== Aletheia v0.1 Network Configuration - Phase 1 Fix ==="
echo ""

# Check if .env has COMPOSE_PROJECT_NAME
if ! grep -q "COMPOSE_PROJECT_NAME=aletheia" .env; then
    echo "ERROR: COMPOSE_PROJECT_NAME=aletheia not found in .env"
    echo "Please ensure your .env file contains this line"
    exit 1
fi

echo "✓ COMPOSE_PROJECT_NAME is set correctly"

# Function to check if services are running
check_running() {
    if docker-compose ps | grep -q "Up"; then
        return 0
    else
        return 1
    fi
}

# Backup current data if services are running
if check_running; then
    echo ""
    echo "⚠️  Services are currently running. We need to stop them to apply network fixes."
    read -p "Do you want to backup the database before proceeding? (recommended) [Y/n]: " backup_choice
    
    if [[ "$backup_choice" != "n" ]] && [[ "$backup_choice" != "N" ]]; then
        echo "Creating database backup..."
        mkdir -p backups
        timestamp=$(date +%Y%m%d_%H%M%S)
        docker-compose exec -T db pg_dumpall -U ${DB_USER:-your_db_user} > "backups/db_backup_${timestamp}.sql" || echo "Warning: Database backup failed or no data to backup"
        echo "✓ Database backup created (if data existed): backups/db_backup_${timestamp}.sql"
        
        # Backup n8n data
        echo "Creating n8n data backup..."
        docker cp aletheia-v01-n8n-1:/home/node/.n8n "backups/n8n_backup_${timestamp}" 2>/dev/null || echo "Note: n8n backup skipped (container may not exist)"
    fi
fi

# Stop all services
echo ""
echo "Stopping all services..."
docker-compose down

# Clean up old networks
echo ""
echo "Cleaning up old networks..."
networks_to_remove=(
    "data-compose_frontend"
    "data-compose_backend"
    "data_compose_frontend"
    "data_compose_backend"
)

for network in "${networks_to_remove[@]}"; do
    if docker network ls | grep -q "$network"; then
        echo "Removing network: $network"
        docker network rm "$network" 2>/dev/null || echo "  Warning: Could not remove $network (may be in use)"
    fi
done

# Remove any orphaned networks
docker network prune -f

echo ""
echo "✓ Old networks cleaned up"

# Start services with new configuration
echo ""
echo "Starting services with new network configuration..."
docker-compose up -d

# Wait for services to be ready
echo ""
echo "Waiting for services to start..."
sleep 10

# Verify connectivity
echo ""
echo "Verifying service connectivity..."

# Check if n8n can reach the database
if docker exec aletheia-n8n-1 ping -c 1 db &>/dev/null; then
    echo "✓ n8n can reach database"
else
    echo "⚠️  Warning: n8n cannot reach database - manual intervention may be needed"
fi

# Check network configuration
echo ""
echo "Current network configuration:"
docker network ls | grep aletheia || echo "No aletheia networks found!"

echo ""
echo "Container network assignments:"
docker ps --format "table {{.Names}}\t{{.Networks}}" | grep -v "NAMES" | sort

echo ""
echo "=== Phase 1 Complete ==="
echo ""
echo "Next steps:"
echo "1. Test n8n PostgreSQL connection at http://localhost:5678"
echo "2. Verify all services are functioning correctly"
echo "3. If everything works, commit these changes to git"
echo ""
echo "PostgreSQL credentials for n8n:"
echo "  Host: db"
echo "  Database: your_db_name"
echo "  User: your_db_user"
echo "  Password: your_secure_password_here"
echo "  Port: 5432"
echo ""

# Check if any services failed to start
if docker-compose ps | grep -q "Exit"; then
    echo "⚠️  WARNING: Some services failed to start!"
    echo "Check logs with: docker-compose logs [service-name]"
    echo ""
fi