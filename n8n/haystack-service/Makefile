.PHONY: help start stop restart status logs test load-test clear console clean dev

# Default target
help:
	@echo "Haystack Service Development Commands:"
	@echo "  make start          - Start Haystack + Elasticsearch"
	@echo "  make start-dev      - Start in standalone mode with debug logging"
	@echo "  make stop           - Stop services"
	@echo "  make restart        - Restart services"
	@echo "  make status         - Check service status"
	@echo "  make logs           - View service logs"
	@echo "  make test           - Run functionality test"
	@echo "  make load-test      - Load test dataset (100 docs)"
	@echo "  make clear          - Clear all documents"
	@echo "  make console        - Start interactive Python console"
	@echo "  make clean          - Stop services and clear data"

# Service management
start:
	@./cli start

start-dev:
	@echo "Starting in development mode (standalone, debug logging)..."
	@HAYSTACK_MODE=standalone LOG_LEVEL=DEBUG ./cli start

stop:
	@./cli stop

restart: stop start

status:
	@./cli status

logs:
	@./cli logs -f

# Data management  
load-test:
	@echo "Loading test dataset..."
	@./cli load test --limit 100

load-small:
	@echo "Loading small test dataset..."
	@./cli load test --limit 10

load-large:
	@echo "Loading large test dataset..."
	@./cli load test --limit 1000

clear:
	@./cli clear

# Development tools
test:
	@./cli test

console:
	@./cli console

search:
	@./cli search "legal document" --limit 5

# Elasticsearch operations
es-indices:
	@./cli es indices

es-stats:
	@./cli es stats

es-health:
	@curl -s http://localhost:9200/_cluster/health | python3 -m json.tool

# Clean everything
clean: stop clear
	@echo "Cleanup complete"

# Development workflow shortcuts
dev: start-dev load-test
	@echo "Development environment ready!"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	@echo "Elasticsearch: http://localhost:9200"

# Quick API tests
api-health:
	@curl -s http://localhost:8000/health | python3 -m json.tool

api-search:
	@curl -s -X POST http://localhost:8000/search \
		-H "Content-Type: application/json" \
		-d '{"query": "legal", "search_type": "hybrid", "top_k": 3}' \
		| python3 -m json.tool

# Docker shortcuts
docker-logs-haystack:
	@docker logs haystack-judicial -f

docker-logs-es:
	@docker logs elasticsearch-judicial -f

docker-stats:
	@docker stats haystack-judicial elasticsearch-judicial

# Testing different search types
test-bm25:
	@echo "Testing BM25 search..."
	@./cli search "contract law" --type bm25 --limit 3

test-vector:
	@echo "Testing vector search..."
	@./cli search "legal precedent" --type vector --limit 3

test-hybrid:
	@echo "Testing hybrid search..."
	@./cli search "constitutional rights" --type hybrid --limit 3

test-all-search: test-bm25 test-vector test-hybrid

# Dataset management
datasets-create:
	@mkdir -p datasets
	@echo "Creating sample datasets..."
	@python3 scripts/generate-datasets.py

datasets-list:
	@echo "Available datasets:"
	@ls -la datasets/

# Installation check
check-deps:
	@echo "Checking Python dependencies..."
	@python3 -c "import click; print('✓ click installed')" || echo "✗ click missing"
	@python3 -c "import requests; print('✓ requests installed')" || echo "✗ requests missing"
	@python3 -c "import elasticsearch; print('✓ elasticsearch installed')" || echo "✗ elasticsearch missing"
	@python3 -c "import psycopg2; print('✓ psycopg2 installed')" || echo "✗ psycopg2 missing"

install-deps:
	@echo "Installing required Python packages..."
	@pip install click requests elasticsearch psycopg2-binary

# Performance testing
perf-test:
	@echo "Running performance test..."
	@python3 scripts/performance-test.py

# Backup and restore
backup:
	@echo "Backing up Elasticsearch data..."
	@mkdir -p backups
	@curl -s -X GET "http://localhost:9200/legal-documents-rag/_search?size=10000" \
		| python3 -m json.tool > backups/backup-$$(date +%Y%m%d-%H%M%S).json
	@echo "Backup saved to backups/"

restore:
	@echo "To restore, use: ./cli load file --file backups/backup-TIMESTAMP.json"