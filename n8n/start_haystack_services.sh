#!/bin/bash

echo "🚀 Starting Haystack Services for Judicial Access"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if we're in the n8n directory or if we can find the compose files
if [ -f "$SCRIPT_DIR/docker-compose.haystack.yml" ]; then
    # Script is in the correct location
    cd "$SCRIPT_DIR/.."
elif [ -f "docker-compose.haystack.yml" ] && [ -f "../docker-compose.yml" ]; then
    # We're already in the n8n directory
    cd ..
else
    echo "❌ Error: Cannot find docker-compose files. Please run this script from the n8n directory."
    echo "   Current directory: $(pwd)"
    echo "   Expected files: docker-compose.haystack.yml and ../docker-compose.yml"
    exit 1
fi

# Verify we're in the correct directory
if [ ! -f "docker-compose.yml" ] || [ ! -f "n8n/docker-compose.haystack.yml" ]; then
    echo "❌ Error: Not in the correct directory structure."
    echo "   Current directory: $(pwd)"
    echo "   Missing required files."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if main services are running
if ! docker-compose ps | grep -q "n8n.*Up"; then
    echo "⚠️  Main n8n services are not running. Starting them first..."
    docker-compose up -d
    sleep 10
fi

# Start Haystack services using both compose files
echo "📦 Starting Haystack and Elasticsearch services..."
docker-compose -f docker-compose.yml -f n8n/docker-compose.haystack.yml up -d elasticsearch haystack-service

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 15

# Setup Elasticsearch index
echo "🔧 Setting up Elasticsearch index..."
if [ -f "n8n/haystack-service/elasticsearch_setup.py" ]; then
    cd n8n/haystack-service
    python3 elasticsearch_setup.py
    cd ../..
else
    echo "  ⚠️  Warning: elasticsearch_setup.py not found, skipping index setup"
fi

# Source port configuration
if [ -f "../scripts/port-config.sh" ]; then
    source ../scripts/port-config.sh
else
    # Default ports if config not found
    WEB_PORT=${WEB_PORT:-8080}
    ELASTICSEARCH_PORT=${ELASTICSEARCH_PORT:-9200}
    HAYSTACK_PORT=${HAYSTACK_PORT:-8000}
fi

# Check service health
echo "🏥 Checking service health..."
echo "Elasticsearch:" 
curl -s http://localhost:${ELASTICSEARCH_PORT}/_cluster/health | python3 -m json.tool 2>/dev/null || echo "  ⚠️  Elasticsearch not ready yet"
echo -e "\nHaystack Service:"
curl -s http://localhost:${HAYSTACK_PORT}/health | python3 -m json.tool 2>/dev/null || echo "  ⚠️  Haystack service not ready yet"

echo ""
echo "✅ Haystack services are starting!"
echo "🌐 n8n UI: http://localhost:${WEB_PORT}/n8n/"
echo "🔍 Elasticsearch: http://localhost:${ELASTICSEARCH_PORT}"
echo "🤖 Haystack API: http://localhost:${HAYSTACK_PORT}"
echo "📚 API docs: http://localhost:${HAYSTACK_PORT}/docs"
echo ""
echo "💡 To stop all services: docker-compose -f docker-compose.yml -f n8n/docker-compose.haystack.yml down"