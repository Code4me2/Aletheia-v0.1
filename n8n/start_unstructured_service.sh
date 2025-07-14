#!/bin/bash

echo "Starting Unstructured Services for Judicial Access"

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
docker-compose -f docker-compose.yml -f n8n/docker-compose.haystack.yml up -d unstructured-service

sleep 30
