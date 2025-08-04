#!/bin/bash
# Test script to verify Docker build will work

echo "=== Docker Build Test Script ==="
echo "This script checks if all requirements are met for a successful build"
echo ""

# Check if .env file exists
if [ ! -f "../../.env" ]; then
    echo "❌ ERROR: .env file not found in project root"
    echo "   Run: cp ../../.env.example ../../.env"
    echo "   Then edit the .env file with your values"
    exit 1
else
    echo "✅ .env file exists"
fi

# Check required environment variables
REQUIRED_VARS=(
    "DB_USER"
    "DB_PASSWORD"
    "DB_NAME"
    "NEXTAUTH_SECRET"
)

echo ""
echo "Checking required environment variables..."
for var in "${REQUIRED_VARS[@]}"; do
    if grep -q "^${var}=" ../../.env; then
        echo "✅ $var is defined"
    else
        echo "❌ ERROR: $var is not defined in .env"
        exit 1
    fi
done

# Check if package-lock.json exists
if [ ! -f "package-lock.json" ]; then
    echo ""
    echo "❌ WARNING: package-lock.json not found"
    echo "   This may cause inconsistent builds"
    echo "   Run: npm install"
fi

# Check Prisma schema
if [ -f "prisma/schema.prisma" ]; then
    echo ""
    echo "✅ Prisma schema found"
    
    # Check if binary targets are set correctly
    if grep -q 'binaryTargets.*=.*\["native"\]' prisma/schema.prisma; then
        echo "✅ Prisma binary targets set to 'native'"
    else
        echo "❌ WARNING: Prisma binary targets may need adjustment"
    fi
else
    echo "❌ ERROR: Prisma schema not found"
    exit 1
fi

echo ""
echo "=== Pre-flight check complete ==="
echo "If all checks passed, you can build with:"
echo "  docker compose build lawyer-chat"
echo ""