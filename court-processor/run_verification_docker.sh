#!/bin/bash
# Run external verification from within Docker network

echo "Running external verification from Docker network..."

# Mount current directory and run verification with network access
docker run --rm \
  --network aletheia_backend \
  -v "$(pwd):/app" \
  -w /app \
  -e COURTLISTENER_API_TOKEN="${COURTLISTENER_API_TOKEN}" \
  python:3.13 \
  bash -c "
    echo 'Installing dependencies...'
    pip install aiohttp requests psycopg2-binary psutil structlog python-dotenv typing-extensions courts-db reporters-db eyecite > /dev/null 2>&1
    
    echo 'Running verification...'
    python3 verify_external_endpoints.py
  "