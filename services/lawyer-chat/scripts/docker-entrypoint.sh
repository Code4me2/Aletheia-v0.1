#!/bin/sh

echo "Waiting for database to be ready..."
# Use node to run prisma directly since npx may not be available in standalone build
until node node_modules/prisma/build/index.js db push --skip-generate 2>/dev/null || node node_modules/@prisma/cli/build/index.js db push --skip-generate 2>/dev/null; do
  echo "Database is unavailable - sleeping"
  sleep 5
done

echo "Database is ready!"

# Run migrations if they exist
echo "Checking for database migrations..."
if [ -d "prisma/migrations" ]; then
  echo "Running database migrations..."
  node node_modules/prisma/build/index.js migrate deploy 2>/dev/null || node node_modules/@prisma/cli/build/index.js migrate deploy 2>/dev/null || echo "Migration deployment skipped"
else
  echo "No migrations directory found, skipping migration deployment"
fi

# Start the application
echo "Starting Next.js application..."
exec node server.js