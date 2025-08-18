#!/bin/bash

# Script to force reimport of n8n workflows
# Use this when workflow node names have been updated

echo "=================================================="
echo "Force Reimport n8n Workflows"
echo "=================================================="
echo ""
echo "This will:"
echo "1. Clear the existing n8n database"
echo "2. Reimport all workflows from /workflow_json"
echo "3. Use the corrected node names"
echo ""
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting force reimport..."
    
    # Stop n8n
    echo "Stopping n8n..."
    docker-compose stop n8n
    
    # Clear the database volume
    echo "Clearing n8n database..."
    docker volume rm aletheia_development_n8n_data 2>/dev/null || true
    
    # Start n8n with force reimport flag
    echo "Starting n8n with force reimport..."
    FORCE_REIMPORT=true docker-compose up -d n8n
    
    echo ""
    echo "Force reimport initiated. Check logs with:"
    echo "  docker logs -f aletheia_development-n8n-1"
    echo ""
    echo "Workflows should now use the correct node names:"
    echo "  - haystackSearch (not n8n-nodes-haystack.HaystackSearch)"
    echo "  - hierarchicalSummarization (not n8n-nodes-hierarchicalSummarization.HierarchicalSummarization)"
    echo "  - dsr1 (for DeepSeek)"
else
    echo "Cancelled."
fi