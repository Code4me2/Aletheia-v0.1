#!/bin/bash
# Fix workflow node types to use packageName.ClassName format

echo "Fixing workflow node types to packageName.ClassName format..."

# hierarchicalSummarization -> n8n-nodes-hierarchicalSummarization.HierarchicalSummarization
sed -i 's/"type": "hierarchicalSummarization"/"type": "n8n-nodes-hierarchicalSummarization.HierarchicalSummarization"/g' workflow_json/*.json

# haystackSearch -> n8n-nodes-haystack.HaystackSearch  
sed -i 's/"type": "haystackSearch"/"type": "n8n-nodes-haystack.HaystackSearch"/g' workflow_json/*.json

# If deepseek is used (dsr1 -> n8n-nodes-deepseek.Dsr1)
sed -i 's/"type": "dsr1"/"type": "n8n-nodes-deepseek.Dsr1"/g' workflow_json/*.json

# If yake is used (keyword_extraction -> n8n-nodes-yake.yakeKeywordExtraction)
sed -i 's/"type": "keyword_extraction"/"type": "n8n-nodes-yake.yakeKeywordExtraction"/g' workflow_json/*.json

# If citationChecker is used
sed -i 's/"type": "citationChecker"/"type": "n8n-nodes-citationchecker.CitationChecker"/g' workflow_json/*.json

# If bitnet is used
sed -i 's/"type": "bitnet"/"type": "n8n-nodes-bitnet.BitNet"/g' workflow_json/*.json

echo "Done! Workflow files updated to use packageName.ClassName format."