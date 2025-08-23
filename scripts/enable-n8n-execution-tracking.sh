#!/bin/bash

# Enable execution tracking in n8n webhooks
# This script patches n8n to return execution IDs in webhook responses

echo "🔧 Enabling n8n execution tracking..."

# Check if container is running
if ! docker ps | grep -q aletheia_development-n8n-1; then
    echo "❌ n8n container is not running"
    exit 1
fi

# Create the patch
cat << 'EOF' > /tmp/n8n-webhook-patch.js
// Patch to make n8n webhooks return execution ID
const fs = require('fs');

const file = '/usr/local/lib/node_modules/n8n/dist/webhooks/webhook-helpers.js';
let content = fs.readFileSync(file, 'utf8');

// Check if already patched
if (content.includes('__EXECUTION_TRACKING_PATCH__')) {
    console.log('Already patched');
    process.exit(0);
}

// Find the line where executionId is set from WorkflowRunner.run
const pattern = /executionId = await[^;]+WorkflowRunner[^;]+\.run\([^)]+\);/;
const match = content.match(pattern);

if (!match) {
    console.error('Could not find execution line to patch');
    process.exit(1);
}

// Add code to inject executionId into response
const injection = match[0] + `
        // __EXECUTION_TRACKING_PATCH__
        // Inject execution ID into webhook response data
        if (executionId && responseCallback) {
            const originalCallback = responseCallback;
            responseCallback = (error, data) => {
                if (!error && data) {
                    // Add execution ID to response
                    if (typeof data === 'object') {
                        data.__executionId = executionId;
                    }
                }
                return originalCallback(error, data);
            };
        }`;

content = content.replace(match[0], injection);

// Write patched file
fs.writeFileSync(file, content);
console.log('✅ Patch applied successfully');
EOF

# Copy patch to container
docker cp /tmp/n8n-webhook-patch.js aletheia_development-n8n-1:/tmp/

# Apply the patch (need root to modify n8n files)
docker exec -u root aletheia_development-n8n-1 node /tmp/n8n-webhook-patch.js

# Restart n8n to apply changes
echo "🔄 Restarting n8n..."
docker restart aletheia_development-n8n-1

echo "⏳ Waiting for n8n to start..."
sleep 10

# Check if n8n is responding
if curl -s http://localhost:8080/n8n/healthz > /dev/null 2>&1; then
    echo "✅ n8n execution tracking enabled!"
    echo ""
    echo "Webhook responses will now include:"
    echo "  { ...response, __executionId: 'xxx-xxx-xxx' }"
    echo ""
    echo "You can track execution progress using the execution ID"
else
    echo "⚠️  n8n may still be starting. Check http://localhost:8080/n8n/"
fi