#!/bin/bash
# Comprehensive build validation script for lawyer-chat Docker build

echo "=== Lawyer-Chat Docker Build Validation ==="
echo "This script validates all requirements for a successful Docker build"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to lawyer-chat directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1

# Track if any issues are found
ISSUES_FOUND=0

# Function to check a condition
check() {
    local condition=$1
    local success_msg=$2
    local error_msg=$3
    
    if eval "$condition"; then
        echo -e "${GREEN}✅ $success_msg${NC}"
    else
        echo -e "${RED}❌ $error_msg${NC}"
        ISSUES_FOUND=1
    fi
}

# 1. Check environment file
echo "1. Checking environment configuration..."
check "[ -f '../../.env' ]" \
    ".env file exists" \
    ".env file missing - run: cp ../../.env.example ../../.env"

# 2. Check required environment variables
echo ""
echo "2. Checking required environment variables..."
if [ -f "../../.env" ]; then
    for var in DB_USER DB_PASSWORD DB_NAME NEXTAUTH_SECRET; do
        if grep -q "^${var}=" ../../.env; then
            echo -e "${GREEN}✅ $var is defined${NC}"
        else
            echo -e "${RED}❌ $var is not defined in .env${NC}"
            ISSUES_FOUND=1
        fi
    done
fi

# 3. Check package files
echo ""
echo "3. Checking package files..."
check "[ -f 'package.json' ]" \
    "package.json exists" \
    "package.json missing"

check "[ -f 'package-lock.json' ]" \
    "package-lock.json exists" \
    "package-lock.json missing - run: npm install"

# 4. Check Prisma configuration
echo ""
echo "4. Checking Prisma configuration..."
check "[ -f 'prisma/schema.prisma' ]" \
    "Prisma schema exists" \
    "Prisma schema missing"

# Check Prisma generator output path
if [ -f "prisma/schema.prisma" ]; then
    if grep -q 'output.*=.*"../src/generated/prisma"' prisma/schema.prisma; then
        echo -e "${GREEN}✅ Prisma output path configured correctly${NC}"
    else
        echo -e "${YELLOW}⚠️  Prisma output path may need adjustment${NC}"
    fi
fi

# 5. Check Docker files
echo ""
echo "5. Checking Docker files..."
check "[ -f 'Dockerfile' ]" \
    "Dockerfile exists" \
    "Dockerfile missing"

check "[ -f 'scripts/docker-entrypoint.sh' ]" \
    "docker-entrypoint.sh exists" \
    "docker-entrypoint.sh missing"

check "[ -x 'scripts/docker-entrypoint.sh' ]" \
    "docker-entrypoint.sh is executable" \
    "docker-entrypoint.sh is not executable - run: chmod +x scripts/docker-entrypoint.sh"

# 6. Check if node_modules exists (for local development)
echo ""
echo "6. Checking local development setup..."
if [ -d "node_modules" ]; then
    echo -e "${GREEN}✅ node_modules exists${NC}"
    
    # Check if Prisma is installed
    check "[ -f 'node_modules/.bin/prisma' ]" \
        "Prisma CLI is installed" \
        "Prisma CLI missing - run: npm install"
    
    # Check if ESLint is installed
    check "[ -f 'node_modules/.bin/eslint' ]" \
        "ESLint is installed" \
        "ESLint missing - run: npm install"
    
    # Check if bcryptjs types are installed
    check "[ -d 'node_modules/@types/bcryptjs' ]" \
        "@types/bcryptjs is installed" \
        "@types/bcryptjs missing - run: npm install"
else
    echo -e "${YELLOW}⚠️  node_modules not found - run: npm install (optional for Docker build)${NC}"
fi

# 7. Check Next.js configuration
echo ""
echo "7. Checking Next.js configuration..."
check "[ -f 'next.config.ts' ]" \
    "next.config.ts exists" \
    "next.config.ts missing"

# Check if standalone output is configured
if [ -f "next.config.ts" ]; then
    if grep -q "output.*:.*'standalone'" next.config.ts; then
        echo -e "${GREEN}✅ Next.js standalone output configured${NC}"
    else
        echo -e "${RED}❌ Next.js standalone output not configured${NC}"
        ISSUES_FOUND=1
    fi
fi

# 8. Test Docker daemon
echo ""
echo "8. Checking Docker setup..."
if docker info >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker daemon is running${NC}"
else
    echo -e "${RED}❌ Docker daemon is not running${NC}"
    ISSUES_FOUND=1
fi

# 9. Check base image availability
echo ""
echo "9. Checking Docker base image..."
if docker pull node:18-slim --quiet >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Base image (node:18-slim) is available${NC}"
else
    echo -e "${YELLOW}⚠️  Could not pull base image (may work offline)${NC}"
fi

# Summary
echo ""
echo "========================================="
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Ready to build.${NC}"
    echo ""
    echo "To build the Docker image, run:"
    echo "  cd ../.. && docker compose build lawyer-chat"
    echo ""
    echo "Or if you want to generate Prisma client locally first:"
    echo "  ./generate-prisma-client.sh"
    echo "  cd ../.. && docker compose build lawyer-chat"
else
    echo -e "${RED}❌ Issues found! Please fix the errors above before building.${NC}"
    exit 1
fi