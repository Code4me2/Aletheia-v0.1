#!/bin/bash

# Lawyer-Chat Frontend Verification Script
# This script provides repeatable methods to verify that new code has been deployed

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}  Lawyer-Chat Frontend Verification${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

# Function to extract component signatures from source
extract_source_signatures() {
    echo -e "${CYAN}1. Source Code Signatures:${NC}"
    
    # Check for key components in source
    COMPONENTS=(
        "CitationPanelEnhanced"
        "CitationPanel"
        "DocumentCabinet"
        "extractCitationMarkers"
        "documentToCitation"
    )
    
    SOURCE_DIR="services/lawyer-chat/src"
    
    for comp in "${COMPONENTS[@]}"; do
        if grep -r "$comp" "$SOURCE_DIR" --include="*.tsx" --include="*.ts" >/dev/null 2>&1; then
            echo -e "  ${GREEN}✓${NC} $comp found in source"
            # Get file count
            FILE_COUNT=$(grep -r "$comp" "$SOURCE_DIR" --include="*.tsx" --include="*.ts" -l 2>/dev/null | wc -l | tr -d ' ')
            echo "    Used in $FILE_COUNT file(s)"
        else
            echo -e "  ${RED}✗${NC} $comp not found in source"
        fi
    done
    echo ""
}

# Function to check build artifacts
check_build_artifacts() {
    echo -e "${CYAN}2. Local Build Artifacts:${NC}"
    
    BUILD_DIR="services/lawyer-chat/.next"
    
    if [ -d "$BUILD_DIR" ]; then
        # Get BUILD_ID
        if [ -f "$BUILD_DIR/BUILD_ID" ]; then
            BUILD_ID=$(cat "$BUILD_DIR/BUILD_ID")
            echo -e "  Build ID: ${YELLOW}$BUILD_ID${NC}"
        fi
        
        # Check build timestamp
        BUILD_TIME=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$BUILD_DIR" 2>/dev/null || \
                     stat -c "%y" "$BUILD_DIR" 2>/dev/null | cut -d' ' -f1-2 || \
                     echo "Unknown")
        echo -e "  Build Time: $BUILD_TIME"
        
        # Check for components in build
        echo -e "  Component presence in build:"
        for comp in "CitationPanel" "DocumentCabinet" "extractCitation"; do
            if grep -r "$comp" "$BUILD_DIR" --include="*.js" >/dev/null 2>&1; then
                echo -e "    ${GREEN}✓${NC} $comp is in build"
            else
                echo -e "    ${YELLOW}○${NC} $comp not found in build (may be minified)"
            fi
        done
    else
        echo -e "  ${RED}✗${NC} No local build found at $BUILD_DIR"
        echo -e "  Run: cd services/lawyer-chat && npm run build"
    fi
    echo ""
}

# Function to check Docker container
check_container() {
    echo -e "${CYAN}3. Docker Container Status:${NC}"
    
    CONTAINER="lawyer-chat"
    
    if docker ps --format "{{.Names}}" | grep -q "^${CONTAINER}$"; then
        echo -e "  ${GREEN}✓${NC} Container is running"
        
        # Get container BUILD_ID
        CONTAINER_BUILD_ID=$(docker exec "$CONTAINER" cat /app/.next/BUILD_ID 2>/dev/null || echo "Not found")
        echo -e "  Container Build ID: ${YELLOW}$CONTAINER_BUILD_ID${NC}"
        
        # Check container start time
        START_TIME=$(docker inspect "$CONTAINER" --format '{{.State.StartedAt}}' 2>/dev/null | cut -d'T' -f1-2 | tr 'T' ' ')
        echo -e "  Container Started: $START_TIME"
        
        # Check if source files exist in container (they shouldn't in production build)
        if docker exec "$CONTAINER" test -d /app/src 2>/dev/null; then
            echo -e "  ${YELLOW}⚠${NC} Source files present (development mode?)"
        else
            echo -e "  ${GREEN}✓${NC} Production build (no source files)"
        fi
        
        # Check for specific components in container build
        echo -e "  Checking deployed components:"
        
        # Method 1: Check server-side rendered code
        for comp in "CitationPanel" "DocumentCabinet"; do
            if docker exec "$CONTAINER" grep -q "$comp" /app/.next/server/app/page.js 2>/dev/null; then
                echo -e "    ${GREEN}✓${NC} $comp in server bundle"
            else
                echo -e "    ${RED}✗${NC} $comp not in server bundle"
            fi
        done
        
        # Method 2: Check chunk files
        CHUNK_COUNT=$(docker exec "$CONTAINER" find /app/.next/static/chunks -name "*.js" 2>/dev/null | wc -l || echo 0)
        echo -e "  Total JS chunks: $CHUNK_COUNT"
        
    else
        echo -e "  ${RED}✗${NC} Container not running"
        echo -e "  Run: ./dev up lawyer-chat"
    fi
    echo ""
}

# Function to verify runtime behavior
verify_runtime() {
    echo -e "${CYAN}4. Runtime Verification:${NC}"
    
    # Check if service is accessible
    CHAT_URL="http://localhost:3000"
    
    if curl -s -o /dev/null -w "%{http_code}" "$CHAT_URL" | grep -q "200\|302"; then
        echo -e "  ${GREEN}✓${NC} Service responding on $CHAT_URL"
        
        # Extract and check for specific component markers
        echo -e "  Checking runtime components:"
        
        # Try to get a page with our components
        RESPONSE=$(docker exec lawyer-chat curl -s http://localhost:3000 2>/dev/null || echo "")
        
        if [ -n "$RESPONSE" ]; then
            # Check for Next.js chunks
            CHUNK_PATHS=$(echo "$RESPONSE" | grep -o '/_next/static/chunks/[^"]*\.js' | head -5)
            if [ -n "$CHUNK_PATHS" ]; then
                echo -e "    ${GREEN}✓${NC} Next.js chunks detected"
                
                # Count unique chunks
                UNIQUE_CHUNKS=$(echo "$CHUNK_PATHS" | sort -u | wc -l)
                echo -e "    Found $UNIQUE_CHUNKS unique chunk references"
            else
                echo -e "    ${YELLOW}⚠${NC} No Next.js chunks found in response"
            fi
            
            # Check for specific text that would indicate our components
            if echo "$RESPONSE" | grep -q "DocumentContext\|Citation"; then
                echo -e "    ${GREEN}✓${NC} Component references found in HTML"
            else
                echo -e "    ${YELLOW}○${NC} No direct component references (normal for production)"
            fi
        fi
    else
        echo -e "  ${RED}✗${NC} Service not responding on $CHAT_URL"
    fi
    echo ""
}

# Function to compare source to deployment
compare_deployment() {
    echo -e "${CYAN}5. Source vs Deployment Comparison:${NC}"
    
    # Get local build ID if exists
    LOCAL_BUILD_ID=""
    if [ -f "services/lawyer-chat/.next/BUILD_ID" ]; then
        LOCAL_BUILD_ID=$(cat "services/lawyer-chat/.next/BUILD_ID")
    fi
    
    # Get container build ID
    CONTAINER_BUILD_ID=$(docker exec lawyer-chat cat /app/.next/BUILD_ID 2>/dev/null || echo "")
    
    if [ -n "$LOCAL_BUILD_ID" ] && [ -n "$CONTAINER_BUILD_ID" ]; then
        if [ "$LOCAL_BUILD_ID" = "$CONTAINER_BUILD_ID" ]; then
            echo -e "  ${GREEN}✓${NC} Build IDs match: $LOCAL_BUILD_ID"
            echo -e "  ${YELLOW}⚠${NC} Container may not have latest source changes"
            echo -e "  Recommendation: Run './dev rebuild lawyer-chat --hard'"
        else
            echo -e "  ${YELLOW}⚠${NC} Build IDs differ:"
            echo -e "    Local:     $LOCAL_BUILD_ID"
            echo -e "    Container: $CONTAINER_BUILD_ID"
            echo -e "  ${CYAN}ℹ${NC} This is normal if container was built separately"
        fi
    else
        echo -e "  ${YELLOW}⚠${NC} Cannot compare builds (missing BUILD_ID)"
    fi
    
    # Check modification times
    echo ""
    echo -e "  Recent file changes:"
    find services/lawyer-chat/src -type f \( -name "*.tsx" -o -name "*.ts" \) -mtime -1 2>/dev/null | head -5 | while read file; do
        echo -e "    • $(basename $file) (modified recently)"
    done
    
    echo ""
}

# Function to generate a unique signature for current source
generate_source_signature() {
    echo -e "${CYAN}6. Source Code Signature:${NC}"
    
    # Create a signature based on specific component files
    SIGNATURE_FILES=(
        "services/lawyer-chat/src/app/page.tsx"
        "services/lawyer-chat/src/components/CitationPanelEnhanced.tsx"
        "services/lawyer-chat/src/components/DocumentCabinet.tsx"
        "services/lawyer-chat/src/utils/citationExtractor.ts"
    )
    
    SIGNATURE=""
    for file in "${SIGNATURE_FILES[@]}"; do
        if [ -f "$file" ]; then
            # Get last modified time and size
            if [[ "$OSTYPE" == "darwin"* ]]; then
                MOD_TIME=$(stat -f "%m" "$file")
                FILE_SIZE=$(stat -f "%z" "$file")
            else
                MOD_TIME=$(stat -c "%Y" "$file")
                FILE_SIZE=$(stat -c "%s" "$file")
            fi
            SIGNATURE="${SIGNATURE}${MOD_TIME}:${FILE_SIZE}:"
        fi
    done
    
    if [ -n "$SIGNATURE" ]; then
        # Create a hash of the signature
        HASH=$(echo "$SIGNATURE" | shasum -a 256 | cut -d' ' -f1 | cut -c1-12)
        echo -e "  Source signature: ${YELLOW}$HASH${NC}"
        echo -e "  ${CYAN}ℹ${NC} Save this to compare after deployment"
        
        # Save to temp file for comparison
        echo "$HASH" > /tmp/lawyer-chat-source-sig
        echo -e "  Saved to: /tmp/lawyer-chat-source-sig"
    else
        echo -e "  ${RED}✗${NC} Could not generate signature"
    fi
    echo ""
}

# Main execution
main() {
    extract_source_signatures
    check_build_artifacts
    check_container
    verify_runtime
    compare_deployment
    generate_source_signature
    
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  Quick Verification Commands:${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    echo "1. Check container build ID:"
    echo "   docker exec lawyer-chat cat /app/.next/BUILD_ID"
    echo ""
    echo "2. Check for specific component:"
    echo "   docker exec lawyer-chat grep -c 'CitationPanelEnhanced' /app/.next/server/app/page.js"
    echo ""
    echo "3. Force rebuild with verification:"
    echo "   ./dev rebuild lawyer-chat --hard --verify"
    echo ""
    echo "4. Compare local vs container build:"
    echo "   diff <(cat services/lawyer-chat/.next/BUILD_ID) <(docker exec lawyer-chat cat /app/.next/BUILD_ID)"
    echo ""
}

# Run main function
main