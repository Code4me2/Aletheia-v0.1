#!/bin/bash

# ============================================================================
# Dev CLI Service Management Module
# ============================================================================
# This module contains commands for managing Docker Compose services

# Handle service commands
handle_service_command() {
    local cmd="$1"
    shift
    
    case "$cmd" in
        up|start)
            service_up "$@"
            ;;
        down|stop)
            service_down "$@"
            ;;
        restart)
            service_restart "$@"
            ;;
        status|ps)
            service_status "$@"
            ;;
        logs|log)
            service_logs "$@"
            ;;
        shell|exec)
            service_shell "$@"
            ;;
        clean)
            service_clean "$@"
            ;;
        list)
            service_list "$@"
            ;;
        *)
            # If not a subcommand, it might be a main command
            return 1
            ;;
    esac
}

# Start services
service_up() {
    local service="$1"
    
    check_requirements
    check_env
    
    # Check if specific service requested
    if [ -n "$service" ]; then
        echo -e "${BLUE}Starting $service...${NC}"
        $DOCKER_COMPOSE up -d "$service"
        echo -e "${GREEN}✓ Service $service started${NC}"
    else
        echo -e "${BLUE}Starting all Aletheia services...${NC}"
        $DOCKER_COMPOSE up -d
        echo ""
        echo -e "${GREEN}✓ Services started successfully!${NC}"
        echo ""
        echo "Access points:"
        echo "  • Main app:     http://localhost:${WEB_PORT:-8080}"
        echo "  • n8n:          http://localhost:${N8N_PORT:-8100}"
        echo "            Note: Check n8n/README.md for credentials"
        echo "  • Lawyer Chat:  http://localhost:${WEB_PORT:-8080}/chat"
        echo "  • AI Portal:    http://localhost:${AI_PORTAL_PORT:-8102}"
        echo ""
        echo "Run './dev logs' to see output"
        echo "Run './dev health' to check services"
        
        # Wait for database to be ready (max 30 seconds)
        DB_READY=false
        for i in {1..30}; do
            if $DOCKER_COMPOSE exec -T db pg_isready -U "${DB_USER:-aletheia}" &>/dev/null; then
                DB_READY=true
                break
            fi
            if [ $i -eq 1 ]; then
                echo ""
                echo -n "Waiting for database to be ready"
            else
                echo -n "."
            fi
            sleep 1
        done
        
        if [ "$DB_READY" = true ]; then
            echo ""  # New line after dots
            
            # Auto-restore court data if it's a fresh database
            if [ -f court-processor/data/court_documents_backup.sql.gz ]; then
                echo ""
                echo -e "${BLUE}Checking for court processor data...${NC}"
                
                # Check if court_documents table exists and count records
                COUNT=$($DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -t -c \
                    "SELECT COUNT(*) FROM public.court_documents" 2>/dev/null || echo "0")
                COUNT=$(echo $COUNT | tr -d ' ')
                
                if [ "$COUNT" = "0" ]; then
                    echo -e "${BLUE}Restoring court processor sample data (485 documents)...${NC}"
                    if gunzip -c court-processor/data/court_documents_backup.sql.gz | \
                       $DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" &>/dev/null; then
                        echo -e "${GREEN}✓ Successfully restored 485 court documents${NC}"
                        echo "  Documents are now available in Lawyer Chat interface"
                    else
                        echo -e "${YELLOW}⚠ Failed to restore court data${NC}"
                        echo "  You can manually restore with: ./dev db restore-court-data"
                    fi
                elif [ "$COUNT" -gt "0" ]; then
                    echo -e "${GREEN}✓ Database already contains $COUNT court documents${NC}"
                fi
            fi
            
            # Auto-initialize lawyer-chat database and seed demo users
            echo ""
            echo -e "${BLUE}Checking lawyer-chat database setup...${NC}"
            
            # Check if User table exists
            USER_TABLE_EXISTS=$($DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -t -c \
                "SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'User');" 2>/dev/null | tr -d ' ')
            
            if [ "$USER_TABLE_EXISTS" = "f" ] || [ "$USER_TABLE_EXISTS" = "false" ]; then
                echo -e "${BLUE}Initializing lawyer-chat database...${NC}"
                
                # Check if lawyer-chat service directory exists
                if [ -d "services/lawyer-chat" ]; then
                    cd services/lawyer-chat
                    
                    # URL-encode the password to handle special characters
                    ENCODED_PASSWORD=$(url_encode "${DB_PASSWORD}")
                    export DATABASE_URL="postgresql://${DB_USER:-aletheia}:${ENCODED_PASSWORD}@localhost:${POSTGRES_PORT:-8200}/${DB_NAME:-aletheia}"
                    
                    if npx prisma db push --force-reset --skip-generate &>/dev/null 2>&1; then
                        echo -e "${GREEN}✓ Database schema created${NC}"
                        
                        # Generate Prisma client
                        if npx prisma generate &>/dev/null 2>&1; then
                            echo -e "${GREEN}✓ Prisma client generated${NC}"
                            
                            # Seed demo users
                            if [ -f "scripts/seed-users.cjs" ]; then
                                if node scripts/seed-users.cjs &>/dev/null 2>&1; then
                                    echo -e "${GREEN}✓ Demo users created:${NC}"
                                    echo "    • demo@reichmanjorgensen.com / demo123"
                                    echo "    • admin@reichmanjorgensen.com / admin123"
                                else
                                    echo -e "${YELLOW}⚠ Failed to seed demo users${NC}"
                                    echo "  You can manually run: cd services/lawyer-chat && node scripts/seed-users.cjs"
                                fi
                            elif [ -f "prisma/seed.ts" ]; then
                                if npx tsx prisma/seed.ts &>/dev/null 2>&1; then
                                    echo -e "${GREEN}✓ Demo users created:${NC}"
                                    echo "    • demo@reichmanjorgensen.com / demo123"
                                    echo "    • admin@reichmanjorgensen.com / admin123"
                                else
                                    echo -e "${YELLOW}⚠ Failed to seed demo users${NC}"
                                    echo "  You can manually run: cd services/lawyer-chat && npx tsx prisma/seed.ts"
                                fi
                            fi
                        else
                            echo -e "${YELLOW}⚠ Failed to generate Prisma client${NC}"
                        fi
                    else
                        echo -e "${YELLOW}⚠ Failed to initialize database schema${NC}"
                        echo "  You can manually run: cd services/lawyer-chat && npx prisma db push"
                    fi
                    
                    cd - &>/dev/null
                else
                    echo -e "${YELLOW}⚠ Lawyer-chat service directory not found${NC}"
                fi
            else
                # Check if demo users exist
                USER_COUNT=$($DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -t -c \
                    "SELECT COUNT(*) FROM \"User\" WHERE email IN ('demo@reichmanjorgensen.com', 'admin@reichmanjorgensen.com');" 2>/dev/null | tr -d ' ')
                
                if [ "$USER_COUNT" = "0" ]; then
                    echo -e "${BLUE}Seeding demo users...${NC}"
                    
                    if [ -d "services/lawyer-chat" ]; then
                        cd services/lawyer-chat
                        # URL-encode the password to handle special characters
                        ENCODED_PASSWORD=$(url_encode "${DB_PASSWORD}")
                        export DATABASE_URL="postgresql://${DB_USER:-aletheia}:${ENCODED_PASSWORD}@localhost:${POSTGRES_PORT:-8200}/${DB_NAME:-aletheia}"
                        
                        if [ -f "scripts/seed-users.cjs" ]; then
                            if node scripts/seed-users.cjs &>/dev/null 2>&1; then
                                echo -e "${GREEN}✓ Demo users created:${NC}"
                                echo "    • demo@reichmanjorgensen.com / demo123"
                                echo "    • admin@reichmanjorgensen.com / admin123"
                            else
                                echo -e "${YELLOW}⚠ Failed to seed demo users${NC}"
                            fi
                        fi
                        
                        cd - &>/dev/null
                    fi
                else
                    echo -e "${GREEN}✓ Lawyer-chat database ready ($USER_COUNT demo users found)${NC}"
                fi
            fi
        else
            echo ""  # New line after dots
            echo -e "${YELLOW}⚠ Database not ready${NC}"
            echo "  Database initialization skipped - run './dev up' again when ready"
        fi
    fi
}

# Stop services
service_down() {
    local service="$1"
    
    check_requirements
    
    # Check if specific service requested
    if [ -n "$service" ]; then
        echo -e "${BLUE}Stopping $service...${NC}"
        $DOCKER_COMPOSE stop "$service"
        echo -e "${GREEN}✓ Service $service stopped${NC}"
    else
        echo -e "${BLUE}Stopping all Aletheia services...${NC}"
        $DOCKER_COMPOSE down
        echo -e "${GREEN}✓ All services stopped${NC}"
    fi
}

# Restart services
service_restart() {
    local service="$1"
    
    check_requirements
    if [ -z "$service" ]; then
        echo -e "${BLUE}Restarting all services...${NC}"
        $DOCKER_COMPOSE restart
    else
        echo -e "${BLUE}Restarting $service...${NC}"
        $DOCKER_COMPOSE restart "$service"
    fi
    echo -e "${GREEN}✓ Restart complete${NC}"
}

# Show service status
service_status() {
    check_requirements
    
    if [ "$OUTPUT_FORMAT" != "json" ]; then
        print_header "Service Status"
        
        # Container status
        echo -e "${CYAN}Containers:${NC}"
        $DOCKER_COMPOSE ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
        echo ""
        
        # Health status
        echo -e "${CYAN}Health Status:${NC}"
    fi
    
    healthy=0
    unhealthy=0
    nocheck=0
    services_json="["
    first=true
    
    for container in $(docker ps --format "{{.Names}}" --filter "label=com.docker.compose.project=${PROJECT_NAME}"); do
        # Special handling for known containers without standard health checks
        if [[ "$container" == *"recap-webhook"* ]]; then
            if [ "$OUTPUT_FORMAT" != "json" ]; then
                echo -e "${YELLOW}○${NC} $container: health check ignored"
            fi
            nocheck=$((nocheck + 1))
            continue
        fi
        
        # Try to get health status
        health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no check{{end}}' "$container" 2>/dev/null || echo "error")
        
        case "$health" in
            healthy)
                if [ "$OUTPUT_FORMAT" != "json" ]; then
                    echo -e "${GREEN}✓${NC} $container: healthy"
                fi
                healthy=$((healthy + 1))
                health_json="\"healthy\""
                ;;
            unhealthy|starting)
                # Skip recap-webhook unhealthy status as it's expected
                if [[ "$container" != *"recap-webhook"* ]]; then
                    if [ "$OUTPUT_FORMAT" != "json" ]; then
                        echo -e "${RED}✗${NC} $container: $health"
                    fi
                    unhealthy=$((unhealthy + 1))
                fi
                health_json="\"$health\""
                ;;
            "no check"|"")
                if [ "$OUTPUT_FORMAT" != "json" ]; then
                    echo -e "${YELLOW}○${NC} $container: no health check"
                fi
                nocheck=$((nocheck + 1))
                health_json="\"no_check\""
                ;;
            error)
                if [ "$OUTPUT_FORMAT" != "json" ]; then
                    echo -e "${RED}✗${NC} $container: inspection failed"
                fi
                unhealthy=$((unhealthy + 1))
                health_json="\"error\""
                ;;
        esac
        
        # Build JSON array
        if [ "$OUTPUT_FORMAT" = "json" ]; then
            if [ "$first" = true ]; then
                first=false
            else
                services_json="${services_json},"
            fi
            services_json="${services_json}{\"name\":\"$container\",\"health\":$health_json}"
        fi
    done
    
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        services_json="${services_json}]"
        echo "{\"healthy\":$healthy,\"unhealthy\":$unhealthy,\"nocheck\":$nocheck,\"services\":$services_json}"
    else
        echo ""
        echo -e "Summary: ${GREEN}$healthy healthy${NC}, ${RED}$unhealthy issues${NC}, ${YELLOW}$nocheck unchecked${NC}"
    fi
}

# Show service logs
service_logs() {
    local service="$1"
    
    check_requirements
    if [ -z "$service" ]; then
        $DOCKER_COMPOSE logs -f --tail=100
    else
        $DOCKER_COMPOSE logs -f --tail=100 "$service"
    fi
}

# Open shell in container
service_shell() {
    local service="$1"
    
    check_requirements
    if [ -z "$service" ]; then
        if [ "$OUTPUT_FORMAT" = "json" ]; then
            echo '{"status":"error","message":"Service name required"}'
        else
            echo -e "${RED}Please specify a service name${NC}"
            echo "Example: ./dev shell db"
        fi
        exit $EXIT_CONFIG_ERROR
    fi
    
    case "$service" in
        db|postgres)
            echo -e "${BLUE}Opening PostgreSQL shell...${NC}"
            $DOCKER_COMPOSE exec db psql -U "${DB_USER:-aletheia}" "${DB_NAME:-aletheia}"
            ;;
        n8n)
            echo -e "${BLUE}Opening n8n shell...${NC}"
            $DOCKER_COMPOSE exec n8n /bin/sh
            ;;
        *)
            echo -e "${BLUE}Opening shell in $service...${NC}"
            $DOCKER_COMPOSE exec "$service" /bin/sh 2>/dev/null || $DOCKER_COMPOSE exec "$service" /bin/bash
            ;;
    esac
}

# List available services
service_list() {
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        # Get services from docker-compose config in JSON format
        services=$($DOCKER_COMPOSE config --services 2>/dev/null)
        if [ -z "$services" ]; then
            echo '{"status":"error","message":"No services found"}'
        else
            echo -n '{"status":"success","services":['
            first=true
            while IFS= read -r service; do
                if [ "$first" = true ]; then
                    first=false
                else
                    echo -n ','
                fi
                echo -n "\"$service\""
            done <<< "$services"
            echo ']}'
        fi
    else
        echo -e "${BLUE}Available Services:${NC}"
        $DOCKER_COMPOSE config --services 2>/dev/null | while read service; do
            # Check if service is running
            if $DOCKER_COMPOSE ps "$service" 2>/dev/null | grep -q "Up\|Running"; then
                echo -e "  ${GREEN}●${NC} $service (running)"
            else
                echo -e "  ${YELLOW}○${NC} $service (stopped)"
            fi
        done
    fi
}

# Clean services and volumes (destructive)
service_clean() {
    if confirm_operation "WARNING: This will delete all data!" "N"; then
        echo -e "${BLUE}Cleaning up...${NC}"
        $DOCKER_COMPOSE down -v
        output_result "success" "Cleanup complete"
    else
        if [ "$OUTPUT_FORMAT" = "json" ]; then
            echo '{"status":"cancelled","message":"User cancelled operation"}'
        else
            echo "Cancelled"
        fi
    fi
}

# Export functions
export -f handle_service_command
export -f service_up
export -f service_down
export -f service_restart
export -f service_status
export -f service_logs
export -f service_shell
export -f service_list
export -f service_clean