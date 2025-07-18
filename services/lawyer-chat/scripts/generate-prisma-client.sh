#!/bin/bash
# Script to generate Prisma client locally before Docker build
# This avoids the 403 errors when trying to download binaries during Docker build

echo "=== Prisma Client Generation Script ==="
echo "This script generates the Prisma client locally to avoid Docker build issues"
echo ""

# Change to the lawyer-chat directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "❌ ERROR: node_modules not found"
    echo "   Please run: npm install"
    exit 1
fi

# Check if Prisma CLI is available
if [ ! -f "node_modules/.bin/prisma" ]; then
    echo "❌ ERROR: Prisma CLI not found in node_modules"
    echo "   Please run: npm install"
    exit 1
fi

# Create the output directory
echo "Creating output directory..."
mkdir -p src/generated/prisma

# Generate Prisma client
echo "Generating Prisma client..."
NODE_ENV=production npx prisma generate --schema=./prisma/schema.prisma

# Check if generation was successful
if [ -d "src/generated/prisma" ] && [ -f "src/generated/prisma/index.js" ]; then
    echo "✅ Prisma client generated successfully!"
    echo "   Location: src/generated/prisma"
    
    # Show generated files
    echo ""
    echo "Generated files:"
    ls -la src/generated/prisma/ | head -10
    echo ""
    
    echo "✅ Ready for Docker build!"
    echo "   Run: docker compose build lawyer-chat"
else
    echo "❌ ERROR: Prisma client generation failed"
    echo "   Please check the error messages above"
    exit 1
fi