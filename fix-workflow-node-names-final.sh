#!/bin/bash
# Fix custom node names in workflow files to match actual node names

echo "Fixing custom node names in workflow files..."

# Check if deepseek is used anywhere
echo "Checking for deepseek usage..."
grep -l "deepseek" workflow_json/*.json || echo "No deepseek found"

# Check if yake is used
echo "Checking for yake usage..."
grep -l "yakeKeywordExtraction" workflow_json/*.json || echo "No yake found"

# For now, let's verify what's in the workflow files
echo ""
echo "Current node types in workflows:"
grep -h '"type":' workflow_json/*.json | grep -v "n8n-nodes-base" | sort | uniq

echo "Done checking!"