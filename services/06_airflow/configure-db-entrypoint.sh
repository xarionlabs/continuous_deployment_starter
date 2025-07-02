#!/bin/bash
set -e

# Read password from Docker secret
if [ -f /run/secrets/PSQL_AIRFLOW_PASSWORD ]; then
    PSQL_AIRFLOW_PASSWORD=$(cat /run/secrets/PSQL_AIRFLOW_PASSWORD)
    export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="postgresql+psycopg2://airflow:${PSQL_AIRFLOW_PASSWORD}@db/airflow"
else
    echo "Error: PSQL_AIRFLOW_PASSWORD secret not found"
    exit 1
fi

# Read Google OAuth client secret from Docker secret if available
if [ -f /run/secrets/GOOGLE_OAUTH_CLIENT_SECRET ]; then
    GOOGLE_OAUTH_CLIENT_SECRET=$(cat /run/secrets/GOOGLE_OAUTH_CLIENT_SECRET)
    export GOOGLE_OAUTH_CLIENT_SECRET="${GOOGLE_OAUTH_CLIENT_SECRET}"
    echo "Google OAuth client secret loaded from Docker secret"
fi

# Execute the original entrypoint with all arguments
exec /entrypoint "$@"