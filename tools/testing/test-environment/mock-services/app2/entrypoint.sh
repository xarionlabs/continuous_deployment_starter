#!/bin/sh
set -e

echo "Starting Test App 2..."
echo "Environment: ${NODE_ENV:-test}"
echo "API URL: ${VITE_API_URL:-http://localhost:8000}"

# Start the application
echo "Starting Node.js server..."
exec node server.js