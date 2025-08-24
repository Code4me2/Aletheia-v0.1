# Data Compose Makefile
# DEPRECATED: Use ./dev CLI instead (run: ./dev help)
# This file is kept for backwards compatibility only

.PHONY: help dev dev-services dev-website stop restart clean build test lint format setup health logs

# Default target - show help
help:
	@echo "⚠️  DEPRECATION WARNING: Makefile commands are deprecated!"
	@echo "=================================================="
	@echo "Please use the ./dev CLI instead:"
	@echo ""
	@echo "  ./dev help     - Show all available commands"
	@echo "  ./dev up       - Start all services"
	@echo "  ./dev down     - Stop all services"
	@echo "  ./dev status   - Check service status"
	@echo "  ./dev test     - Run tests"
	@echo ""
	@echo "See DEVELOPER_GUIDE.md for details."
	@echo "=================================================="
	@echo ""
	@echo "Legacy Makefile Commands (will be removed):"
	@echo "================================="
	@echo "Setup & Development:"
	@echo "  make setup          - Initial project setup (install deps, init DBs)"
	@echo "  make dev            - Start all services and website development"
	@echo "  make dev-services   - Start only Docker services (n8n, DB, nginx)"
	@echo "  make dev-website    - Start only website development server"
	@echo "  make stop           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo ""
	@echo "Building & Testing:"
	@echo "  make build          - Build all components"
	@echo "  make test           - Run all tests"
	@echo "  make test-coverage  - Run tests with coverage"
	@echo "  make lint           - Run linting"
	@echo "  make lint-fix       - Run linting with auto-fix"
	@echo "  make format         - Format all code"
	@echo ""
	@echo "Database & Logs:"
	@echo "  make db-init        - Initialize databases"
	@echo "  make logs           - Follow all service logs"
	@echo "  make logs-n8n       - Follow n8n logs only"
	@echo "  make logs-web       - Follow web service logs only"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make clean-all      - Clean everything (including Docker volumes)"
	@echo "  make health         - Check service health"
	@echo "  make update         - Update all dependencies"

# Initial setup
setup:
	@echo "🚀 Setting up Data Compose project..."
	npm install
	cp -n .env.example .env || true
	@echo "✅ Dependencies installed"
	@echo "📝 Please edit .env file with your configuration"
	@echo "🔄 Initializing databases..."
	make db-init
	@echo "✨ Setup complete! Run 'make dev' to start development"

# Development commands
dev: dev-services
	@echo "🚀 Starting website development server..."
	npm run dev:website

dev-services:
	@echo "🐳 Starting Docker services..."
	docker-compose up -d
	@echo "⏳ Waiting for services to be healthy..."
	@sleep 5
	make health

dev-website:
	@echo "🌐 Starting website development only..."
	npm run dev:website

# Service management
stop:
	@echo "🛑 Stopping all services..."
	docker-compose down
	@echo "✅ All services stopped"

restart:
	@echo "🔄 Restarting all services..."
	make stop
	make dev-services

# Building
build:
	@echo "🔨 Building all components..."
	docker-compose build
	npm run build
	@echo "✅ Build complete"

build-nodes:
	@echo "🔧 Building n8n custom nodes..."
	npm run build:nodes

# Testing
test:
	@echo "🧪 Running tests..."
	npm test

test-coverage:
	@echo "📊 Running tests with coverage..."
	npm run test:coverage

test-watch:
	@echo "👀 Running tests in watch mode..."
	npm run test:watch

# Code quality
lint:
	@echo "🔍 Running linters..."
	npm run lint

lint-fix:
	@echo "🔧 Running linters with auto-fix..."
	npm run lint:fix

format:
	@echo "✨ Formatting code..."
	npm run format

format-check:
	@echo "🔍 Checking code formatting..."
	npm run format:check

# Database operations
db-init:
	@echo "🗄️  Initializing databases..."
	bash scripts/init-databases.sh

db-backup:
	@echo "💾 Backing up databases..."
	mkdir -p backups
	docker-compose exec -T db pg_dump -U ${DB_USER:-postgres} ${DB_NAME:-mydb} > backups/db_backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backed up to backups/"

db-restore:
	@echo "📥 Restoring database from backup..."
	@echo "Usage: make db-restore FILE=backups/db_backup_YYYYMMDD_HHMMSS.sql"
	@test -n "$(FILE)" || (echo "❌ Please specify FILE=path/to/backup.sql" && exit 1)
	docker-compose exec -T db psql -U ${DB_USER:-postgres} ${DB_NAME:-mydb} < $(FILE)

# Logging
logs:
	@echo "📜 Following all service logs..."
	docker-compose logs -f

logs-n8n:
	@echo "📜 Following n8n logs..."
	docker-compose logs -f n8n

logs-web:
	@echo "📜 Following web service logs..."
	docker-compose logs -f web

logs-db:
	@echo "📜 Following database logs..."
	docker-compose logs -f db

# Maintenance
clean:
	@echo "🧹 Cleaning build artifacts..."
	npm run clean
	find . -name "dist" -type d -prune -exec rm -rf {} +
	find . -name ".next" -type d -prune -exec rm -rf {} +
	find . -name "coverage" -type d -prune -exec rm -rf {} +
	@echo "✅ Build artifacts cleaned"

clean-all: clean
	@echo "🗑️  Cleaning everything (including Docker volumes)..."
	docker-compose down -v
	find . -name "node_modules" -type d -prune -exec rm -rf {} +
	@echo "✅ Everything cleaned"

health:
	@echo "🏥 Checking service health..."
	@curl -sf http://localhost:8080/n8n/healthz > /dev/null && echo "✅ n8n is healthy" || echo "❌ n8n is not responding"
	@curl -sf http://localhost:8080 > /dev/null && echo "✅ Web server is healthy" || echo "❌ Web server is not responding"
	@docker-compose exec -T db pg_isready -U ${DB_USER:-postgres} > /dev/null && echo "✅ Database is healthy" || echo "❌ Database is not responding"

update:
	@echo "📦 Updating dependencies..."
	npm update
	npm audit fix
	@echo "✅ Dependencies updated"

# Docker shortcuts
docker-ps:
	@docker-compose ps

docker-shell-n8n:
	@echo "🐚 Opening shell in n8n container..."
	docker-compose exec n8n /bin/sh

docker-shell-web:
	@echo "🐚 Opening shell in web container..."
	docker-compose exec web /bin/sh

docker-shell-db:
	@echo "🐚 Opening PostgreSQL shell..."
	docker-compose exec db psql -U ${DB_USER:-postgres} ${DB_NAME:-mydb}

# Git helpers
git-status:
	@git status

git-commit:
	@echo "📝 Creating commit with conventional format..."
	@echo "Use format: type(scope): description"
	@echo "Types: feat, fix, docs, style, refactor, test, chore"
	git add -A && git commit

# Development workflow shortcuts
work-start: dev
	@echo "💼 Development environment ready!"
	@echo "- Web UI: http://localhost:8080"
	@echo "- n8n UI: http://localhost:8080/n8n/"
	@echo "- Logs: make logs"

work-stop: stop
	@echo "👋 Development environment stopped. Have a great day!"