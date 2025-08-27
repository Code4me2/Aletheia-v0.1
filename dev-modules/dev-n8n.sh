#!/bin/bash

# ============================================================================
# Dev CLI n8n Module
# ============================================================================
# This module contains all n8n-related commands
# Kept as a single module to facilitate merging with n8n branch changes

# Main n8n command handler
handle_n8n_command() {
    local cmd="$1"
    shift
    
    # This section is extracted directly from the main dev script
    # to keep it intact for easier merging with n8n branch updates
            case "$2" in
                setup)
                    echo -e "${BLUE}Running n8n auto-setup...${NC}"
                    if ! check_service_running "n8n"; then
                        exit $EXIT_SERVICE_UNAVAILABLE
                    fi
                    
                    # Run auto-setup
                    $DOCKER_COMPOSE exec -T n8n sh /usr/local/bin/auto-setup
                    
                    echo ""
                    echo -e "${GREEN}Setup complete!${NC}"
                    echo "Access n8n at: http://localhost:${N8N_PORT:-8100}"
                    echo "Login: admin@aletheia.local / admin123"
                    ;;
                workflows)
                    case "$3" in
                        list)
                            echo -e "${BLUE}Listing n8n workflows...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            # Execute n8n CLI inside container to list workflows
                            $DOCKER_COMPOSE exec -T n8n n8n list:workflow 2>/dev/null || {
                                echo -e "${RED}Failed to list workflows. n8n may still be starting up.${NC}"
                                exit 1
                            }
                            ;;
                        import)
                            echo -e "${BLUE}Importing workflows to n8n...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            # Check if workflow_json directory exists
                            if [ ! -d "workflow_json" ]; then
                                echo -e "${RED}workflow_json directory not found${NC}"
                                exit 1
                            fi
                            
                            # Count workflow files
                            workflow_count=$(find workflow_json -name "*.json" -type f 2>/dev/null | wc -l)
                            if [ $workflow_count -eq 0 ]; then
                                echo -e "${YELLOW}No workflow files found in workflow_json/${NC}"
                                exit 0
                            fi
                            
                            echo "Found $workflow_count workflow file(s) to import"
                            
                            # Copy workflows to container and import
                            for workflow_file in workflow_json/*.json; do
                                if [ -f "$workflow_file" ]; then
                                    basename=$(basename "$workflow_file")
                                    echo -n "  • Importing $basename... "
                                    
                                    # Copy file to container
                                    docker cp "$workflow_file" "$(docker-compose ps -q n8n):/tmp/$basename"
                                    
                                    # Import using n8n CLI
                                    if $DOCKER_COMPOSE exec -T n8n n8n import:workflow --input="/tmp/$basename" 2>/dev/null; then
                                        echo -e "${GREEN}✓${NC}"
                                    else
                                        echo -e "${RED}✗${NC}"
                                    fi
                                    
                                    # Clean up temp file
                                    $DOCKER_COMPOSE exec -T n8n rm -f "/tmp/$basename"
                                fi
                            done
                            
                            echo -e "${GREEN}Workflow import complete${NC}"
                            ;;
                        export)
                            echo -e "${BLUE}Exporting n8n workflows...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            # Create export directory
                            export_dir="workflow_export_$(date +%Y%m%d_%H%M%S)"
                            mkdir -p "$export_dir"
                            
                            echo "Exporting workflows to $export_dir/"
                            
                            # Get list of workflows and export each
                            # Skip "User settings..." and header lines
                            workflow_list=$($DOCKER_COMPOSE exec -T n8n n8n list:workflow 2>/dev/null | grep -v "User settings" | grep -v "Error tracking" | grep "|")
                            
                            if [ -z "$workflow_list" ]; then
                                echo -e "${YELLOW}No workflows found to export${NC}"
                                rmdir "$export_dir"
                                exit 0
                            fi
                            
                            echo "$workflow_list" | while IFS='|' read -r workflow_id workflow_name rest; do
                                workflow_id=$(echo "$workflow_id" | tr -d ' ')
                                workflow_name=$(echo "$workflow_name" | tr -d ' ' | tr '/' '_')
                                
                                if [ -z "$workflow_id" ] || [ "$workflow_id" = "ID" ]; then
                                    continue
                                fi
                                
                                echo -n "  • Exporting workflow $workflow_id ($workflow_name)... "
                                
                                # Export workflow to container temp file
                                if $DOCKER_COMPOSE exec -T n8n n8n export:workflow --id="$workflow_id" --output="/tmp/workflow_$workflow_id.json" 2>/dev/null; then
                                    # Copy from container to host
                                    docker cp "$($DOCKER_COMPOSE ps -q n8n):/tmp/workflow_$workflow_id.json" "$export_dir/${workflow_name}.json" 2>/dev/null
                                    $DOCKER_COMPOSE exec -T n8n rm -f "/tmp/workflow_$workflow_id.json" 2>/dev/null
                                    echo -e "${GREEN}✓${NC}"
                                else
                                    echo -e "${RED}✗${NC}"
                                fi
                            done
                            
                            echo -e "${GREEN}Workflows exported to $export_dir/${NC}"
                            ;;
                        reset)
                            echo -e "${YELLOW}This will clear all n8n workflows and reimport from workflow_json/${NC}"
                            read -p "Are you sure? (y/N) " -n 1 -r
                            echo
                            if [[ $REPLY =~ ^[Yy]$ ]]; then
                                echo -e "${BLUE}Resetting n8n workflows...${NC}"
                                
                                # Stop n8n
                                echo "Stopping n8n..."
                                $DOCKER_COMPOSE stop n8n
                                
                                # Clear the database volume
                                echo "Clearing n8n database..."
                                docker volume rm "${PROJECT_NAME}_n8n_data" 2>/dev/null || true
                                
                                # Start n8n with force reimport
                                echo "Starting n8n with force reimport..."
                                FORCE_REIMPORT=true $DOCKER_COMPOSE up -d n8n
                                
                                echo -e "${GREEN}Workflow reset initiated. Check logs with: ./dev logs n8n${NC}"
                            else
                                echo "Cancelled"
                            fi
                            ;;
                        activate)
                            echo -e "${BLUE}Activating all n8n workflows...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            if $DOCKER_COMPOSE exec -T n8n n8n update:workflow --all --active=true 2>/dev/null; then
                                echo -e "${GREEN}All workflows activated${NC}"
                            else
                                echo -e "${RED}Failed to activate workflows${NC}"
                                exit 1
                            fi
                            ;;
                        deactivate)
                            if [ -z "$4" ]; then
                                echo -e "${BLUE}Deactivating all n8n workflows...${NC}"
                                if ! check_service_running "n8n"; then
                                    exit $EXIT_SERVICE_UNAVAILABLE
                                fi
                                
                                if $DOCKER_COMPOSE exec -T n8n n8n update:workflow --all --active=false 2>/dev/null; then
                                    echo -e "${GREEN}All workflows deactivated${NC}"
                                else
                                    echo -e "${RED}Failed to deactivate workflows${NC}"
                                    exit 1
                                fi
                            else
                                echo -e "${BLUE}Deactivating workflow $4...${NC}"
                                if $DOCKER_COMPOSE exec -T n8n n8n update:workflow --id="$4" --active=false 2>/dev/null; then
                                    echo -e "${GREEN}Workflow $4 deactivated${NC}"
                                else
                                    echo -e "${RED}Failed to deactivate workflow $4${NC}"
                                    exit 1
                                fi
                            fi
                            ;;
                        execute)
                            if [ -z "$4" ]; then
                                echo "Usage: ./dev n8n workflows execute <workflow-id> [json-data]"
                                echo ""
                                echo "Execute a specific workflow by ID"
                                echo "Get workflow IDs with: ./dev n8n workflows list"
                                echo ""
                                echo "Examples:"
                                echo "  ./dev n8n workflows execute abc123"
                                echo "  ./dev n8n workflows execute abc123 '{\"test\": true}'"
                                exit 1
                            fi
                            
                            echo -e "${BLUE}Executing workflow $4...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            # Use our custom execution helper
                            data="${5:-{}}"
                            $DOCKER_COMPOSE exec -T n8n n8n-exec trigger "$4" "$data"
                            ;;
                        *)
                            echo "Usage: ./dev n8n workflows {list|import|export|reset|activate|deactivate|execute}"
                            echo ""
                            echo "Commands:"
                            echo "  list           - List all workflows in n8n"
                            echo "  import         - Import workflows from workflow_json/"
                            echo "  export         - Export all workflows to a timestamped directory"
                            echo "  reset          - Clear all workflows and reimport from workflow_json/"
                            echo "  activate       - Activate all workflows"
                            echo "  deactivate [id] - Deactivate all workflows or specific one"
                            echo "  execute <id>   - Execute a specific workflow"
                            ;;
                    esac
                    ;;
                nodes)
                    case "$3" in
                        list)
                            echo -e "${BLUE}Listing n8n custom nodes...${NC}"
                            echo ""
                            echo "Installed custom nodes:"
                            for node_dir in n8n/custom-nodes/n8n-nodes-*; do
                                if [ -d "$node_dir" ]; then
                                    node_name=$(basename "$node_dir")
                                    if [ -f "$node_dir/package.json" ]; then
                                        version=$(grep '"version"' "$node_dir/package.json" | head -1 | cut -d'"' -f4)
                                        echo "  • $node_name (v$version)"
                                        
                                        # Check if built
                                        if [ -d "$node_dir/dist" ]; then
                                            echo "    Status: Built ✓"
                                        else
                                            echo "    Status: Not built ✗"
                                        fi
                                    fi
                                fi
                            done
                            ;;
                        build)
                            echo -e "${BLUE}Building n8n custom nodes...${NC}"
                            
                            failed=0
                            for node_dir in n8n/custom-nodes/n8n-nodes-*; do
                                if [ -d "$node_dir" ] && [ -f "$node_dir/package.json" ]; then
                                    node_name=$(basename "$node_dir")
                                    echo -n "  • Building $node_name... "
                                    
                                    cd "$node_dir"
                                    if npm install --silent 2>/dev/null && npm run build --silent 2>/dev/null; then
                                        echo -e "${GREEN}✓${NC}"
                                    else
                                        echo -e "${RED}✗${NC}"
                                        failed=$((failed + 1))
                                    fi
                                    cd - > /dev/null
                                fi
                            done
                            
                            if [ $failed -eq 0 ]; then
                                echo -e "${GREEN}All nodes built successfully${NC}"
                                echo "Rebuild n8n container to use updated nodes: ./dev rebuild n8n"
                            else
                                echo -e "${YELLOW}$failed node(s) failed to build${NC}"
                            fi
                            ;;
                        verify)
                            echo -e "${BLUE}Verifying n8n custom nodes...${NC}"
                            
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            echo "Checking custom nodes in container..."
                            
                            # Check if custom nodes directory exists in container
                            if $DOCKER_COMPOSE exec -T n8n test -d /data/.n8n/custom 2>/dev/null; then
                                echo -e "${GREEN}✓${NC} Custom nodes directory exists"
                                
                                # List nodes in container
                                echo ""
                                echo "Nodes in container:"
                                $DOCKER_COMPOSE exec -T n8n ls -la /data/.n8n/custom/ 2>/dev/null | grep "^d" | awk '{print "  • " $NF}'
                            else
                                echo -e "${RED}✗${NC} Custom nodes directory not found"
                            fi
                            
                            # Check if nodes are loading properly
                            echo ""
                            echo "Checking n8n logs for node loading errors..."
                            if $DOCKER_COMPOSE logs n8n 2>&1 | tail -50 | grep -i "error.*loading\|failed.*load" > /dev/null; then
                                echo -e "${YELLOW}⚠ Found node loading errors in logs. Check: ./dev logs n8n${NC}"
                            else
                                echo -e "${GREEN}✓ No node loading errors found${NC}"
                            fi
                            ;;
                        *)
                            echo "Usage: ./dev n8n nodes {list|build|verify}"
                            echo ""
                            echo "Commands:"
                            echo "  list    - List all custom nodes and their status"
                            echo "  build   - Build all custom nodes"
                            echo "  verify  - Verify nodes are properly installed in container"
                            ;;
                    esac
                    ;;
                cli)
                    # Pass-through to n8n CLI
                    shift 2
                    
                    # Check if any arguments provided
                    if [ $# -eq 0 ]; then
                        echo "Usage: ./dev n8n cli <command> [options]"
                        echo ""
                        echo "Pass commands directly to the n8n CLI"
                        echo ""
                        echo "Examples:"
                        echo "  ./dev n8n cli --version              # Get n8n version"
                        echo "  ./dev n8n cli --help                 # Get n8n help"
                        echo "  ./dev n8n cli list:workflow --help   # Get help for specific command"
                        echo ""
                        echo "Note: Avoid 'start' or 'webhook' commands which conflict with running instance"
                        exit 1
                    fi
                    
                    if ! check_service_running "n8n"; then
                        exit $EXIT_SERVICE_UNAVAILABLE
                    fi
                    
                    echo -e "${BLUE}Executing n8n CLI command...${NC}"
                    $DOCKER_COMPOSE exec -T n8n n8n "$@"
                    ;;
                credentials)
                    case "$3" in
                        export)
                            echo -e "${BLUE}Exporting n8n credentials...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            export_dir="credentials_export_$(date +%Y%m%d_%H%M%S)"
                            mkdir -p "$export_dir"
                            echo "Exporting credentials to $export_dir/"
                            
                            if $DOCKER_COMPOSE exec -T n8n n8n export:credentials --all --separate --output="/tmp/cred_export/" 2>&1 | grep -v "Error tracking disabled"; then
                                docker cp "$($DOCKER_COMPOSE ps -q n8n):/tmp/cred_export/" "$export_dir/" 2>/dev/null
                                $DOCKER_COMPOSE exec -T n8n rm -rf "/tmp/cred_export/" 2>/dev/null
                                echo -e "${GREEN}Credentials exported to $export_dir/${NC}"
                            else
                                echo -e "${RED}Failed to export credentials${NC}"
                                rmdir "$export_dir"
                                exit 1
                            fi
                            ;;
                        import)
                            if [ -z "$4" ]; then
                                echo "Usage: ./dev n8n credentials import <file-or-directory>"
                                echo ""
                                echo "Import credentials from a JSON file or directory"
                                exit 1
                            fi
                            
                            echo -e "${BLUE}Importing n8n credentials...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            import_path="$4"
                            
                            if [ ! -e "$import_path" ]; then
                                echo -e "${RED}File or directory not found: $import_path${NC}"
                                exit 1
                            fi
                            
                            container_path="/tmp/cred_import_$(date +%s)"
                            docker cp "$import_path" "$($DOCKER_COMPOSE ps -q n8n):$container_path"
                            
                            if [ -d "$import_path" ]; then
                                echo "Importing from directory..."
                                import_flags="--separate --input=$container_path"
                            else
                                echo "Importing from file..."
                                import_flags="--input=$container_path"
                            fi
                            
                            if $DOCKER_COMPOSE exec -T n8n n8n import:credentials $import_flags 2>/dev/null; then
                                echo -e "${GREEN}Credentials imported successfully${NC}"
                            else
                                echo -e "${RED}Failed to import credentials${NC}"
                                exit 1
                            fi
                            
                            $DOCKER_COMPOSE exec -T n8n rm -rf "$container_path" 2>/dev/null
                            ;;
                        backup)
                            echo -e "${BLUE}Backing up n8n credentials (encrypted)...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            backup_file="credentials_backup_$(date +%Y%m%d_%H%M%S).json"
                            
                            if $DOCKER_COMPOSE exec -T n8n n8n export:credentials --all --output="/tmp/$backup_file" 2>/dev/null; then
                                docker cp "$($DOCKER_COMPOSE ps -q n8n):/tmp/$backup_file" "$backup_file" 2>/dev/null
                                $DOCKER_COMPOSE exec -T n8n rm -f "/tmp/$backup_file" 2>/dev/null
                                echo -e "${GREEN}Credentials backed up to $backup_file${NC}"
                                echo -e "${YELLOW}Note: Credentials are encrypted with your n8n instance key${NC}"
                            else
                                echo -e "${RED}Failed to backup credentials${NC}"
                                exit 1
                            fi
                            ;;
                        *)
                            echo "Usage: ./dev n8n credentials {export|import|backup}"
                            echo ""
                            echo "Commands:"
                            echo "  export       - Export all credentials to separate files"
                            echo "  import <path> - Import credentials from file or directory"
                            echo "  backup       - Create encrypted backup of all credentials"
                            echo ""
                            echo "Note: Credentials contain sensitive data. Handle exports carefully."
                            ;;
                    esac
                    ;;
                executions)
                    case "$3" in
                        list)
                            echo -e "${BLUE}Listing recent n8n executions...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            # List executions using n8n CLI
                            $DOCKER_COMPOSE exec -T n8n n8n list:execution --limit=10 2>/dev/null || {
                                echo -e "${YELLOW}No executions found or n8n is still starting${NC}"
                            }
                            ;;
                        *)
                            echo "Usage: ./dev n8n executions {list}"
                            echo ""
                            echo "Commands:"
                            echo "  list - List recent workflow executions"
                            ;;
                    esac
                    ;;
                env)
                    case "$3" in
                        list)
                            echo -e "${BLUE}Listing environment variables in n8n container...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            echo ""
                            echo "Current n8n environment variables:"
                            $DOCKER_COMPOSE exec -T n8n env | sort | grep -E "^(N8N_|DB_|POSTGRES_|REDIS_|SMTP_|COURT_|NEXT_)" || {
                                echo "Standard environment only:"
                                $DOCKER_COMPOSE exec -T n8n env | sort | grep "^N8N_"
                            }
                            ;;
                        inject)
                            echo -e "${BLUE}Injecting .env variables into n8n container...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            # Create a script to export env vars
                            if [ -f .env ]; then
                                echo -e "${YELLOW}Note: Environment variables injected this way are temporary.${NC}"
                                echo -e "${YELLOW}For permanent changes, update docker-compose.yml and rebuild.${NC}"
                                echo ""
                                
                                # Read .env and export to container
                                while IFS='=' read -r key value; do
                                    # Skip comments and empty lines
                                    [[ "$key" =~ ^#.*$ ]] && continue
                                    [[ -z "$key" ]] && continue
                                    
                                    # Export to container (note: this is temporary and won't persist)
                                    echo "Exporting $key"
                                    $DOCKER_COMPOSE exec -T n8n sh -c "export $key='$value'" 2>/dev/null
                                done < .env
                                
                                echo -e "${GREEN}Environment variables injected (temporary)${NC}"
                                echo ""
                                echo "To make permanent, add to docker-compose.yml under n8n service:"
                                echo "  environment:"
                                grep -E "^(DB_|POSTGRES_|REDIS_|SMTP_|COURT_)" .env | while IFS='=' read -r key value; do
                                    echo "    - $key=\${$key}"
                                done | head -10
                                if [ $(grep -E "^(DB_|POSTGRES_|REDIS_|SMTP_|COURT_)" .env | wc -l) -gt 10 ]; then
                                    echo "    ... and more"
                                fi
                            else
                                echo -e "${RED}No .env file found${NC}"
                                exit 1
                            fi
                            ;;
                        *)
                            echo "Usage: ./dev n8n env {list|inject}"
                            echo ""
                            echo "Commands:"
                            echo "  list   - List environment variables in n8n container"
                            echo "  inject - Inject .env variables into n8n (temporary)"
                            echo ""
                            echo "Note: For permanent env var changes, modify docker-compose.yml"
                            ;;
                    esac
                    ;;
                test)
                    case "$3" in
                        webhook)
                            echo -e "${BLUE}Testing n8n webhook...${NC}"
                            
                            webhook_id="${N8N_WEBHOOK_ID:-c188c31c-1c45-4118-9ece-5b6057ab5177}"
                            port="${N8N_PORT:-8100}"
                            
                            echo "Sending test payload to webhook..."
                            echo ""
                            
                            # Create test payload
                            payload='{
                                "test": true,
                                "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
                                "source": "dev-cli",
                                "message": "Test webhook trigger from dev CLI"
                            }'
                            
                            # Send webhook request
                            response=$(curl -s -X POST "http://localhost:$port/webhook/$webhook_id" \
                                -H 'Content-Type: application/json' \
                                -d "$payload" 2>&1)
                            
                            if [ $? -eq 0 ]; then
                                echo -e "${GREEN}✓ Webhook request sent successfully${NC}"
                                echo ""
                                echo "Response:"
                                echo "$response" | head -20
                                
                                if echo "$response" | grep -q "Workflow Webhook Error"; then
                                    echo ""
                                    echo -e "${YELLOW}Note: Webhook received but workflow may have errors${NC}"
                                    echo "Check workflow configuration in n8n UI"
                                fi
                            else
                                echo -e "${RED}✗ Failed to send webhook request${NC}"
                                echo "Check if n8n is running: ./dev status n8n"
                            fi
                            ;;
                        *)
                            echo "Usage: ./dev n8n test {webhook}"
                            echo ""
                            echo "Commands:"
                            echo "  webhook - Send test payload to configured webhook"
                            ;;
                    esac
                    ;;
                monitor)
                    case "$3" in
                        logs)
                            echo -e "${BLUE}Monitoring n8n logs (Ctrl+C to stop)...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            # Tail logs with optional filter
                            if [ -n "$4" ]; then
                                echo "Filtering for: $4"
                                $DOCKER_COMPOSE logs -f n8n 2>&1 | grep --line-buffered -i "$4"
                            else
                                $DOCKER_COMPOSE logs -f n8n 2>&1
                            fi
                            ;;
                        webhooks)
                            echo -e "${BLUE}Monitoring webhook activity...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            echo "Watching for webhook calls (Ctrl+C to stop):"
                            echo ""
                            # Monitor n8n logs for webhook activity
                            $DOCKER_COMPOSE logs -f n8n 2>&1 | grep --line-buffered -E "webhook|Webhook|/webhook/" | while read line; do
                                echo "[$(date '+%H:%M:%S')] $line"
                            done
                            ;;
                        executions)
                            echo -e "${BLUE}Monitoring workflow executions...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            echo "Real-time execution monitoring (Ctrl+C to stop):"
                            echo ""
                            
                            # Use our execution helper for real-time monitoring
                            $DOCKER_COMPOSE exec -T n8n sh -c "while true; do clear; echo '=== n8n Execution Monitor ==='; echo ''; n8n-exec query last 10; echo ''; echo '=== Currently Running ==='; n8n-exec query running; sleep 2; done"
                            ;;
                        errors)
                            echo -e "${BLUE}Monitoring n8n errors...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            echo "Watching for errors (Ctrl+C to stop):"
                            echo ""
                            $DOCKER_COMPOSE logs -f n8n 2>&1 | grep --line-buffered -iE "error|fail|exception|warn" | while read line; do
                                if echo "$line" | grep -qi "error\|fail\|exception"; then
                                    echo -e "[$(date '+%H:%M:%S')] ${RED}✗${NC} $line"
                                else
                                    echo -e "[$(date '+%H:%M:%S')] ${YELLOW}⚠${NC} $line"
                                fi
                            done
                            ;;
                        *)
                            echo "Usage: ./dev n8n monitor {logs|webhooks|executions|errors} [filter]"
                            echo ""
                            echo "Commands:"
                            echo "  logs       - Monitor all n8n logs (optional filter)"
                            echo "  webhooks   - Monitor webhook activity"
                            echo "  executions - Monitor workflow executions"
                            echo "  errors     - Monitor errors and warnings"
                            echo ""
                            echo "Examples:"
                            echo "  ./dev n8n monitor logs                # All logs"
                            echo "  ./dev n8n monitor logs 'webhook'      # Filtered logs"
                            echo "  ./dev n8n monitor executions          # Execution activity"
                            echo "  ./dev n8n monitor errors              # Errors only"
                            echo ""
                            echo "Press Ctrl+C to stop monitoring"
                            ;;
                    esac
                    ;;
                query)
                    case "$3" in
                        status)
                            if [ "$OUTPUT_FORMAT" != "json" ]; then
                                echo -e "${BLUE}Querying n8n status...${NC}"
                            fi
                            if ! check_service_running "n8n" "true"; then
                                if [ "$OUTPUT_FORMAT" = "json" ]; then
                                    echo '{"status":"error","service":"n8n","message":"Service is not running"}'
                                else
                                    echo -e "${RED}✗ n8n is not running${NC}"
                                fi
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            # Check health endpoint
                            health_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${N8N_PORT:-8100}/healthz")
                            if echo "$health_status" | grep -q "200"; then
                                health_ok=true
                            else
                                health_ok=false
                            fi
                            
                            if [ "$OUTPUT_FORMAT" = "json" ]; then
                                echo "{\"status\":\"success\",\"service\":\"n8n\",\"running\":true,\"health\":$health_ok}"
                            else
                                echo -e "${GREEN}✓ n8n is running${NC}"
                                echo ""
                                if [ "$health_ok" = true ]; then
                                    echo -e "${GREEN}✓ Health check: OK${NC}"
                                else
                                    echo -e "${RED}✗ Health check: Failed${NC}"
                                fi
                            fi
                            
                            if [ "$OUTPUT_FORMAT" != "json" ]; then
                                # Get version
                                echo ""
                                echo -n "Version: "
                                $DOCKER_COMPOSE exec -T n8n n8n --version 2>/dev/null || echo "Unknown"
                                
                                # Count workflows
                                echo ""
                                workflow_count=$($DOCKER_COMPOSE exec -T n8n n8n list:workflow 2>/dev/null | grep -c "|" || echo 0)
                                echo "Active workflows: $workflow_count"
                                
                                # Check custom nodes
                                echo ""
                                if $DOCKER_COMPOSE exec -T n8n test -d /data/.n8n/custom 2>/dev/null; then
                                    node_count=$($DOCKER_COMPOSE exec -T n8n ls /data/.n8n/custom/ 2>/dev/null | wc -l || echo 0)
                                    echo "Custom nodes installed: $node_count"
                                else
                                    echo "Custom nodes: None"
                                fi
                            fi
                            ;;
                        webhook-url)
                            echo -e "${BLUE}n8n Webhook URLs:${NC}"
                            echo ""
                            
                            # Get from environment
                            webhook_id="${N8N_WEBHOOK_ID:-c188c31c-1c45-4118-9ece-5b6057ab5177}"
                            port="${N8N_PORT:-8100}"
                            
                            echo "Production webhook URL:"
                            echo "  http://localhost:$port/webhook/$webhook_id"
                            echo ""
                            echo "Test webhook URL:"
                            echo "  http://localhost:$port/webhook-test/$webhook_id"
                            echo ""
                            echo "Internal (container) URL:"
                            echo "  http://n8n:5678/webhook/$webhook_id"
                            echo ""
                            echo "To test webhook:"
                            echo "  curl -X POST http://localhost:$port/webhook/$webhook_id \\"
                            echo "    -H 'Content-Type: application/json' \\"
                            echo "    -d '{\"test\": \"data\"}'"
                            ;;
                        last-execution)
                            echo -e "${BLUE}Querying last execution details...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            echo ""
                            # Query SQLite database directly
                            $DOCKER_COMPOSE exec -T n8n sqlite3 -header -column /data/.n8n/database.sqlite \
                                "SELECT id, workflowId, status, datetime(startedAt/1000, 'unixepoch') as started 
                                 FROM execution_entity 
                                 ORDER BY startedAt DESC 
                                 LIMIT ${4:-5}" 2>/dev/null || echo "No executions found"
                            ;;
                        active-workflows)
                            echo -e "${BLUE}Querying active workflows...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            echo ""
                            echo "Active workflows:"
                            $DOCKER_COMPOSE exec -T n8n n8n list:workflow 2>&1 | grep -v "User settings\|Error tracking" | while IFS='|' read -r id name; do
                                if [ ! -z "$id" ] && [ "$id" != "ID" ]; then
                                    # Trim whitespace
                                    id=$(echo "$id" | xargs)
                                    name=$(echo "$name" | xargs)
                                    
                                    # Try to get workflow details using n8n CLI
                                    echo ""
                                    echo "  ID: $id"
                                    echo "  Name: $name"
                                    
                                    # Check if workflow is active by trying to get its status from database
                                    if $DOCKER_COMPOSE exec -T n8n test -f /data/.n8n/database.sqlite 2>/dev/null; then
                                        active=$($DOCKER_COMPOSE exec -T n8n sqlite3 /data/.n8n/database.sqlite \
                                            "SELECT active FROM workflow_entity WHERE id = '$id';" 2>/dev/null)
                                        if [ "$active" = "1" ]; then
                                            echo -e "  Status: ${GREEN}Active${NC}"
                                        else
                                            echo -e "  Status: ${YELLOW}Inactive${NC}"
                                        fi
                                    fi
                                fi
                            done
                            ;;
                        running-executions)
                            echo -e "${BLUE}Querying running executions...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            echo ""
                            $DOCKER_COMPOSE exec -T n8n sqlite3 -header -column /data/.n8n/database.sqlite \
                                "SELECT id, workflowId, datetime(startedAt/1000, 'unixepoch') as started 
                                 FROM execution_entity 
                                 WHERE finished = 0 
                                 ORDER BY startedAt DESC" 2>/dev/null || echo "No running executions"
                            ;;
                        failed-executions)
                            echo -e "${BLUE}Querying failed executions...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            echo ""
                            $DOCKER_COMPOSE exec -T n8n sqlite3 -header -column /data/.n8n/database.sqlite \
                                "SELECT id, workflowId, status, datetime(startedAt/1000, 'unixepoch') as started 
                                 FROM execution_entity 
                                 WHERE status = 'failed' OR status = 'crashed' 
                                 ORDER BY startedAt DESC 
                                 LIMIT ${4:-10}" 2>/dev/null || echo "No failed executions"
                            ;;
                        execution-stats)
                            if [ "$OUTPUT_FORMAT" != "json" ]; then
                                echo -e "${BLUE}Querying execution statistics...${NC}"
                            fi
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            # Get statistics
                            total=$($DOCKER_COMPOSE exec -T n8n sqlite3 /data/.n8n/database.sqlite \
                                "SELECT COUNT(*) FROM execution_entity" 2>/dev/null || echo "0")
                            successful=$($DOCKER_COMPOSE exec -T n8n sqlite3 /data/.n8n/database.sqlite \
                                "SELECT COUNT(*) FROM execution_entity WHERE status = 'success'" 2>/dev/null || echo "0")
                            failed=$($DOCKER_COMPOSE exec -T n8n sqlite3 /data/.n8n/database.sqlite \
                                "SELECT COUNT(*) FROM execution_entity WHERE status = 'failed' OR status = 'crashed'" 2>/dev/null || echo "0")
                            
                            if [ "$OUTPUT_FORMAT" = "json" ]; then
                                echo "{\"total\":$total,\"successful\":$successful,\"failed\":$failed}"
                            else
                                echo ""
                                echo "Total Executions: $total"
                                echo "Successful: $successful"
                                echo "Failed: $failed"
                            fi
                            ;;
                        execution-details)
                            if [ -z "$4" ]; then
                                echo "Usage: ./dev n8n query execution-details <execution-id>"
                                exit 1
                            fi
                            
                            echo -e "${BLUE}Querying execution details for $4...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            echo ""
                            $DOCKER_COMPOSE exec -T n8n sqlite3 -header -column /data/.n8n/database.sqlite \
                                "SELECT id, workflowId, status, mode, 
                                        datetime(startedAt/1000, 'unixepoch') as started,
                                        datetime(stoppedAt/1000, 'unixepoch') as stopped
                                 FROM execution_entity 
                                 WHERE id = '$4'" 2>/dev/null || echo "Execution not found"
                            ;;
                        workflow-info)
                            echo -e "${BLUE}Querying workflow information...${NC}"
                            if ! check_service_running "n8n"; then
                                exit $EXIT_SERVICE_UNAVAILABLE
                            fi
                            
                            echo ""
                            if [ -z "$4" ]; then
                                $DOCKER_COMPOSE exec -T n8n sqlite3 -header -column /data/.n8n/database.sqlite \
                                    "SELECT id, name, active FROM workflow_entity ORDER BY name" 2>/dev/null || echo "No workflows found"
                            else
                                $DOCKER_COMPOSE exec -T n8n sqlite3 -header -column /data/.n8n/database.sqlite \
                                    "SELECT id, name, active FROM workflow_entity WHERE id = '$4'" 2>/dev/null || echo "Workflow not found"
                            fi
                            ;;
                        api-status)
                            echo -e "${BLUE}Checking n8n API status...${NC}"
                            port="${N8N_PORT:-8100}"
                            
                            echo ""
                            echo "API Endpoints:"
                            
                            # Check main API
                            echo -n "  REST API: "
                            if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/rest/workflows" | grep -q "401\|403"; then
                                echo -e "${YELLOW}Protected (authentication required)${NC}"
                            elif curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/rest/workflows" | grep -q "200"; then
                                echo -e "${GREEN}Open (no authentication)${NC}"
                            else
                                echo -e "${RED}Not accessible${NC}"
                            fi
                            
                            # Check public API
                            echo -n "  Public API: "
                            if curl -s "http://localhost:$port/api/v1" 2>&1 | grep -q "Cannot GET"; then
                                echo -e "${RED}Disabled${NC}"
                            else
                                echo -e "${GREEN}Enabled${NC}"
                            fi
                            
                            # Check Swagger UI
                            echo -n "  Swagger UI: "
                            if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/api/v1/docs/" | grep -q "200"; then
                                echo -e "${GREEN}Available at http://localhost:$port/api/v1/docs/${NC}"
                            else
                                echo -e "${YELLOW}Not available${NC}"
                            fi
                            
                            echo ""
                            echo "To enable API access, set in docker-compose.yml:"
                            echo "  N8N_PUBLIC_API_DISABLED=false"
                            echo "  N8N_PUBLIC_API_SWAGGERUI_DISABLED=false"
                            ;;
                        *)
                            echo "Usage: ./dev n8n query {status|webhook-url|last-execution|running-executions|failed-executions|execution-stats|execution-details|workflow-info|active-workflows|api-status}"
                            echo ""
                            echo "Commands:"
                            echo "  status              - Query n8n service status and stats"
                            echo "  webhook-url         - Display webhook URLs for testing"
                            echo "  last-execution [n]  - Show details of last n executions (default: 5)"
                            echo "  running-executions  - Show currently running executions"
                            echo "  failed-executions   - Show failed executions"
                            echo "  execution-stats     - Display execution statistics"
                            echo "  execution-details   - Get details of specific execution"
                            echo "  workflow-info [id]  - Get workflow information"
                            echo "  active-workflows    - List active workflows with status"
                            echo "  api-status          - Check API endpoint availability"
                            echo ""
                            echo "Examples:"
                            echo "  ./dev n8n query last-execution 10"
                            echo "  ./dev n8n query execution-details abc123"
                            echo "  ./dev n8n query workflow-info"
                            ;;
                    esac
                    ;;
                *)
                    echo "Usage: ./dev n8n {setup|workflows|nodes|cli|credentials|executions|env|test|monitor|query} [command]"
                    echo ""
                    echo "Subcommands:"
                    echo "  setup       - Auto-setup n8n owner account and activate workflows"
                    echo "  workflows   - Manage workflows (list, import, export, execute, activate/deactivate)"
                    echo "  nodes       - Manage custom nodes (list, build, verify)"
                    echo "  credentials - Manage credentials (export, import, backup)"
                    echo "  executions  - View workflow executions"
                    echo "  env         - Manage environment variables"
                    echo "  test        - Test n8n functionality (webhooks)"
                    echo "  monitor     - Continuous monitoring (logs, webhooks, executions, errors)"
                    echo "  query       - Query n8n status and configuration"
                    echo "  cli         - Pass commands directly to n8n CLI"
                    echo ""
                    echo "Examples:"
                    echo "  ./dev n8n workflows list             # List all workflows"
                    echo "  ./dev n8n env list                   # List container env vars"
                    echo "  ./dev n8n monitor executions         # Watch workflow executions"
                    echo "  ./dev n8n query status               # Check n8n status"
                    echo "  ./dev n8n credentials backup          # Backup all credentials"
                    ;;
            esac
}

# Export function
export -f handle_n8n_command
