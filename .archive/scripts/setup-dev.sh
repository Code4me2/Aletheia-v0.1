#!/bin/bash
# Development environment setup script

set -e

echo "🚀 Setting up Data Compose development environment..."

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi

# Check Node version
NODE_VERSION=$(node -v | cut -d 'v' -f 2 | cut -d '.' -f 1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version is too old. Please install Node.js 18 or higher."
    exit 1
fi

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker."
    exit 1
fi

# Check for Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration"
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Set up husky
echo "🐺 Setting up Git hooks..."
npm run prepare || npx husky install

# Build custom nodes
echo "🔧 Building n8n custom nodes..."
npm run build:nodes || true

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs
mkdir -p backups
mkdir -p coverage
mkdir -p test-results

# Set up git-secrets if available
if command -v git-secrets &> /dev/null; then
    echo "🔒 Setting up git-secrets..."
    git secrets --install
    git secrets --register-aws
fi

# Pull Docker images
echo "🐳 Pulling Docker images..."
docker-compose pull

# Initialize databases
echo "🗄️  Initializing databases..."
bash scripts/init-databases.sh

# Run initial health check
echo "🏥 Running health check..."
make health || true

echo "✨ Development environment setup complete!"
echo ""
echo "📚 Next steps:"
echo "  1. Edit .env file with your configuration"
echo "  2. Run 'make dev' to start development"
echo "  3. Visit http://localhost:8080"
echo ""
echo "📖 Run 'make help' for available commands"