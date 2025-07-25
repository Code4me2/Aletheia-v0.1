#!/bin/bash

# Fix custom node type references in workflow files

echo "Fixing custom node type references in workflow files..."

# Backup workflows first
cp -r workflow_json workflow_json.backup.$(date +%Y%m%d_%H%M%S)

# Fix hierarchicalSummarization node references
echo "Fixing hierarchicalSummarization references..."
sed -i 's/"type": "hierarchicalSummarization"/"type": "n8n-nodes-hierarchicalSummarization.hierarchicalSummarization"/g' workflow_json/*.json

# Fix haystackSearch node references
echo "Fixing haystackSearch references..."
sed -i 's/"type": "haystackSearch"/"type": "n8n-nodes-haystack.haystackSearch"/g' workflow_json/*.json

# Fix any other custom node references
echo "Fixing deepseek references..."
sed -i 's/"type": "deepseek"/"type": "n8n-nodes-deepseek.deepseek"/g' workflow_json/*.json

echo "Fixing yake references..."
sed -i 's/"type": "yake"/"type": "n8n-nodes-yake.yake"/g' workflow_json/*.json

echo "Fixing citationchecker references..."
sed -i 's/"type": "citationChecker"/"type": "n8n-nodes-citationchecker.citationChecker"/g' workflow_json/*.json

echo "Fixing bitnet references..."
sed -i 's/"type": "bitnet"/"type": "n8n-nodes-bitnet.bitnet"/g' workflow_json/*.json

echo "Done! Workflow files have been updated with full package names."
echo "Backup created in workflow_json.backup.*"
echo ""
echo "Next steps:"
echo "1. Restart n8n container to reload workflows: docker-compose restart n8n"
echo "2. Check if workflows activate properly"