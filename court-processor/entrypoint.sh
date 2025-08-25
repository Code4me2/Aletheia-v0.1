#!/bin/sh
# Court Processor Entrypoint Script
# Handles privilege separation for cron tasks and API server

# Function to run commands as appuser
run_as_appuser() {
    su -c "$1" appuser
}

# Start cron in background (requires root)
cron

# Verify setup as appuser
run_as_appuser "echo 'Court Processor Container Started'"
run_as_appuser "python3 --version"

# Check database connectivity as appuser
if [ -n "$DATABASE_URL" ]; then
    run_as_appuser "echo 'Database URL configured: Yes'"
else
    echo "WARNING: DATABASE_URL not configured"
fi

# Create log files with proper permissions
touch /data/logs/court-processor.log /data/logs/api.log /data/logs/simplified-api.log
chown appuser:appuser /data/logs/court-processor.log /data/logs/api.log /data/logs/simplified-api.log

# Start the API server (primary API for lawyer-chat integration)
echo "Starting Court Documents API on port ${SIMPLE_API_PORT:-8104}..."
su -c "cd /app && python3 api.py --host 0.0.0.0 --port ${SIMPLE_API_PORT:-8104} > /data/logs/api.log 2>&1 &" appuser

# Optionally start the Unified API server if it exists (keep for backward compatibility)
if [ -f "/app/api/unified_api.py" ]; then
    echo "Starting Unified Court Document Processor API (legacy)..."
    su -c "cd /app && python3 -m uvicorn api.unified_api:app --host 0.0.0.0 --port 8090 --log-level info > /data/logs/api.log 2>&1 &" appuser 2>/dev/null || echo "Note: Unified API not available or failed to start"
fi

# Monitor logs (as appuser)
echo "Monitoring court processor logs..."
exec su -c "tail -f /data/logs/court-processor.log /data/logs/api.log 2>/dev/null || tail -f /dev/null" appuser