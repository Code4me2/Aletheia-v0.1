#!/bin/bash

# ============================================================================
# Dev CLI Common Functions Library
# ============================================================================
# This module contains shared functions used across all dev CLI commands
# Source this file in other modules: source "$(dirname "$0")/dev-modules/dev-lib.sh"

# Exit codes for consistent error handling
readonly EXIT_SUCCESS=0
readonly EXIT_CONFIG_ERROR=1
readonly EXIT_SERVICE_UNAVAILABLE=2
readonly EXIT_PERMISSION_DENIED=3
readonly EXIT_RESOURCE_ERROR=4
readonly EXIT_USER_CANCELLED=5

# Check if database is ready
check_db_ready() {
    local db_user="${DB_USER:-aletheia}"
    local db_name="${DB_NAME:-aletheia}"
    
    if ! $DOCKER_COMPOSE exec -T db pg_isready -U "$db_user" &>/dev/null; then
        if [ "$OUTPUT_FORMAT" = "json" ]; then
            echo '{"status":"error","message":"Database is not running"}'
        else
            echo -e "${RED}✗ Database is not running${NC}"
            echo "  Start the database with: ./dev up db"
        fi
        return $EXIT_SERVICE_UNAVAILABLE
    fi
    return $EXIT_SUCCESS
}

# Check if a service is running
check_service_running() {
    local service="$1"
    local quiet="${2:-false}"
    
    if ! $DOCKER_COMPOSE ps "$service" 2>/dev/null | grep -q "Up\|Running"; then
        if [ "$quiet" != "true" ]; then
            if [ "$OUTPUT_FORMAT" = "json" ]; then
                echo "{\"status\":\"error\",\"service\":\"$service\",\"message\":\"Service is not running\"}"
            else
                echo -e "${YELLOW}$service is not running. Start it with: ./dev up $service${NC}"
            fi
        fi
        return $EXIT_SERVICE_UNAVAILABLE
    fi
    return $EXIT_SUCCESS
}

# Wait for a service to be ready
wait_for_service() {
    local service="$1"
    local max_wait="${2:-30}"
    local check_command="${3:-}"
    
    echo -e "${BLUE}Waiting for $service to be ready...${NC}"
    
    local count=0
    while [ $count -lt $max_wait ]; do
        if [ -n "$check_command" ]; then
            if eval "$check_command" &>/dev/null; then
                echo -e "${GREEN}✓ $service is ready${NC}"
                return $EXIT_SUCCESS
            fi
        else
            if check_service_running "$service" true; then
                echo -e "${GREEN}✓ $service is ready${NC}"
                return $EXIT_SUCCESS
            fi
        fi
        echo -n "."
        sleep 1
        count=$((count + 1))
    done
    
    echo ""
    echo -e "${RED}✗ $service failed to start within ${max_wait} seconds${NC}"
    return $EXIT_SERVICE_UNAVAILABLE
}

# Get container name for a service
get_container_name() {
    local service="$1"
    $DOCKER_COMPOSE ps -q "$service" 2>/dev/null | head -1
}

# Output in JSON format if requested
output_result() {
    local status="$1"
    local message="$2"
    local data="${3:-}"
    
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        if [ -n "$data" ]; then
            echo "{\"status\":\"$status\",\"message\":\"$message\",\"data\":$data}"
        else
            echo "{\"status\":\"$status\",\"message\":\"$message\"}"
        fi
    else
        if [ "$status" = "success" ]; then
            echo -e "${GREEN}✓ $message${NC}"
        elif [ "$status" = "error" ]; then
            echo -e "${RED}✗ $message${NC}"
        elif [ "$status" = "warning" ]; then
            echo -e "${YELLOW}⚠ $message${NC}"
        else
            echo "$message"
        fi
    fi
}

# Execute command with retry logic
retry_command() {
    local cmd="$1"
    local max_attempts="${2:-3}"
    local delay="${3:-2}"
    
    for i in $(seq 1 $max_attempts); do
        if eval "$cmd"; then
            return $EXIT_SUCCESS
        fi
        
        if [ $i -lt $max_attempts ]; then
            echo "Attempt $i/$max_attempts failed, retrying in ${delay}s..."
            sleep $delay
        fi
    done
    
    return $EXIT_SERVICE_UNAVAILABLE
}

# Validate port availability
check_port() {
    local port="$1"
    local service="${2:-unknown}"
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        if [ "$OUTPUT_FORMAT" = "json" ]; then
            echo "{\"port\":$port,\"service\":\"$service\",\"status\":\"occupied\"}"
        else
            echo -e "${RED}✗ Port $port ($service) is already in use${NC}"
        fi
        return $EXIT_CONFIG_ERROR
    fi
    return $EXIT_SUCCESS
}

# Generate secure password
generate_password() {
    LC_ALL=C tr -dc 'A-Za-z0-9!@#%^&*()_+=' < /dev/urandom | head -c "${1:-32}"
}

# URL encode a string (for database passwords with special characters)
url_encode() {
    local string="$1"
    python3 -c "import urllib.parse; print(urllib.parse.quote('$string'))" 2>/dev/null || echo "$string"
}

# Check if Docker and docker-compose are installed
check_requirements() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        echo -e "${YELLOW}Please install Docker Desktop from: https://www.docker.com/products/docker-desktop${NC}"
        exit $EXIT_CONFIG_ERROR
    fi
    
    # Check for docker-compose (either standalone or plugin)
    if [ -z "$DOCKER_COMPOSE" ]; then
        echo -e "${RED}Error: docker-compose is not installed${NC}"
        echo -e "${YELLOW}Docker Compose should come with Docker Desktop. Please reinstall Docker Desktop.${NC}"
        exit $EXIT_CONFIG_ERROR
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker daemon is not running${NC}"
        echo -e "${YELLOW}Please start Docker Desktop first:${NC}"
        echo -e "  • On macOS: Open Docker Desktop from Applications"
        echo -e "  • On Linux: Run 'sudo systemctl start docker'"
        echo -e "  • On Windows: Open Docker Desktop from Start Menu"
        echo ""
        echo -e "${CYAN}After starting Docker, run this command again.${NC}"
        exit $EXIT_SERVICE_UNAVAILABLE
    fi
}

# Check if .env exists
check_env() {
    if [ ! -f .env ]; then
        if [ -f .env.required ]; then
            echo -e "${YELLOW}No .env file found. Creating from .env.required...${NC}"
            cp .env.required .env
            echo -e "${GREEN}Created .env file. Please edit it with your values.${NC}"
            echo -e "${YELLOW}Run './dev up' when ready.${NC}"
            exit $EXIT_CONFIG_ERROR
        else
            echo -e "${RED}No .env file found!${NC}"
            echo "Please create one with at least these variables:"
            echo "  DB_PASSWORD=<your_password>"
            echo "  N8N_ENCRYPTION_KEY=<your_key>"
            echo "  NEXTAUTH_SECRET=<your_secret>"
            exit $EXIT_CONFIG_ERROR
        fi
    fi
}

# Print a section header
print_header() {
    local title="$1"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  $title${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
}

# Confirm dangerous operation
confirm_operation() {
    local message="$1"
    local default="${2:-N}"
    
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        # In JSON mode, skip confirmations
        return $EXIT_SUCCESS
    fi
    
    echo -e "${YELLOW}$message${NC}"
    
    if [ "$default" = "Y" ]; then
        echo -n "Are you sure? (Y/n): "
    else
        echo -n "Are you sure? (y/N): "
    fi
    
    read -r response
    
    if [ "$default" = "Y" ]; then
        if [[ "$response" =~ ^[Nn]$ ]]; then
            return $EXIT_USER_CANCELLED
        fi
    else
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            return $EXIT_USER_CANCELLED
        fi
    fi
    
    return $EXIT_SUCCESS
}

# Export all functions for use in subshells
export -f check_db_ready
export -f check_service_running
export -f wait_for_service
export -f get_container_name
export -f output_result
export -f retry_command
export -f check_port
export -f generate_password
export -f url_encode
export -f check_requirements
export -f check_env
export -f print_header
export -f confirm_operation