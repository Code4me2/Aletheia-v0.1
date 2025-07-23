#!/bin/bash

# Aletheia Deployment Script
# Provides easy deployment across different environments with flexible port management

set -e

# Default values
ENVIRONMENT="development"
ENABLE_MONITORING=false
ENABLE_LOAD_BALANCER=false
ENABLE_SSL=false
COMPOSE_FILES=()
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Usage information
usage() {
    cat << EOF
Aletheia Deployment Script

USAGE:
    $0 [OPTIONS] COMMAND

COMMANDS:
    up          Start services
    down        Stop services
    restart     Restart services
    status      Show service status
    logs        Show service logs
    clean       Clean up containers and volumes
    config      Show resolved configuration
    ports       Show port mappings for environment

OPTIONS:
    -e, --environment ENV    Environment (development|staging|production) [default: development]
    -m, --monitoring         Enable monitoring stack (Prometheus, Grafana, Loki)
    -l, --load-balancer      Enable load balancer (HAProxy)
    -s, --ssl                Enable SSL/TLS (production only)
    -v, --verbose            Verbose output
    -h, --help               Show this help

EXAMPLES:
    # Start development environment
    $0 up

    # Start staging with monitoring
    $0 -e staging -m up

    # Start production with full stack
    $0 -e production -m -l -s up

    # Check port mappings for staging
    $0 -e staging ports

    # View logs for specific service
    $0 -e development logs n8n
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -m|--monitoring)
                ENABLE_MONITORING=true
                shift
                ;;
            -l|--load-balancer)
                ENABLE_LOAD_BALANCER=true
                shift
                ;;
            -s|--ssl)
                ENABLE_SSL=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            up|down|restart|status|logs|clean|config|ports)
                COMMAND="$1"
                shift
                break
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Remaining arguments are passed to docker-compose
    EXTRA_ARGS=("$@")
}

# Validate environment
validate_environment() {
    case $ENVIRONMENT in
        development|staging|production)
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            log_error "Valid environments: development, staging, production"
            exit 1
            ;;
    esac
}

# Generate environment configuration
setup_environment() {
    log_info "Setting up $ENVIRONMENT environment..."
    
    # Generate environment-specific .env file
    if ! python3 scripts/generate-env.py "$ENVIRONMENT"; then
        log_error "Failed to generate environment configuration"
        exit 1
    fi
    
    # Copy generated .env file to main .env
    cp ".env.$ENVIRONMENT" .env
    log_success "Environment configuration loaded"
}

# Build compose file list
build_compose_files() {
    COMPOSE_FILES=("docker-compose.yml")
    
    # Add environment-specific overrides
    if $ENABLE_MONITORING || $ENABLE_LOAD_BALANCER; then
        COMPOSE_FILES+=("docker-compose.env.yml")
    fi
    
    # Add Haystack if needed
    if [[ -f "n8n/docker-compose.haystack.yml" ]]; then
        COMPOSE_FILES+=("n8n/docker-compose.haystack.yml")
    fi
    
    # Add environment-specific compose files
    case $ENVIRONMENT in
        staging)
            if [[ -f "docker-compose.staging.yml" ]]; then
                COMPOSE_FILES+=("docker-compose.staging.yml")
            fi
            ;;
        production)
            if [[ -f "docker-compose.production.yml" ]]; then
                COMPOSE_FILES+=("docker-compose.production.yml")
            fi
            ;;
    esac
    
    log_info "Using compose files: ${COMPOSE_FILES[*]}"
}

# Execute docker-compose command
execute_compose() {
    local cmd="$1"
    shift
    
    # Build docker-compose command
    local compose_cmd=("docker-compose")
    
    # Add all compose files
    for file in "${COMPOSE_FILES[@]}"; do
        compose_cmd+=("-f" "$file")
    done
    
    compose_cmd+=("$cmd" "$@")
    
    if $VERBOSE; then
        log_info "Executing: ${compose_cmd[*]}"
    fi
    
    "${compose_cmd[@]}"
}

# Show port mappings
show_ports() {
    log_info "Port mappings for $ENVIRONMENT environment:"
    python3 scripts/generate-env.py "$ENVIRONMENT" | grep -A 20 "Port summary"
}

# Check service health
check_health() {
    log_info "Checking service health..."
    
    local unhealthy_services=()
    
    # Get list of running services
    local services
    services=$(execute_compose ps --services --filter "status=running")
    
    for service in $services; do
        if ! execute_compose ps "$service" | grep -q "Up (healthy)"; then
            unhealthy_services+=("$service")
        fi
    done
    
    if [[ ${#unhealthy_services[@]} -eq 0 ]]; then
        log_success "All services are healthy"
    else
        log_warning "Unhealthy services: ${unhealthy_services[*]}"
    fi
}

# Main execution logic
main() {
    parse_args "$@"
    
    if [[ -z "$COMMAND" ]]; then
        log_error "No command specified"
        usage
        exit 1
    fi
    
    validate_environment
    setup_environment
    build_compose_files
    
    case $COMMAND in
        up)
            log_info "Starting Aletheia $ENVIRONMENT environment..."
            execute_compose up -d "${EXTRA_ARGS[@]}"
            sleep 5
            check_health
            log_success "Environment started successfully"
            show_ports
            ;;
        down)
            log_info "Stopping Aletheia $ENVIRONMENT environment..."
            execute_compose down "${EXTRA_ARGS[@]}"
            log_success "Environment stopped"
            ;;
        restart)
            log_info "Restarting Aletheia $ENVIRONMENT environment..."
            execute_compose restart "${EXTRA_ARGS[@]}"
            sleep 5
            check_health
            log_success "Environment restarted"
            ;;
        status)
            execute_compose ps "${EXTRA_ARGS[@]}"
            check_health
            ;;
        logs)
            execute_compose logs -f "${EXTRA_ARGS[@]}"
            ;;
        clean)
            log_warning "This will remove all containers and volumes"
            read -p "Are you sure? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                execute_compose down -v --remove-orphans
                docker system prune -f
                log_success "Cleanup completed"
            fi
            ;;
        config)
            execute_compose config "${EXTRA_ARGS[@]}"
            ;;
        ports)
            show_ports
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"