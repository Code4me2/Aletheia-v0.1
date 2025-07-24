#!/bin/bash
set -e

echo "[n8n-init] Starting n8n workflow automation with deduplication..."

# Function to check if n8n is ready
wait_for_n8n() {
    local max_attempts=30
    local attempt=0
    
    echo "[n8n-init] Waiting for n8n to be ready..."
    
    while [ $attempt -lt $max_attempts ]; do
        # Use wget which is available in the n8n container
        if wget -q --spider http://localhost:5678/healthz 2>/dev/null; then
            echo "[n8n-init] n8n is ready!"
            return 0
        fi
        
        echo "[n8n-init] Waiting for n8n... (attempt $((attempt+1))/$max_attempts)"
        sleep 2
        attempt=$((attempt+1))
    done
    
    echo "[n8n-init] ERROR: n8n did not start in time"
    return 1
}

# Function to get existing workflow names
get_existing_workflows() {
    # Get list of workflows and extract names
    # Format: ID|Name, we want just the names
    n8n list:workflow 2>/dev/null | tail -n +2 | cut -d'|' -f2 || true
}

# Function to extract workflow name from JSON file
get_workflow_name_from_json() {
    local json_file="$1"
    # Use jq if available, otherwise use grep/sed
    if command -v jq >/dev/null 2>&1; then
        jq -r '.name // empty' "$json_file" 2>/dev/null || echo ""
    else
        # Fallback to grep/sed for name extraction
        grep -o '"name"[[:space:]]*:[[:space:]]*"[^"]*"' "$json_file" 2>/dev/null | \
        sed 's/.*"name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' || echo ""
    fi
}

# Function to import workflows with deduplication
import_workflows() {
    echo "[n8n-init] Importing workflows with deduplication..."
    
    # Check if workflows directory exists
    if [ ! -d "/workflows" ]; then
        echo "[n8n-init] WARNING: /workflows directory not found"
        return 0
    fi
    
    # Get existing workflow names
    echo "[n8n-init] Checking existing workflows..."
    local existing_workflows=$(get_existing_workflows)
    
    # Count workflow files
    local workflow_count=$(find /workflows -name "*.json" -type f 2>/dev/null | wc -l)
    
    if [ $workflow_count -eq 0 ]; then
        echo "[n8n-init] No workflow files found in /workflows"
        return 0
    fi
    
    echo "[n8n-init] Found $workflow_count workflow file(s)"
    
    local imported=0
    local skipped=0
    
    # Import each workflow
    for workflow_file in /workflows/*.json; do
        if [ -f "$workflow_file" ]; then
            local basename=$(basename "$workflow_file")
            
            # Extract workflow name from JSON
            local workflow_name=$(get_workflow_name_from_json "$workflow_file")
            
            if [ -z "$workflow_name" ]; then
                echo "[n8n-init] WARNING: Could not extract name from $basename, skipping"
                skipped=$((skipped+1))
                continue
            fi
            
            # Check if workflow already exists
            if echo "$existing_workflows" | grep -Fxq "$workflow_name"; then
                echo "[n8n-init] Skipping '$workflow_name' - already exists"
                skipped=$((skipped+1))
            else
                echo "[n8n-init] Importing: $basename (name: '$workflow_name')"
                
                # Use n8n import command
                if n8n import:workflow --input="$workflow_file"; then
                    echo "[n8n-init] Successfully imported: $basename"
                    imported=$((imported+1))
                    # Add to existing workflows list for subsequent checks
                    existing_workflows="$existing_workflows
$workflow_name"
                else
                    echo "[n8n-init] WARNING: Failed to import: $basename"
                fi
            fi
        fi
    done
    
    echo "[n8n-init] Import complete: $imported imported, $skipped skipped"
}

# Function to activate all workflows
activate_workflows() {
    echo "[n8n-init] Activating all workflows..."
    
    if n8n update:workflow --all --active=true; then
        echo "[n8n-init] All workflows activated successfully"
    else
        echo "[n8n-init] WARNING: Failed to activate some workflows"
    fi
}

# Main execution
main() {
    # Start n8n in background
    echo "[n8n-init] Starting n8n in background..."
    n8n start &
    N8N_PID=$!
    
    # Wait for n8n to be ready
    if ! wait_for_n8n; then
        kill $N8N_PID 2>/dev/null || true
        exit 1
    fi
    
    # Import workflows with deduplication
    import_workflows
    
    # Activate workflows
    activate_workflows
    
    # Kill background n8n
    echo "[n8n-init] Stopping background n8n process..."
    kill $N8N_PID 2>/dev/null || true
    wait $N8N_PID 2>/dev/null || true
    
    # Start n8n in foreground
    echo "[n8n-init] Starting n8n in foreground..."
    exec n8n start
}

# Run main function
main