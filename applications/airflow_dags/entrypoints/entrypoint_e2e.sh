#!/bin/bash
set -e

echo "Running e2e health check for Airflow service..."

# Check if AIRFLOW_WEB_VIRTUAL_HOST is set
if [ -z "$AIRFLOW_WEB_VIRTUAL_HOST" ]; then
    echo "✗ Error: AIRFLOW_WEB_VIRTUAL_HOST environment variable is not set"
    exit 1
fi

AIRFLOW_URL="https://${AIRFLOW_WEB_VIRTUAL_HOST}"
HEALTH_ENDPOINT="${AIRFLOW_URL}/api/v2/monitor/health"

echo "Checking Airflow health at: $HEALTH_ENDPOINT"

# Test Airflow health endpoint
HTTP_STATUS=$(curl -s -o /tmp/airflow_health.json -w "%{http_code}" "$HEALTH_ENDPOINT" || echo "000")

if [ "$HTTP_STATUS" = "200" ]; then
    echo "✓ Airflow health check passed (HTTP $HTTP_STATUS)"
    
    # Check if response contains expected health data
    if command -v jq >/dev/null 2>&1; then
        if jq -e '.metadatabase.status' /tmp/airflow_health.json >/dev/null 2>&1; then
            METADB_STATUS=$(jq -r '.metadatabase.status' /tmp/airflow_health.json)
            echo "✓ Metadatabase status: $METADB_STATUS"
        fi
        
        if jq -e '.scheduler.status' /tmp/airflow_health.json >/dev/null 2>&1; then
            SCHEDULER_STATUS=$(jq -r '.scheduler.status' /tmp/airflow_health.json)
            echo "✓ Scheduler status: $SCHEDULER_STATUS"
        fi
    else
        echo "✓ Health response received (jq not available for detailed parsing)"
    fi
    
    # Clean up
    rm -f /tmp/airflow_health.json
    
    echo "✓ Airflow e2e health check completed successfully!"
    exit 0
else
    echo "✗ Airflow health check failed (HTTP $HTTP_STATUS)"
    if [ -f /tmp/airflow_health.json ]; then
        echo "Response body:"
        cat /tmp/airflow_health.json
        rm -f /tmp/airflow_health.json
    fi
    exit 1
fi