#!/bin/bash
# Fix custom node type references in workflow files - remove package prefix

echo "Fixing custom node type references in workflow files..."

# Backup workflows first
cp -r workflow_json workflow_json.backup.$(date +%Y%m%d_%H%M%S)

# Fix node type references - remove the package prefix
echo "Removing package prefixes from node types..."

# hierarchicalSummarization
sed -i 's/"type": "n8n-nodes-hierarchicalSummarization\.hierarchicalSummarization"/"type": "hierarchicalSummarization"/g' workflow_json/*.json

# haystackSearch  
sed -i 's/"type": "n8n-nodes-haystack\.haystackSearch"/"type": "haystackSearch"/g' workflow_json/*.json

# deepseek (note: class name is Dsr1, node name is deepseek)
sed -i 's/"type": "n8n-nodes-deepseek\.deepseek"/"type": "deepseek"/g' workflow_json/*.json
sed -i 's/"type": "n8n-nodes-deepseek\.Dsr1"/"type": "deepseek"/g' workflow_json/*.json

# yake
sed -i 's/"type": "n8n-nodes-yake\.yake"/"type": "yakeKeywordExtraction"/g' workflow_json/*.json
sed -i 's/"type": "n8n-nodes-yake\.yakeKeywordExtraction"/"type": "yakeKeywordExtraction"/g' workflow_json/*.json

# citationChecker
sed -i 's/"type": "n8n-nodes-citationchecker\.citationChecker"/"type": "citationChecker"/g' workflow_json/*.json

# bitnet
sed -i 's/"type": "n8n-nodes-bitnet\.bitnet"/"type": "bitnet"/g' workflow_json/*.json
sed -i 's/"type": "n8n-nodes-bitnet\.BitNet"/"type": "bitnet"/g' workflow_json/*.json

echo "Done! Workflow files have been updated to use simple node names."
echo "Backup created in workflow_json.backup.*"