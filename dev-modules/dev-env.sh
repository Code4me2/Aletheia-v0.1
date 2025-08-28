#!/bin/bash

# ============================================================================
# Dev CLI Environment Module
# ============================================================================
# This module contains commands for managing environment configuration

# Handle environment commands
handle_env_command() {
    local cmd="$1"
    shift
    
    case "$cmd" in
        check)
            env_check "$@"
            ;;
        list)
            env_list "$@"
            ;;
        ports)
            env_ports "$@"
            ;;
        *)
            if [ "$OUTPUT_FORMAT" = "json" ]; then
                echo '{"status":"error","message":"Unknown environment command"}'
            else
                echo "Usage: ./dev env [check|list]"
                echo "  check - Verify all required variables are set"
                echo "  list  - List all environment variables"
                echo ""
                echo "Or use: ./dev ports to show port configuration"
            fi
            return $EXIT_CONFIG_ERROR
            ;;
    esac
}

# Check environment configuration
env_check() {
    if [ "$OUTPUT_FORMAT" != "json" ]; then
        print_header "Environment Configuration Check"
    fi
    
    if [ ! -f .env ]; then
        if [ "$OUTPUT_FORMAT" = "json" ]; then
            echo '{"status":"error","message":"No .env file found"}'
        else
            echo -e "${RED}✗ No .env file found${NC}"
        fi
        return $EXIT_CONFIG_ERROR
    fi
    
    source .env
    
    # Required variables
    if [ "$OUTPUT_FORMAT" != "json" ]; then
        echo -e "${CYAN}Required Variables:${NC}"
    fi
    
    required_vars="DB_USER DB_PASSWORD DB_NAME N8N_ENCRYPTION_KEY NEXTAUTH_SECRET"
    missing=0
    missing_vars=""
    
    for var in $required_vars; do
        if [ -z "${!var}" ]; then
            if [ "$OUTPUT_FORMAT" != "json" ]; then
                echo -e "${RED}✗${NC} $var is not set"
            fi
            missing=$((missing + 1))
            missing_vars="$missing_vars $var"
        else
            if [ "$OUTPUT_FORMAT" != "json" ]; then
                if [[ "$var" == *"PASSWORD"* ]] || [[ "$var" == *"SECRET"* ]] || [[ "$var" == *"KEY"* ]]; then
                    echo -e "${GREEN}✓${NC} $var is set (hidden)"
                else
                    echo -e "${GREEN}✓${NC} $var = ${!var}"
                fi
            fi
        fi
    done
    
    # Optional variables
    if [ "$OUTPUT_FORMAT" != "json" ]; then
        echo ""
        echo -e "${CYAN}Port Configuration:${NC}"
        echo "  WEB_PORT = ${WEB_PORT:-8080}"
        echo "  N8N_PORT = ${N8N_PORT:-8100}"
        echo "  AI_PORTAL_PORT = ${AI_PORTAL_PORT:-8102}"
        echo "  POSTGRES_PORT = ${POSTGRES_PORT:-8200}"
        echo "  REDIS_PORT = ${REDIS_PORT:-8201}"
    fi
    
    # Security check
    security_warnings=0
    weak_password=false
    
    if [[ "$DB_PASSWORD" =~ ^(password|123456|admin|default|aletheia123|postgres)$ ]]; then
        weak_password=true
        security_warnings=$((security_warnings + 1))
        if [ "$OUTPUT_FORMAT" != "json" ]; then
            echo ""
            echo -e "${CYAN}Security Check:${NC}"
            echo -e "${YELLOW}⚠${NC}  DB_PASSWORD appears to be weak/default"
        fi
    else
        if [ "$OUTPUT_FORMAT" != "json" ]; then
            echo ""
            echo -e "${CYAN}Security Check:${NC}"
            echo -e "${GREEN}✓${NC} DB_PASSWORD appears strong"
        fi
    fi
    
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        echo "{\"status\":\"$([ $missing -eq 0 ] && echo 'success' || echo 'error')\",\"missing_count\":$missing,\"security_warnings\":$security_warnings,\"weak_password\":$weak_password}"
    else
        echo ""
        if [ $missing -eq 0 ]; then
            echo -e "${GREEN}✅ All required variables are set${NC}"
        else
            echo -e "${RED}✗ Missing $missing required variable(s)${NC}"
        fi
    fi
    
    [ $missing -eq 0 ] && return $EXIT_SUCCESS || return $EXIT_CONFIG_ERROR
}

# List environment variables
env_list() {
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        if [ -f .env ]; then
            echo -n '{"status":"success","variables":['
            first=true
            grep -E "^[A-Z]" .env | cut -d= -f1 | sort | while read var; do
                if [ "$first" = true ]; then
                    first=false
                else
                    echo -n ','
                fi
                echo -n "\"$var\""
            done
            echo ']}'
        else
            echo '{"status":"error","message":"No .env file found"}'
            return $EXIT_CONFIG_ERROR
        fi
    else
        echo -e "${BLUE}Environment variables in use:${NC}"
        if [ -f .env ]; then
            grep -E "^[A-Z]" .env | cut -d= -f1 | sort
        else
            echo -e "${RED}No .env file found${NC}"
            return $EXIT_CONFIG_ERROR
        fi
    fi
}

# Show port configuration
env_ports() {
    if [ "$OUTPUT_FORMAT" != "json" ]; then
        print_header "Port Configuration"
    fi
    
    if [ -f .env ]; then
        source .env
    fi
    
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        cat << EOF
{
  "status": "success",
  "ports": {
    "web": ${WEB_PORT:-8080},
    "n8n": ${N8N_PORT:-8100},
    "ai_portal": ${AI_PORTAL_PORT:-8102},
    "court_processor": ${COURT_PROCESSOR_PORT:-8104},
    "postgres": ${POSTGRES_PORT:-8200},
    "redis": ${REDIS_PORT:-8201},
    "docker_api": ${DOCKER_API_PORT:-5002},
    "recap_webhook": ${RECAP_WEBHOOK_PORT:-5001}
  }
}
EOF
    else
        echo -e "${CYAN}Configured Ports:${NC}"
        echo "  Web Interface:    ${WEB_PORT:-8080}"
        echo "  n8n:             ${N8N_PORT:-8100}"
        echo "  AI Portal:       ${AI_PORTAL_PORT:-8102}"
        echo "  Court Processor: ${COURT_PROCESSOR_PORT:-8104}"
        echo "  PostgreSQL:      ${POSTGRES_PORT:-8200}"
        echo "  Redis:           ${REDIS_PORT:-8201}"
        echo "  Docker API:      ${DOCKER_API_PORT:-5002}"
        echo "  RECAP Webhook:   ${RECAP_WEBHOOK_PORT:-5001}"
        echo ""
    fi
}

# Export functions
export -f handle_env_command
export -f env_check
export -f env_list
export -f env_ports