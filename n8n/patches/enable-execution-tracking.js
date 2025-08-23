// Automatic patch to enable execution tracking in n8n webhooks
// Applied at container startup to make webhooks return execution IDs

const fs = require('fs');
const path = require('path');

console.log('[PATCH] Enabling execution tracking for webhooks...');

const file = '/usr/local/lib/node_modules/n8n/dist/webhooks/webhook-helpers.js';

// Check if file exists
if (!fs.existsSync(file)) {
    console.error('[PATCH] webhook-helpers.js not found - n8n structure may have changed');
    process.exit(1);
}

let content = fs.readFileSync(file, 'utf8');

// Check if already patched
if (content.includes('__EXECUTION_TRACKING_PATCH__')) {
    console.log('[PATCH] ✅ Already patched - skipping');
    process.exit(0);
}

// Create backup
const backupFile = file + '.backup';
if (!fs.existsSync(backupFile)) {
    fs.writeFileSync(backupFile, content);
    console.log('[PATCH] Backup created:', backupFile);
}

// Find the line where executionId is set from WorkflowRunner.run
const pattern = /executionId = await[^;]+WorkflowRunner[^;]+\.run\([^)]+\);/;
const match = content.match(pattern);

if (!match) {
    console.error('[PATCH] Could not find WorkflowRunner.run() call - code structure changed?');
    process.exit(1);
}

// Inject code to add executionId to webhook responses
const injection = match[0] + `
        // __EXECUTION_TRACKING_PATCH__ - Expose execution ID for progress tracking
        // This modification allows external services to track workflow execution progress
        if (executionId && responseCallback) {
            const originalCallback = responseCallback;
            responseCallback = (error, data) => {
                if (!error && data && typeof data === 'object') {
                    // Add execution ID to response for tracking
                    data.__executionId = executionId;
                    console.log('[WEBHOOK] Execution ID injected:', executionId);
                }
                return originalCallback(error, data);
            };
        }`;

content = content.replace(match[0], injection);

// Write patched file
try {
    fs.writeFileSync(file, content);
    console.log('[PATCH] ✅ Successfully patched webhook-helpers.js');
    console.log('[PATCH] Webhooks will now return __executionId in responses');
} catch (error) {
    console.error('[PATCH] Failed to write patched file:', error.message);
    process.exit(1);
}