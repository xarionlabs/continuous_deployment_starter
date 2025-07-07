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

export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="postgresql+psycopg2://airflow:${PSQL_AIRFLOW_PASSWORD}@db/airflow"

# Read Google OAuth client secret from Docker secret if available
if [ -f /run/secrets/GOOGLE_OAUTH_CLIENT_SECRET ]; then
    GOOGLE_OAUTH_CLIENT_SECRET=$(cat /run/secrets/GOOGLE_OAUTH_CLIENT_SECRET)
    export GOOGLE_OAUTH_CLIENT_SECRET="${GOOGLE_OAUTH_CLIENT_SECRET}"
    echo "Google OAuth client secret loaded from Docker secret"
fi

# Execute the original entrypoint with all arguments
exec /entrypoint "$@"