#!/bin/bash
set -e

echo "Building n8n custom nodes..."

# Base directory for custom nodes
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CUSTOM_NODES_DIR="$SCRIPT_DIR/custom-nodes"

# List of nodes that need building (excluding deepseek which already has dist)
NODES=(
    "n8n-nodes-bitnet"
    "n8n-nodes-citationchecker"
    "n8n-nodes-citation-gen"
    "n8n-nodes-haystack"
    "n8n-nodes-hierarchicalSummarization"
    "n8n-nodes-yake"
)

# Function to build a node
build_node() {
    local node_name=$1
    local node_path="$CUSTOM_NODES_DIR/$node_name"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Building $node_name..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ ! -d "$node_path" ]; then
        echo "✗ Directory not found: $node_path"
        return 1
    fi
    
    cd "$node_path"
    
    # Check if package.json exists
    if [ ! -f "package.json" ]; then
        echo "✗ No package.json found in $node_path"
        return 1
    fi
    
    # Install dependencies
    echo "Installing dependencies..."
    npm install --no-audit --no-fund || {
        echo "✗ Failed to install dependencies for $node_name"
        return 1
    }
    
    # Build the node
    echo "Building TypeScript..."
    npm run build || {
        echo "✗ Failed to build $node_name"
        return 1
    }
    
    # Verify dist directory was created
    if [ -d "dist" ]; then
        echo "✓ Successfully built $node_name"
        echo "  dist/ contains: $(ls -1 dist | wc -l) files"
    else
        echo "✗ dist/ directory was not created for $node_name"
        return 1
    fi
    
    echo ""
}

# Build each node
for node in "${NODES[@]}"; do
    build_node "$node" || echo "Warning: Failed to build $node"
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Build summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check which nodes have dist directories
for node in "${NODES[@]}"; do
    if [ -d "$CUSTOM_NODES_DIR/$node/dist" ]; then
        echo "✓ $node - HAS dist/"
    else
        echo "✗ $node - NO dist/"
    fi
done

echo ""
echo "n8n should now be able to recognize the custom nodes."
echo "Restart n8n to load the newly built nodes:"
echo "  docker compose restart n8n"