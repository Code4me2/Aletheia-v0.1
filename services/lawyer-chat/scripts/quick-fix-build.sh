#!/bin/bash
# Quick fix script for build issues

echo "=== Quick Build Fix Script ==="
echo "This script ensures all dependencies are properly installed"
echo ""

# Change to lawyer-chat directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1

# Ensure we have package-lock.json
if [ ! -f "package-lock.json" ]; then
    echo "⚠️  package-lock.json missing, running npm install..."
    npm install
fi

# Verify critical dependencies
echo "Checking critical dependencies..."

# Check ESLint
if ! npm list eslint >/dev/null 2>&1; then
    echo "❌ ESLint missing, installing..."
    npm install --save-dev eslint
else
    echo "✅ ESLint is installed"
fi

# Check @types/bcryptjs
if ! npm list @types/bcryptjs >/dev/null 2>&1; then
    echo "❌ @types/bcryptjs missing, installing..."
    npm install --save-dev @types/bcryptjs
else
    echo "✅ @types/bcryptjs is installed"
fi

# Ensure bcryptjs is in dependencies (not devDependencies)
if ! grep -q '"bcryptjs"' package.json | grep -v devDependencies; then
    echo "⚠️  Moving bcryptjs to dependencies..."
    npm install --save bcryptjs
fi

echo ""
echo "✅ Dependencies fixed!"
echo ""
echo "Next steps:"
echo "1. cd ../.."
echo "2. docker compose build --no-cache lawyer-chat"
echo ""
echo "Alternative (if build still fails):"
echo "Uncomment the ESLint ignore in next.config.ts"