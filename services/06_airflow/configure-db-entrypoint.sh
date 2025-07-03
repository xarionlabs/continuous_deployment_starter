#!/bin/bash
set -euf -o pipefail

# Helper function to read value from a file path specified by an environment variable
# Usage: read_from_file_env <VAR_TO_SET> <FILE_ENV_VAR_NAME> [default_value]
read_from_file_env() {
    local var_name="$1"
    local file_env_var_name="$2" # This variable holds the path to the secret file
    local default_value="${3:-}"
    local secret_file_path="${!file_env_var_name:-}" # Dereference to get the path

    if [ -n "$secret_file_path" ] && [ -f "$secret_file_path" ]; then
        echo "Reading $var_name from file: $secret_file_path"
        export "$var_name"="$(cat "$secret_file_path")"
    elif [ -n "$default_value" ]; then
        echo "Using default value for $var_name as $file_env_var_name was not set or file not found."
        export "$var_name"="$default_value"
    else
        echo "Warning: $var_name not set. $file_env_var_name was not set or file $secret_file_path not found, and no default value provided." >&2
    fi
}

# --- Configure Airflow Metadata Database Connection ---
# Variables like DB_HOST, DB_PORT, DB_DATABASE, DB_USER, DB_PASSWORD_FILE are expected from docker-compose env.
DB_PASSWORD=""
if [ -n "${DB_PASSWORD_FILE:-}" ] && [ -f "${DB_PASSWORD_FILE}" ]; then
    DB_PASSWORD=$(cat "${DB_PASSWORD_FILE}")
    echo "Read Airflow metadata DB password from ${DB_PASSWORD_FILE}."
else
    echo "Error: DB_PASSWORD_FILE (${DB_PASSWORD_FILE:-not set}) for Airflow metadata not found or not set." >&2
    exit 1
fi

if [ -z "${DB_HOST:-}" ] || [ -z "${DB_USER:-}" ] || [ -z "${DB_DATABASE:-}" ]; then
  echo "Error: DB_HOST, DB_USER, DB_DATABASE must be set for Airflow metadata DB." >&2
  exit 1
fi
DB_PORT="${DB_PORT:-5432}" # Default PostgreSQL port
export AIRFLOW__CORE__SQL_ALCHEMY_CONN="postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_DATABASE}"
echo "AIRFLOW__CORE__SQL_ALCHEMY_CONN set to: postgresql+psycopg2://${DB_USER}:****@${DB_HOST}:${DB_PORT}/${DB_DATABASE}"


# --- Configure Fernet Key ---
read_from_file_env "AIRFLOW__CORE__FERNET_KEY" "AIRFLOW__CORE__FERNET_KEY_FILE"
if [ -z "${AIRFLOW__CORE__FERNET_KEY:-}" ]; then
    echo "Error: AIRFLOW__CORE__FERNET_KEY is not set. Please provide it via AIRFLOW__CORE__FERNET_KEY_FILE." >&2
    # In production, a fernet key must be set. For dev, one could be generated:
    # export AIRFLOW__CORE__FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    # But for a service, it must be persistent and shared.
    exit 1
fi

# --- Configure Google OAuth (if used) ---
# GOOGLE_OAUTH_CLIENT_ID is expected as a direct env var from docker-compose
# GOOGLE_OAUTH_CLIENT_SECRET_FILE is expected from docker-compose, pointing to a secret file path
if [ -n "${GOOGLE_OAUTH_CLIENT_ID:-}" ]; then
    read_from_file_env "GOOGLE_OAUTH_CLIENT_SECRET" "GOOGLE_OAUTH_CLIENT_SECRET_FILE"
    if [ -n "${GOOGLE_OAUTH_CLIENT_SECRET:-}" ]; then
        echo "Google OAuth Client ID and Secret are configured."
    else
        echo "Warning: GOOGLE_OAUTH_CLIENT_ID is set, but GOOGLE_OAUTH_CLIENT_SECRET could not be read." >&2
    fi
else
    echo "Google OAuth not configured (GOOGLE_OAUTH_CLIENT_ID not set)."
fi


# --- Load Shopify and App DB Credentials for DAGs ---
# These will be available as environment variables to the Airflow processes.
# DAGs (shopify_common.py) can then access them using os.getenv() or prefer Airflow Connections.
echo "Loading credentials for Shopify DAGs..."
read_from_file_env "SHOPIFY_API_KEY" "SHOPIFY_API_KEY_FILE"
read_from_file_env "SHOPIFY_API_PASSWORD" "SHOPIFY_API_PASSWORD_FILE"
read_from_file_env "SHOPIFY_STORE_DOMAIN" "SHOPIFY_STORE_DOMAIN_FILE"

read_from_file_env "APP_DB_HOST" "APP_DB_HOST_FILE"
read_from_file_env "APP_DB_PORT" "APP_DB_PORT_FILE" "5432" # Default App DB port
read_from_file_env "APP_DB_NAME" "APP_DB_NAME_FILE"
read_from_file_env "APP_DB_USER" "APP_DB_USER_FILE"
read_from_file_env "APP_DB_PASSWORD" "APP_DB_PASSWORD_FILE"

# --- Create/Update Airflow Connection for Application Database ---
# AIRFLOW_CONN_APP_DB_CONN_ID is set in docker-compose.yml (e.g., "app_db_main_application")
# This step should ideally run after `airflow db migrate` or `airflow db init` has completed.
# The `airflow-init` service handles `db migrate`. Webserver and Scheduler start after `airflow-init`.
# So, this connection setup should be safe here when run by webserver/scheduler entrypoints.
# For the `airflow db migrate` command itself, this part might not be necessary or might fail if run too early.
# We check if the command being run is 'webserver' or 'scheduler' before attempting to add connection.
if [[ "$1" == "webserver" || "$1" == "scheduler" ]]; then
    if [ -n "${APP_DB_HOST:-}" ] && \
       [ -n "${APP_DB_PORT:-}" ] && \
       [ -n "${APP_DB_NAME:-}" ] && \
       [ -n "${APP_DB_USER:-}" ] && \
       [ -n "${APP_DB_PASSWORD:-}" ] && \
       [ -n "${AIRFLOW_CONN_APP_DB_CONN_ID:-}" ]; then
      echo "Attempting to create/update Airflow connection '${AIRFLOW_CONN_APP_DB_CONN_ID}' for application database..."
      # Use a subshell to avoid exiting the main script if airflow command fails (e.g. connection already exists)
      (airflow connections add "${AIRFLOW_CONN_APP_DB_CONN_ID}" \
        --conn-type "postgres" \
        --conn-host "${APP_DB_HOST}" \
        --conn-port "${APP_DB_PORT}" \
        --conn-schema "${APP_DB_NAME}" \
        --conn-login "${APP_DB_USER}" \
        --conn-password "${APP_DB_PASSWORD}" \
        && echo "Connection ${AIRFLOW_CONN_APP_DB_CONN_ID} processed successfully.") || \
        echo "Warning: Failed to add/update connection ${AIRFLOW_CONN_APP_DB_CONN_ID}. It might already exist with the same configuration, or Airflow is not fully ready."
    else
        echo "Skipping creation of Airflow connection for App DB as not all required APP_DB_* or AIRFLOW_CONN_APP_DB_CONN_ID env vars are set for it."
    fi
else
    echo "Skipping Airflow connection setup for command: $1"
fi

echo "Configuration complete. Executing original Airflow entrypoint with command: $@"
# Execute the original Airflow entrypoint (from base image) with all arguments passed to this script
exec /entrypoint "$@"