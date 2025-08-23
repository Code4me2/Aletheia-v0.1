#!/bin/bash

# Aletheia Developer Helper Script
# Provides common commands and utilities for developers
# Safe to run - makes no destructive changes without confirmation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script name for usage
SCRIPT_NAME=$(basename "$0")

# Default compose project name
PROJECT_NAME=${COMPOSE_PROJECT_NAME:-aletheia_development}

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Show usage
show_usage() {
    cat << EOF
Aletheia Developer Helper

Usage: $SCRIPT_NAME [command] [options]

Commands:
  status          Show status of all services
  logs [service]  Show logs (all services or specific one)
  reload-nginx    Reload nginx configuration (fixes 404 after rebuild)
  restart [service] Restart service(s)
  validate        Run setup validation checks
  endpoints       Test all service endpoints
  ports           Show port usage
  clean-logs      Clear Docker logs (with confirmation)
  backup-db       Backup database to file
  help            Show this help message

Examples:
  $SCRIPT_NAME status
  $SCRIPT_NAME logs lawyer-chat
  $SCRIPT_NAME reload-nginx
  $SCRIPT_NAME restart lawyer-chat
  $SCRIPT_NAME validate

EOF
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
}

# Get container name for a service
get_container_name() {
    local service=$1
    docker ps --format "{{.Names}}" | grep -E "${PROJECT_NAME}.*${service}" | head -1
}

# Command: status
cmd_status() {
    print_header "Service Status"
    check_docker
    
    echo ""
    echo "Container Status:"
    echo "-----------------"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "${PROJECT_NAME}|NAMES" || echo "No Aletheia containers running"
    
    echo ""
    echo "Container Health:"
    echo "-----------------"
    for container in $(docker ps --format "{{.Names}}" | grep "${PROJECT_NAME}"); do
        health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no health check")
        if [ "$health" = "healthy" ]; then
            print_success "$container: $health"
        elif [ "$health" = "no health check" ]; then
            echo "  $container: $health"
        else
            print_warning "$container: $health"
        fi
    done
}

# Command: logs
cmd_logs() {
    local service=${1:-}
    check_docker
    
    if [ -z "$service" ]; then
        print_header "Showing logs for all services"
        docker-compose logs -f --tail=50
    else
        container=$(get_container_name "$service")
        if [ -z "$container" ]; then
            print_error "Service '$service' not found or not running"
            exit 1
        fi
        print_header "Showing logs for $service"
        docker logs -f --tail=50 "$container"
    fi
}

# Command: reload-nginx
cmd_reload_nginx() {
    print_header "Reloading Nginx"
    check_docker
    
    nginx_container=$(get_container_name "web")
    if [ -z "$nginx_container" ]; then
        print_error "Nginx container not found. Is it running?"
        exit 1
    fi
    
    echo "Testing nginx configuration..."
    if docker exec "$nginx_container" nginx -t > /dev/null 2>&1; then
        print_success "Configuration is valid"
        
        echo "Reloading nginx..."
        docker exec "$nginx_container" nginx -s reload
        print_success "Nginx reloaded successfully"
        
        # Test endpoints
        echo ""
        echo "Testing endpoints:"
        sleep 2
        for endpoint in "/" "/chat" "/n8n/"; do
            if curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080${endpoint}" | grep -q "^[23]"; then
                print_success "http://localhost:8080${endpoint} is accessible"
            else
                print_warning "http://localhost:8080${endpoint} returned an error"
            fi
        done
    else
        print_error "Nginx configuration has errors. Please check:"
        docker exec "$nginx_container" nginx -t
        exit 1
    fi
}

# Command: restart
cmd_restart() {
    local service=${1:-}
    check_docker
    
    if [ -z "$service" ]; then
        print_error "Please specify a service to restart"
        echo "Available services: web, lawyer-chat, ai-portal, n8n, court-processor, db, redis"
        exit 1
    fi
    
    print_header "Restarting $service"
    
    echo "Stopping $service..."
    docker-compose stop "$service"
    
    echo "Starting $service..."
    docker-compose up -d "$service"
    
    # Wait for health check
    sleep 3
    container=$(get_container_name "$service")
    if [ ! -z "$container" ]; then
        health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no health check")
        if [ "$health" = "healthy" ]; then
            print_success "$service restarted and healthy"
        else
            print_warning "$service restarted (status: $health)"
        fi
    fi
    
    # If we restarted a backend service, suggest nginx reload
    if [[ "$service" == "lawyer-chat" ]] || [[ "$service" == "ai-portal" ]] || [[ "$service" == "n8n" ]]; then
        echo ""
        print_warning "You may need to reload nginx for routing to work properly:"
        echo "  $SCRIPT_NAME reload-nginx"
    fi
}

# Command: validate
cmd_validate() {
    print_header "Running Validation Checks"
    
    # Check if validation script exists
    if [ -f "scripts/validate-setup.sh" ]; then
        bash scripts/validate-setup.sh
    else
        print_error "Validation script not found at scripts/validate-setup.sh"
        exit 1
    fi
}

# Command: endpoints
cmd_endpoints() {
    print_header "Testing Service Endpoints"
    check_docker
    
    endpoints=(
        "http://localhost:8080/|Main Web Interface"
        "http://localhost:8080/health|Health Check"
        "http://localhost:8080/chat|Lawyer Chat"
        "http://localhost:8080/n8n/|n8n Workflows"
        "http://localhost:8085/|AI Portal"
    )
    
    for endpoint_info in "${endpoints[@]}"; do
        IFS='|' read -r url description <<< "$endpoint_info"
        
        response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
        
        if [[ "$response" =~ ^[23] ]]; then
            print_success "$description ($url): $response"
        elif [ "$response" = "000" ]; then
            print_error "$description ($url): Connection failed"
        else
            print_warning "$description ($url): $response"
        fi
    done
    
    echo ""
    echo "Note: Some endpoints may require authentication or specific setup."
}

# Command: ports
cmd_ports() {
    print_header "Port Usage"
    
    ports=(
        "8080:Main Web Interface"
        "5678:n8n Workflows"
        "8085:AI Portal"
        "5432:PostgreSQL"
        "6379:Redis"
        "8104:Court Processor API"
        "9200:Elasticsearch (optional)"
        "8000:Haystack (optional)"
    )
    
    echo "Checking Aletheia ports..."
    echo ""
    
    for port_info in "${ports[@]}"; do
        IFS=':' read -r port description <<< "$port_info"
        
        # Check if port is in use
        if lsof -i ":$port" > /dev/null 2>&1; then
            # Check if it's our container
            if docker ps --format "{{.Ports}}" | grep -q ":$port->"; then
                print_success "Port $port ($description): Used by Aletheia"
            else
                print_warning "Port $port ($description): Used by another process"
            fi
        else
            echo "  Port $port ($description): Available"
        fi
    done
}

# Command: clean-logs
cmd_clean_logs() {
    print_header "Clean Docker Logs"
    
    print_warning "This will truncate logs for all Aletheia containers."
    read -p "Are you sure? (y/N): " confirm
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        for container in $(docker ps -a --format "{{.Names}}" | grep "${PROJECT_NAME}"); do
            log_file=$(docker inspect --format='{{.LogPath}}' "$container" 2>/dev/null)
            if [ ! -z "$log_file" ] && [ -f "$log_file" ]; then
                echo "Truncating logs for $container..."
                sudo truncate -s 0 "$log_file"
            fi
        done
        print_success "Logs cleaned"
    else
        echo "Cancelled"
    fi
}

# Command: backup-db
cmd_backup_db() {
    print_header "Database Backup"
    check_docker
    
    db_container=$(get_container_name "db")
    if [ -z "$db_container" ]; then
        print_error "Database container not found"
        exit 1
    fi
    
    # Create backup filename with timestamp
    backup_file="backup_$(date +%Y%m%d_%H%M%S).sql"
    
    echo "Creating backup: $backup_file"
    
    # Get database credentials from .env
    if [ -f .env ]; then
        source .env
        DB_USER=${DB_USER:-aletheia_user}
        DB_NAME=${DB_NAME:-aletheia_db}
    else
        DB_USER="aletheia_user"
        DB_NAME="aletheia_db"
    fi
    
    # Perform backup
    if docker exec "$db_container" pg_dump -U "$DB_USER" "$DB_NAME" > "$backup_file" 2>/dev/null; then
        size=$(du -h "$backup_file" | cut -f1)
        print_success "Database backed up to $backup_file ($size)"
    else
        print_error "Backup failed. Check database credentials and connection."
        rm -f "$backup_file"
        exit 1
    fi
}

# Main script logic
main() {
    # Check if we're in the project root
    if [ ! -f "docker-compose.yml" ]; then
        print_error "Please run this script from the Aletheia project root directory"
        exit 1
    fi
    
    # Parse command
    command=${1:-help}
    shift || true
    
    case "$command" in
        status)
            cmd_status "$@"
            ;;
        logs)
            cmd_logs "$@"
            ;;
        reload-nginx)
            cmd_reload_nginx "$@"
            ;;
        restart)
            cmd_restart "$@"
            ;;
        validate)
            cmd_validate "$@"
            ;;
        endpoints)
            cmd_endpoints "$@"
            ;;
        ports)
            cmd_ports "$@"
            ;;
        clean-logs)
            cmd_clean_logs "$@"
            ;;
        backup-db)
            cmd_backup_db "$@"
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"