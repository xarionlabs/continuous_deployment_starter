#!/bin/sh
set -e

echo "Starting Test Shopify App..."
echo "Environment: ${NODE_ENV:-test}"
echo "Shopify API Key: ${SHOPIFY_API_KEY:-test_key}"
echo "Database URL: ${DATABASE_URL:-not set}"

# Start the application
echo "Starting Node.js server..."
exec node server.js