#!/bin/sh
# n8n Execution Helper Script
# Provides advanced execution querying and workflow triggering capabilities

set -e

DB_PATH="/data/database.sqlite"
N8N_PORT="${N8N_PORT:-5678}"

# Function to query executions from SQLite
query_executions() {
    if [ ! -f "$DB_PATH" ]; then
        echo "Error: Database not found at $DB_PATH"
        exit 1
    fi
    
    case "$1" in
        last)
            sqlite3 -header -column "$DB_PATH" "
                SELECT 
                    id,
                    workflowId,
                    finished,
                    mode,
                    status,
                    datetime(startedAt/1000, 'unixepoch') as started,
                    datetime(stoppedAt/1000, 'unixepoch') as stopped,
                    CASE 
                        WHEN stoppedAt IS NOT NULL 
                        THEN (stoppedAt - startedAt) / 1000.0 || ' seconds'
                        ELSE 'Running'
                    END as duration
                FROM execution_entity 
                ORDER BY startedAt DESC 
                LIMIT ${2:-5};"
            ;;
        
        running)
            sqlite3 -header -column "$DB_PATH" "
                SELECT 
                    id,
                    workflowId,
                    mode,
                    datetime(startedAt/1000, 'unixepoch') as started,
                    'Running for ' || ((strftime('%s', 'now') * 1000 - startedAt) / 1000) || ' seconds' as duration
                FROM execution_entity 
                WHERE finished = 0
                ORDER BY startedAt DESC;"
            ;;
        
        failed)
            sqlite3 -header -column "$DB_PATH" "
                SELECT 
                    id,
                    workflowId,
                    status,
                    datetime(startedAt/1000, 'unixepoch') as started,
                    datetime(stoppedAt/1000, 'unixepoch') as stopped
                FROM execution_entity 
                WHERE status = 'failed' OR status = 'crashed'
                ORDER BY startedAt DESC 
                LIMIT ${2:-10};"
            ;;
        
        workflow)
            if [ -z "$2" ]; then
                echo "Error: Workflow ID required"
                exit 1
            fi
            sqlite3 -header -column "$DB_PATH" "
                SELECT 
                    id,
                    finished,
                    mode,
                    status,
                    datetime(startedAt/1000, 'unixepoch') as started,
                    datetime(stoppedAt/1000, 'unixepoch') as stopped
                FROM execution_entity 
                WHERE workflowId = '$2'
                ORDER BY startedAt DESC 
                LIMIT ${3:-10};"
            ;;
        
        stats)
            echo "=== Execution Statistics ==="
            sqlite3 "$DB_PATH" "
                SELECT 
                    'Total Executions: ' || COUNT(*) as metric
                FROM execution_entity
                UNION ALL
                SELECT 
                    'Successful: ' || COUNT(*)
                FROM execution_entity WHERE status = 'success'
                UNION ALL
                SELECT 
                    'Failed: ' || COUNT(*)
                FROM execution_entity WHERE status = 'failed' OR status = 'crashed'
                UNION ALL
                SELECT 
                    'Currently Running: ' || COUNT(*)
                FROM execution_entity WHERE finished = 0
                UNION ALL
                SELECT 
                    'Unique Workflows: ' || COUNT(DISTINCT workflowId)
                FROM execution_entity;"
            ;;
            
        details)
            if [ -z "$2" ]; then
                echo "Error: Execution ID required"
                exit 1
            fi
            
            # Get execution details
            sqlite3 -header -column "$DB_PATH" "
                SELECT 
                    id,
                    workflowId,
                    finished,
                    mode,
                    status,
                    datetime(startedAt/1000, 'unixepoch') as started,
                    datetime(stoppedAt/1000, 'unixepoch') as stopped,
                    retryOf,
                    retrySuccessId
                FROM execution_entity 
                WHERE id = '$2';"
            
            echo ""
            echo "=== Execution Data ==="
            # Get execution data (limited to first 500 chars for display)
            sqlite3 "$DB_PATH" "
                SELECT 
                    SUBSTR(data, 1, 500) as data_preview
                FROM execution_entity 
                WHERE id = '$2';"
            ;;
        
        *)
            echo "Usage: query_executions {last|running|failed|workflow|stats|details} [options]"
            ;;
    esac
}

# Function to trigger workflow via internal API
trigger_workflow() {
    WORKFLOW_ID="$1"
    DATA="${2:-{}}"
    
    if [ -z "$WORKFLOW_ID" ]; then
        echo "Error: Workflow ID required"
        exit 1
    fi
    
    # Use n8n's internal API to trigger workflow
    # This works even when n8n is running as a service
    response=$(curl -s -X POST "http://localhost:${N8N_PORT}/webhook/${WORKFLOW_ID}" \
        -H "Content-Type: application/json" \
        -d "$DATA" 2>&1)
    
    if [ $? -eq 0 ]; then
        echo "Workflow triggered successfully"
        echo "Response: $response"
        
        # Try to get the execution ID from the response
        exec_id=$(echo "$response" | jq -r '.executionId' 2>/dev/null || echo "")
        if [ ! -z "$exec_id" ] && [ "$exec_id" != "null" ]; then
            echo "Execution ID: $exec_id"
            echo ""
            echo "To check status: ./dev n8n query details $exec_id"
        fi
    else
        echo "Failed to trigger workflow"
        echo "Error: $response"
    fi
}

# Function to get workflow details
get_workflow() {
    WORKFLOW_ID="$1"
    
    if [ -z "$WORKFLOW_ID" ]; then
        # List all workflows
        sqlite3 -header -column "$DB_PATH" "
            SELECT 
                id,
                name,
                active,
                datetime(createdAt, 'unixepoch') as created,
                datetime(updatedAt, 'unixepoch') as updated
            FROM workflow_entity 
            ORDER BY updatedAt DESC;"
    else
        # Get specific workflow
        sqlite3 -header -column "$DB_PATH" "
            SELECT 
                id,
                name,
                active,
                datetime(createdAt, 'unixepoch') as created,
                datetime(updatedAt, 'unixepoch') as updated
            FROM workflow_entity 
            WHERE id = '$WORKFLOW_ID';"
        
        echo ""
        echo "=== Recent Executions for this Workflow ==="
        query_executions workflow "$WORKFLOW_ID" 5
    fi
}

# Main command router
case "$1" in
    query)
        shift
        query_executions "$@"
        ;;
    
    trigger)
        shift
        trigger_workflow "$@"
        ;;
    
    workflow)
        shift
        get_workflow "$@"
        ;;
    
    monitor)
        # Real-time monitoring using watch
        shift
        watch -n 2 "sqlite3 -header -column '$DB_PATH' '
            SELECT 
                id,
                workflowId,
                CASE 
                    WHEN finished = 0 THEN \"RUNNING\"
                    ELSE status
                END as status,
                datetime(startedAt/1000, \"unixepoch\") as started
            FROM execution_entity 
            ORDER BY startedAt DESC 
            LIMIT 10;'"
        ;;
    
    *)
        echo "n8n Execution Helper"
        echo ""
        echo "Usage:"
        echo "  query {last|running|failed|workflow|stats|details} [options]"
        echo "  trigger <workflow-id> [json-data]"
        echo "  workflow [workflow-id]"
        echo "  monitor                    # Real-time execution monitoring"
        echo ""
        echo "Examples:"
        echo "  query last 10              # Last 10 executions"
        echo "  query running              # Currently running executions"
        echo "  query workflow abc123      # Executions for specific workflow"
        echo "  query details exec456      # Details of specific execution"
        echo "  trigger abc123 '{\"test\":true}'"
        echo "  workflow                   # List all workflows"
        echo "  monitor                    # Watch executions in real-time"
        ;;
esac