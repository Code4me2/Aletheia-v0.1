#!/bin/sh
# Fix custom nodes that are missing dist/index.js files
# This script ensures all custom nodes can be loaded by n8n

echo "🔧 Fixing custom node index files..."

# Function to create index.js if missing
fix_node_index() {
    NODE_DIR="$1"
    NODE_NAME="$2"
    NODE_CLASS="$3"
    
    if [ -d "$NODE_DIR" ]; then
        if [ ! -f "$NODE_DIR/dist/index.js" ]; then
            echo "  ✨ Creating index.js for $NODE_NAME..."
            cat > "$NODE_DIR/dist/index.js" << EOF
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.nodes = void 0;
const ${NODE_CLASS}_node_1 = require("./nodes/${NODE_CLASS}/${NODE_CLASS}.node");
exports.nodes = [${NODE_CLASS}_node_1.${NODE_CLASS}];
EOF
        else
            echo "  ✓ $NODE_NAME index.js exists"
        fi
    fi
}

# Fix each potentially broken node
fix_node_index "/data/.n8n/custom/n8n-nodes-citation-gen" "CitationGen" "CitationGen"
fix_node_index "/data/.n8n/custom/n8n-nodes-hierarchicalSummarization" "HierarchicalSummarization" "HierarchicalSummarization"
fix_node_index "/data/.n8n/custom/n8n-nodes-yake" "YAKE" "yakeKeywordExtraction"
fix_node_index "/data/.n8n/custom/n8n-nodes-unstructured" "Unstructured" "unstructured"

# DeepSeek has a different structure - it doesn't need dist/index.js
echo "  ✓ DeepSeek uses different loading mechanism"

echo "✅ Custom nodes fixed!"

# Run auto-setup in background after n8n starts
(
    sleep 10  # Give n8n time to initialize
    if [ -f /usr/local/bin/auto-setup ]; then
        /usr/local/bin/auto-setup
    fi
) &

# Start n8n normally
exec n8n