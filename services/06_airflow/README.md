# Airflow Service (`services/06_airflow`)

## Overview

This directory contains the service definition for deploying the main Apache Airflow instance for this project. This instance is responsible for orchestrating various data pipelines and workflows.

As of recent updates, this Airflow service now also includes **Shopify Data Integration DAGs** designed to fetch data from Shopify stores and load it into the application's PostgreSQL database.

## Key Features & Configuration

-   **Executor**: Uses `LocalExecutor` for running tasks.
-   **Custom Docker Image**: Builds a custom Docker image named `airflow_service_prod:${TAG}` using the `Dockerfile` in this directory.
    -   Base Image: `docker.io/apache/airflow:3.0.2`.
    -   Python Dependencies: Installs additional Python packages required for the Shopify DAGs (e.g., `ShopifyAPI`, `psycopg2-binary`, `pandas`) from `applications/airflow_dags/requirements.txt`.
    -   Shopify DAGs: Copies DAG files from `applications/airflow_dags/dags/` into `/opt/airflow/dags/shopify_dags/` within the image.
-   **Database Backend**: Connects to an external/shared PostgreSQL database for Airflow metadata. Connection details are provided via environment variables and secrets.
-   **Secrets Management**: Sensitive configurations (database passwords, API keys, Fernet key) are managed via Docker secrets. The `configure-db-entrypoint.sh` script reads these secrets from files and makes them available to Airflow.
-   **Entrypoint**: Uses a custom `configure-db-entrypoint.sh` script to:
    -   Construct the `AIRFLOW__CORE__SQL_ALCHEMY_CONN` for Airflow's metadata database.
    -   Set the `AIRFLOW__CORE__FERNET_KEY`.
    -   Load Shopify API credentials and Application Database connection details from secrets, making them available as environment variables.
    -   Attempt to create/update an Airflow Connection (default ID: `app_db_main_application`) for the main application database (where Shopify data is stored).
-   **Included Components**:
    -   `airflow-webserver`: The Airflow web UI.
    -   `airflow-scheduler`: The Airflow scheduler responsible for monitoring and triggering DAGs.
    -   `airflow-init`: A one-off service to handle database migrations (`airflow db migrate`) and initial admin user creation.
-   **Google OAuth**: Includes configuration for Google OAuth for Airflow UI authentication (optional, based on environment variable settings).

## Service Definition Files

-   `docker-compose.yml`: Defines the Airflow services for deployment.
-   `Dockerfile`: Builds the custom Airflow image with Shopify DAG dependencies and DAG files.
-   `configure-db-entrypoint.sh`: Custom entrypoint script for Airflow containers.
-   `webserver_config.py`: Custom Airflow webserver configuration (e.g., for Google OAuth).
-   `.env.example`: Example environment variables that might be used for local testing or to understand what variables the `docker-compose.yml` expects (though for production, these are typically injected by the deployment system).

## Prerequisites for Deployment

1.  **Custom Docker Image**: If not built by the deployment system directly, the `airflow_service_prod:${TAG}` image must be pre-built and available in your container registry.
    ```bash
    # From the services/06_airflow/ directory:
    docker build -t your-registry/airflow_service_prod:your-tag .
    docker push your-registry/airflow_service_prod:your-tag
    # Ensure image name in docker-compose.yml matches.
    ```
    The `docker-compose.yml` is set up with `build: .` so it can also build the image during deployment.

2.  **Shared PostgreSQL Database**: An external PostgreSQL server must be available for Airflow's metadata. A dedicated database (e.g., `airflow_prod_meta`) and user should be created for this Airflow instance.

3.  **Docker Secrets**: All secrets referenced in `docker-compose.yml` must be created in your Docker Swarm / Kubernetes environment. The `*_FILE` environment variables in `docker-compose.yml` (e.g., `PSQL_AIRFLOW_PASSWORD_FILE`) should point to the paths where these secrets are mounted inside the containers (e.g., `/run/secrets/secret_name`). Secrets include:
    -   `psql_airflow_password`: Password for Airflow's metadata database user.
    -   `airflow_fernet_key`: Fernet key for encrypting connections.
    -   `google_oauth_client_secret` (if Google OAuth is used).
    -   `shopify_api_key`, `shopify_api_password`, `shopify_store_domain`: Shopify credentials for the new DAGs.
    -   `app_db_host`, `app_db_port`, `app_db_name`, `app_db_user`, `app_db_password`: Connection details for the main application database where Shopify data will be stored.

4.  **Environment Variables**: The deployment system must provide all required environment variables to `docker-compose.yml`, including:
    -   `TAG`: Docker image tag (e.g., `latest`).
    -   `AIRFLOW_UID`, `AIRFLOW_GID`: For file permissions.
    -   `AIRFLOW_ADMIN_USER`, `AIRFLOW_ADMIN_PASSWORD`: For the initial Airflow admin user.
    -   `AIRFLOW_METADATA_DB_HOST`, `AIRFLOW_METADATA_DB_PORT`, `AIRFLOW_METADATA_DB_NAME`, `AIRFLOW_METADATA_DB_USER`: Connection details for Airflow's metadata database.
    -   Paths to secret files (e.g., `PSQL_AIRFLOW_PASSWORD_FILE`, `SHOPIFY_API_KEY_FILE`).
    -   `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_DOMAIN_WHITELIST` (if used).
    -   `AIRFLOW_WEB_VIRTUAL_HOST` (if using a reverse proxy).
    -   Network names: `AIRFLOW_METADATA_DB_NETWORK_NAME`, `APP_DB_NETWORK_NAME`, `PROXY_NETWORK_NAME`.

5.  **External Docker Networks**: The Docker networks specified (e.g., for DB, App DB, Proxy) must exist.

## Deployment

Deploy using your standard Docker Compose or Docker Swarm/Kubernetes deployment procedures, ensuring all environment variables and secrets are correctly supplied.

## Shopify Data Integration DAGs

-   **Location in Image**: Copied to `/opt/airflow/dags/shopify_dags/`.
-   **Dependencies**: `ShopifyAPI`, `psycopg2-binary`, `pandas` (installed via `Dockerfile`).
-   **Functionality**:
    -   Fetch past purchase data from Shopify.
    -   Fetch store metadata (products, collections) from Shopify.
    -   Store this data in the main application database (connection configured via `app_db_main_application` Airflow Connection, set up by the entrypoint script from secrets).
-   **Triggering**: Can be run on a schedule (defined in DAGs) or triggered via the Airflow API by applications like `app.pxy6.com`.

## Important Considerations

-   **Database for Airflow Metadata**: This service requires its own database for Airflow metadata.
-   **Application Database Connection**: The Shopify DAGs connect to the main application database using an Airflow Connection (default ID `app_db_main_application`). Ensure the secrets for this connection (`APP_DB_*_FILE`) point to the correct application database.
-   **Security**: Manage all secrets securely.
-   **Resource Allocation**: Adjust CPU/memory for Airflow services as needed.
