#\!/bin/sh
DB_PATH="/data/database.sqlite"

case "$1" in
    stats)
        echo "=== Execution Statistics ==="
        sqlite3 "$DB_PATH" "SELECT 'Total Executions: ' || COUNT(*) FROM execution_entity" 2>/dev/null || echo "No executions yet"
        ;;
    last)
        sqlite3 -header -column "$DB_PATH" "SELECT id, workflowId, status FROM execution_entity ORDER BY id DESC LIMIT 5" 2>/dev/null || echo "No executions found"
        ;;
    *)
        echo "Usage: n8n-exec {stats|last}"
        ;;
esac
