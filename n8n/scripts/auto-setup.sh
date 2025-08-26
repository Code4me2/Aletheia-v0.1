#!/bin/sh
DB_PATH="/data/.n8n/database.sqlite"
SETUP_EMAIL="${N8N_SETUP_EMAIL:-admin@aletheia.local}"

echo "n8n Auto Setup: Checking initialization status..."

if [ ! -f "$DB_PATH" ]; then
    echo "Database not found. Waiting..."
    sleep 5
    if [ ! -f "$DB_PATH" ]; then
        echo "Database still not ready"
        exit 0
    fi
fi

# Check if owner is set up
IS_SETUP=$(sqlite3 "$DB_PATH" "SELECT value FROM settings WHERE key = 'userManagement.isInstanceOwnerSetUp'" 2>/dev/null || echo "")

if [ "$IS_SETUP" = "true" ]; then
    echo "n8n already has an owner account"
else
    echo "Creating owner account..."
    # Create basic owner (password: admin123)
    sqlite3 "$DB_PATH" "INSERT INTO user (id, email, firstName, lastName, role, disabled, settings, createdAt, updatedAt) VALUES ('auto-setup-user', '$SETUP_EMAIL', 'Admin', 'User', 'global:owner', 0, '{}', datetime('now'), datetime('now'))"
    sqlite3 "$DB_PATH" "INSERT OR REPLACE INTO settings (key, value, loadOnStartup) VALUES ('userManagement.isInstanceOwnerSetUp', 'true', 1)"
    echo "Owner created: $SETUP_EMAIL"
fi

# Activate workflows
echo "Activating workflows..."
sqlite3 "$DB_PATH" "UPDATE workflow_entity SET active = 1 WHERE active = 0"

WORKFLOW_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM workflow_entity" 2>/dev/null || echo "0")
echo "Workflows active: $WORKFLOW_COUNT"
echo "Setup complete!"
