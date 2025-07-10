#!/usr/bin/env bash
set -euf -o pipefail

# This entrypoint is for the local development docker-compose setup.
# It primarily sets up an Airflow connection for the application database
# using environment variables, making it easier to get started without
# manually configuring it in the Airflow UI.

# Default AIRFLOW_UID to 50000 if not set
AIRFLOW_UID="${AIRFLOW_UID:-50000}"

# Ensure the script is executable
chmod +x /opt/airflow/entrypoint_dev.sh

# Create Airflow Connection for App DB if relevant env vars are set
# This makes it available for DAGs if they use the specified conn_id
# These APP_DB_* vars and AIRFLOW_CONN_APP_DB_CONN_ID are passed from docker-compose environment.
if [ -n "${APP_DB_HOST:-}" ] && \
   [ -n "${APP_DB_PORT:-}" ] && \
   [ -n "${APP_DB_NAME:-}" ] && \
   [ -n "${APP_DB_USER:-}" ] && \
   [ -n "${APP_DB_PASSWORD:-}" ] && \
   [ -n "${AIRFLOW_CONN_APP_DB_CONN_ID:-}" ]; then
  echo "Attempting to create/update Airflow connection ${AIRFLOW_CONN_APP_DB_CONN_ID} for application database..."

  # The 'airflow connections add' command might run before the DB is fully initialized by 'airflow db init'
  # in the airflow-init service, especially on the first run.
  # A small delay or a more robust check for Airflow readiness might be needed if issues arise.
  # However, 'airflow-init' depends on 'postgres_airflow_meta', and other services depend on 'airflow-init'.
  # This entrypoint runs in webserver & scheduler, which start after init.

  # Check if airflow db init has completed by looking for a common table.
  # This is a simple check. A more robust method would be to use `airflow db check`.
  # However, `airflow db check` might also need the db to be initialized.
  # For now, assume that by the time webserver/scheduler start, init is done.

  airflow connections add "${AIRFLOW_CONN_APP_DB_CONN_ID}" \
    --conn-type "postgres" \
    --conn-host "${APP_DB_HOST}" \
    --conn-port "${APP_DB_PORT}" \
    --conn-schema "${APP_DB_NAME}" \
    --conn-login "${APP_DB_USER}" \
    --conn-password "${APP_DB_PASSWORD}" \
    || echo "Failed to add/update connection ${AIRFLOW_CONN_APP_DB_CONN_ID}. This might be okay if it already exists with the same configuration or if another process is also trying to create it."
else
    echo "Skipping creation of Airflow connection for App DB as not all required APP_DB_* or AIRFLOW_CONN_APP_DB_CONN_ID env vars are set."
    echo "APP_DB_HOST: ${APP_DB_HOST:-not set}"
    echo "APP_DB_PORT: ${APP_DB_PORT:-not set}"
    echo "APP_DB_NAME: ${APP_DB_NAME:-not set}"
    echo "APP_DB_USER: ${APP_DB_USER:-not set}"
    echo "APP_DB_PASSWORD: ${APP_DB_PASSWORD:-not set (hidden)}"
    echo "AIRFLOW_CONN_APP_DB_CONN_ID: ${AIRFLOW_CONN_APP_DB_CONN_ID:-not set}"
fi

# Original Airflow entrypoint logic might involve more, like chown.
# This script assumes permissions are handled by `user:` directive in docker-compose.
# Drop root privileges if running as root, to match Airflow's default user
# The `user:` directive in docker-compose should make this unnecessary if set to airflow user's UID (e.g. 50000)
if [ "$(id -u)" = "0" ]; then
    echo "Switching to user airflow (UID ${AIRFLOW_UID})"
    # The command to run (webserver, scheduler) is passed as arguments to this script ($@)
    exec su-exec airflow "$@"
else
    # If already running as the correct user
    exec "$@"
fi
