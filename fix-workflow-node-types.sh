#!/bin/bash

echo "Fixing workflow node types..."

# Create backup directory
mkdir -p workflow_json/backup

# Fix all workflow files
for file in workflow_json/*.json; do
    if [ -f "$file" ]; then
        # Create backup
        cp "$file" "workflow_json/backup/$(basename "$file")"
        
        # Fix node types
        sed -i 's/"type": "n8n-nodes-haystack\.haystackSearch"/"type": "haystackSearch"/g' "$file"
        sed -i 's/"type": "n8n-nodes-hierarchicalSummarization\.hierarchicalSummarization"/"type": "hierarchicalSummarization"/g' "$file"
        sed -i 's/"type": "n8n-nodes-citationchecker\.citationChecker"/"type": "citationChecker"/g' "$file"
        sed -i 's/"type": "n8n-nodes-deepseek\.dsr1"/"type": "dsr1"/g' "$file"
        sed -i 's/"type": "n8n-nodes-yake\.yakeKeywordExtraction"/"type": "yakeKeywordExtraction"/g' "$file"
        sed -i 's/"type": "n8n-nodes-bitnet\.bitNet"/"type": "bitNet"/g' "$file"
        sed -i 's/"type": "n8n-nodes-bitnet\.summaryProcessor"/"type": "summaryProcessor"/g' "$file"
        
        echo "Fixed: $(basename "$file")"
    fi
done

echo "All workflow files have been fixed!"