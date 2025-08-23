#!/bin/sh
# Custom entrypoint for n8n with execution tracking patch

echo "🚀 Starting n8n with custom modifications..."

# Apply execution tracking patch
echo "📝 Applying execution tracking patch..."
node /patches/enable-execution-tracking.js || echo "⚠️  Patch failed but continuing..."

# Start n8n normally
echo "✨ Starting n8n..."
exec n8n