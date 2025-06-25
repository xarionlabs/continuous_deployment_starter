#!/bin/bash
set -e

cd /app/src

# Check if APP_PXY6_VIRTUAL_HOST environment variable is set
if [ -z "$APP_PXY6_VIRTUAL_HOST" ]; then
    echo "ERROR: APP_PXY6_VIRTUAL_HOST environment variable is not set"
    exit 1
fi

HEALTH_URL="http://$APP_PXY6_VIRTUAL_HOST/api/health"

echo "Waiting for app to be ready at $HEALTH_URL..."
# Wait for the app to be accessible via healthcheck
timeout=60
while [ $timeout -gt 0 ]; do
    if curl -f "$HEALTH_URL" >/dev/null 2>&1; then
        echo "App is ready!"
        break
    fi
    sleep 1
    timeout=$((timeout - 1))
done

if [ $timeout -eq 0 ]; then
    echo "App failed to start within 60 seconds"
    exit 1
fi

echo "Running e2e healthcheck test..."
# Test the healthcheck endpoint and verify response
response=$(curl -s "$HEALTH_URL")
echo "Healthcheck response: $response"

# Check if response contains expected fields and database is healthy
if echo "$response" | grep -q '"status":"ok"' && echo "$response" | grep -q '"timestamp"' && echo "$response" | grep -q '"database":{"status":"ok"'; then
    echo "✓ Healthcheck test passed - app and database are healthy"
else
    echo "✗ Healthcheck test failed - app or database is not healthy"
    echo "Response details: $response"
    exit 1
fi

echo "E2E tests completed successfully"