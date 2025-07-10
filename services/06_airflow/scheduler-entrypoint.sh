#!/bin/bash
set -e

# Read password from Docker secret or environment variable
if [ -f /run/secrets/PSQL_AIRFLOW_PASSWORD ]; then
    PSQL_AIRFLOW_PASSWORD=$(cat /run/secrets/PSQL_AIRFLOW_PASSWORD)
elif [ -n "$PSQL_AIRFLOW_PASSWORD" ]; then
    # Password already available as environment variable
    echo "Using PSQL_AIRFLOW_PASSWORD from environment variable"
else
    echo "Error: PSQL_AIRFLOW_PASSWORD not found in secrets or environment"
    exit 1
fi

# Read pxy6 database password from Docker secret or environment variable
if [ -f /run/secrets/PSQL_PXY6_AIRFLOW_PASSWORD ]; then
    PSQL_PXY6_AIRFLOW_PASSWORD=$(cat /run/secrets/PSQL_PXY6_AIRFLOW_PASSWORD)
elif [ -n "$PSQL_PXY6_AIRFLOW_PASSWORD" ]; then
    # Password already available as environment variable
    echo "Using PSQL_PXY6_AIRFLOW_PASSWORD from environment variable"
else
    echo "Error: PSQL_PXY6_AIRFLOW_PASSWORD not found in secrets or environment"
    exit 1
fi

export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="postgresql+psycopg2://airflow:${PSQL_AIRFLOW_PASSWORD}@db/airflow"
export PXY6_DATABASE_URL="postgresql+psycopg2://pxy6_airflow:${PSQL_PXY6_AIRFLOW_PASSWORD}@db/pxy6"

# Read Google OAuth client secret from Docker secret if available
if [ -f /run/secrets/GOOGLE_OAUTH_CLIENT_SECRET ]; then
    GOOGLE_OAUTH_CLIENT_SECRET=$(cat /run/secrets/GOOGLE_OAUTH_CLIENT_SECRET)
    export GOOGLE_OAUTH_CLIENT_SECRET="${GOOGLE_OAUTH_CLIENT_SECRET}"
    echo "Google OAuth client secret loaded from Docker secret"
fi

# Scheduler-specific operations
echo 'Installing pxy6 package before starting scheduler...'

# Wait for DAGs to be deployed
echo 'Waiting for DAGs to be deployed...'
max_wait=60  # Maximum wait time in seconds
waited=0
while true; do
  # Check if any Python files exist in the dags directory
  if find /opt/airflow/dags -name "*.py" -type f | grep -q .; then
    echo 'DAGs found in /opt/airflow/dags/'
    break
  fi
  
  if [ $waited -ge $max_wait ]; then
    echo "Warning: No DAGs found after ${max_wait} seconds, proceeding anyway..."
    break
  fi
  
  echo "No DAGs found yet, waiting... (${waited}s elapsed)"
  sleep 5
  waited=$((waited + 5))
done

# Install pxy6 package and dependencies from the shared package files
cd /opt/airflow
pip install --no-cache-dir -r requirements.txt
pip install --no-cache-dir -e .

echo 'pxy6 package installed successfully'
echo 'Verifying installation:'
python -c 'from pxy6.utils import get_postgres_hook; print("✓ pxy6 package working")'

echo 'Starting Airflow scheduler...'
exec /entrypoint airflow scheduler