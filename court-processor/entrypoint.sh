#!/bin/sh
# Court Processor Entrypoint Script
# Handles privilege separation for cron tasks

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

# Create log file with proper permissions
touch /data/logs/court-processor.log
chown appuser:appuser /data/logs/court-processor.log

# Monitor logs (as appuser)
echo "Monitoring court processor logs..."
exec su -c "tail -f /data/logs/court-processor.log 2>/dev/null || tail -f /dev/null" appuser