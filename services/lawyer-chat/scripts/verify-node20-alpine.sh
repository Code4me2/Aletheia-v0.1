#!/bin/bash

echo "=== Node.js 20 Alpine Verification ==="
echo ""

# Check all FROM statements
echo "1. Verifying all stages use node:20-alpine..."
DEPS=$(grep "FROM.*AS deps" ../Dockerfile)
BUILDER=$(grep "FROM.*AS builder" ../Dockerfile)
RUNNER=$(grep "FROM.*AS runner" ../Dockerfile)

echo "   deps:    $DEPS"
echo "   builder: $BUILDER"
echo "   runner:  $RUNNER"

# Count alpine occurrences
ALPINE_COUNT=$(grep -c "FROM node:20-alpine" ../Dockerfile)
echo ""
echo "2. Alpine stages found: $ALPINE_COUNT (should be 3)"

# Check for apt-get
APT_COUNT=$(grep -c "apt-get" ../Dockerfile)
echo ""
echo "3. Debian apt-get commands found: $APT_COUNT (should be 0)"

# Check for apk
APK_COUNT=$(grep -c "apk add" ../Dockerfile)
echo ""
echo "4. Alpine apk commands found: $APK_COUNT (should be 3)"

# Final verification
if [[ $ALPINE_COUNT -eq 3 && $APT_COUNT -eq 0 && $APK_COUNT -eq 3 ]]; then
    echo ""
    echo "✅ SUCCESS: Node.js 20 Alpine upgrade implemented correctly!"
    echo "   - All 3 stages use node:20-alpine ✓"
    echo "   - No apt-get commands remain ✓"
    echo "   - All package installations use apk ✓"
    echo ""
    echo "This matches the security guide requirements exactly."
else
    echo ""
    echo "❌ ERROR: Implementation doesn't match security guide"
fi