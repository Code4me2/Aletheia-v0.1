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
touch /data/logs/court-processor.log /data/logs/api.log
chown appuser:appuser /data/logs/court-processor.log /data/logs/api.log

# Start the Unified API server in background as appuser
echo "Starting Unified Court Document Processor API..."
su -c "cd /app && python3 -m uvicorn api.unified_api:app --host 0.0.0.0 --port 8090 --log-level info > /data/logs/api.log 2>&1 &" appuser

# Monitor logs (as appuser)
echo "Monitoring court processor logs..."
exec su -c "tail -f /data/logs/court-processor.log /data/logs/api.log 2>/dev/null || tail -f /dev/null" appuser