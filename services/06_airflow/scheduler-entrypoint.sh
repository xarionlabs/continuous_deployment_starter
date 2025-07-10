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
while [ ! -f /opt/airflow/dags/shopify_data_pipeline.py ]; do
  echo 'Waiting for DAGs to be deployed...'
  sleep 5
done

# Install pxy6 package and dependencies from the shared package files
cd /opt/airflow
pip install --no-cache-dir -r requirements.txt
pip install --no-cache-dir -e .

echo 'pxy6 package installed successfully'
echo 'Verifying installation:'
python -c 'from pxy6.utils.database import DatabaseManager; print("✓ pxy6 package working")'

echo 'Starting Airflow scheduler...'
exec /entrypoint airflow scheduler