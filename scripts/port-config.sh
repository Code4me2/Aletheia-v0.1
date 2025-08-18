#!/bin/bash
# Centralized port configuration loader

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source environment file if exists
if [ -f "${SCRIPT_DIR}/../.env" ]; then
    source "${SCRIPT_DIR}/../.env"
fi

# Export default ports if not set
export WEB_PORT=${WEB_PORT:-8080}
export N8N_PORT=${N8N_PORT:-8100}
export LAWYER_CHAT_PORT=${LAWYER_CHAT_PORT:-8101}
export AI_PORTAL_PORT=${AI_PORTAL_PORT:-8102}
export POSTGRES_PORT=${POSTGRES_PORT:-8200}
export REDIS_PORT=${REDIS_PORT:-8201}
export ELASTICSEARCH_PORT=${ELASTICSEARCH_PORT:-8202}
export HAYSTACK_PORT=${HAYSTACK_PORT:-8500}
export BITNET_PORT=${BITNET_PORT:-8501}
export PROMETHEUS_PORT=${PROMETHEUS_PORT:-8300}
export GRAFANA_PORT=${GRAFANA_PORT:-8301}

# Helper functions
get_service_url() {
    local service=$1
    case $service in
        web) echo "http://localhost:${WEB_PORT}" ;;
        n8n) echo "http://localhost:${WEB_PORT}/n8n" ;;
        chat) echo "http://localhost:${WEB_PORT}/chat" ;;
        ai-portal) echo "http://localhost:${WEB_PORT}/portal" ;;
        haystack) echo "http://localhost:${HAYSTACK_PORT}" ;;
        *) echo "http://localhost:${WEB_PORT}" ;;
    esac
}
