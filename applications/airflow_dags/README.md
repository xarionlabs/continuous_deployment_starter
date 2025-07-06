# Airflow DAGs for Shopify Data Integration

This project contains Apache Airflow DAGs designed to fetch data from Shopify stores and load it into a PostgreSQL database. This data can then be used by other applications, such as `app.pxy6.com`.

## Overview

The primary goals of this Airflow setup are:
1.  **Fetch Past Purchase Data**: Regularly pull order history and line item details from Shopify.
2.  **Fetch Store Metadata**: Regularly pull product catalog information (products, variants, images), collections (custom and smart), and other relevant store metadata.
3.  **Expose DAGs via API**: Allow external applications (like `app.pxy6.com`) to trigger these data refresh processes on demand via Airflow's REST API.

## Project Structure

-   `dags/`: Contains the Python DAG definition files.
    -   `shopify_common.py`: Shared utilities for Shopify API interaction and database operations.
    -   `shopify_get_past_purchases_dag.py`: DAG for fetching order data.
    -   `shopify_get_store_metadata_dag.py`: DAG for fetching products, collections, etc.
-   `plugins/`: For any custom Airflow plugins (currently empty).
-   `Dockerfile`: Defines the custom Docker image for running these Airflow DAGs, including necessary Python dependencies. Builds an image named `airflow-shopify-dags-dev:latest` (for local dev) or `airflow_shopify_dags:(TAG)` (for service deployment).
-   `docker-compose.yaml`: For local development. Sets up Airflow services (webserver, scheduler) using `LocalExecutor` and a dedicated PostgreSQL database for Airflow metadata.
-   `entrypoint_dev.sh`: Entrypoint script for local development Docker Compose setup. Automatically creates an Airflow Connection for the application database using environment variables.
-   `.env.example`: Example environment variables for local development. Copy to `.env` and customize.
-   `requirements.txt`: Python dependencies required by the DAGs and plugins.

## Local Development Setup

1.  **Prerequisites**:
    *   Docker and Docker Compose installed.
    *   Access to a running PostgreSQL instance that will serve as the main application database (where Shopify data will be stored).
    *   Shopify store credentials (API Key, API Password/Admin Access Token, Store Domain).

2.  **Configuration**:
    *   Copy `.env.example` to `.env` in the `applications/airflow_dags/` directory.
    *   Edit `.env` to provide:
        *   `AIRFLOW_UID`, `AIRFLOW_GID` (usually `50000` and `0` are fine).
        *   `AIRFLOW_WEBSERVER_HOST_PORT` (e.g., `8081` for Airflow UI).
        *   `AIRFLOW_METADATA_DB_HOST_PORT` (e.g., `5434` if you want to access Airflow's metadata DB from host).
        *   Shopify credentials: `SHOPIFY_API_KEY`, `SHOPIFY_API_PASSWORD`, `SHOPIFY_STORE_DOMAIN`.
        *   Application Database connection details (where Shopify data will be written by DAGs):
            *   `APP_DB_HOST`: Hostname or IP of your application's PostgreSQL server (e.g., `host.docker.internal` if DB is on host and using Docker Desktop, or `172.17.0.1` for Docker on Linux, or a Docker service name if DB is another container on a shared network).
            *   `APP_DB_PORT`: Port of your application's PostgreSQL server.
            *   `APP_DB_NAME`: Database name.
            *   `APP_DB_USER`: Username for the database.
            *   `APP_DB_PASSWORD`: Password for the database.
            *   `AIRFLOW_CONN_APP_DB_CONN_ID`: Airflow Connection ID that DAGs will use (default: `app_db_main_application`). The `entrypoint_dev.sh` will create this connection using the `APP_DB_*` variables.

3.  **Build and Run Airflow**:
    ```bash
    cd applications/airflow_dags
    docker-compose build
    docker-compose up -d
    ```

4.  **Access Airflow UI**:
    *   Open your browser to `http://localhost:<AIRFLOW_WEBSERVER_HOST_PORT>` (e.g., `http://localhost:8081`).
    *   Log in with credentials `admin`/`admin` (or as set in your `.env` file for `AIRFLOW_ADMIN_USER`/`AIRFLOW_ADMIN_PASSWORD`).

5.  **Using the DAGs**:
    *   In the Airflow UI, you should see `shopify_fetch_past_purchases` and `shopify_fetch_store_metadata` DAGs.
    *   Ensure the Airflow Connection `app_db_main_application` (or your configured `AIRFLOW_CONN_APP_DB_CONN_ID`) exists under Admin -> Connections and points to your application database. The `entrypoint_dev.sh` script attempts to create this.
    *   You can manually trigger these DAGs from the UI.
    *   Monitor their execution and check logs for any issues.
    *   Verify that data is being populated in your application database tables (`ShopifyOrder`, `ShopifyProduct`, etc.).

## Key Components & Logic

-   **DAGs**:
    -   `shopify_fetch_past_purchases`: Fetches orders and their line items. Uses `updated_at_min` for incremental loads based on the previous successful run or a configurable lookback period for initial runs. Handles upserts into `ShopifyOrder` and `ShopifyOrderLineItem` tables.
    -   `shopify_fetch_store_metadata`: Fetches products (with variants and images), custom collections, and smart collections. Also uses `updated_at_min` for incremental updates. Handles upserts into respective tables (`ShopifyProduct`, `ShopifyProductVariant`, `ShopifyProductImage`, `ShopifyCollection`, `ShopifySmartCollection`).
-   **`shopify_common.py`**:
    -   `get_shopify_session()`: Manages connection to the Shopify API using credentials from environment variables or Airflow Variables.
    -   `get_app_db_hook()`: Provides a `PostgresHook` to the application database using the connection ID `app_db_main_application`.
    -   Upsert logic in DAGs uses `ON CONFLICT DO UPDATE` with PostgreSQL.
-   **Database Schema**: The expected PostgreSQL table structures are defined by the Prisma schema in `applications/app.pxy6.com/src/prisma/schema.prisma`. Ensure migrations have been run for that application to create these tables.

## Triggering DAGs via API (for `app.pxy6.com`)

The Airflow webserver exposes a REST API. `app.pxy6.com` uses this API to trigger DAG runs.
-   **Endpoint to trigger a DAG**: `POST /api/v1/dags/{dag_id}/dagRuns`
-   **Authentication**: Basic Authentication is enabled. `app.pxy6.com` needs to be configured with Airflow API URL, username, and password.

## Environment Variables for DAGs (within Airflow execution context)

These are primarily sourced from the `.env` file for local development or injected by the service environment for deployment.
-   `SHOPIFY_API_KEY`, `SHOPIFY_API_PASSWORD`, `SHOPIFY_STORE_DOMAIN`: For Shopify connection.
-   `APP_DB_HOST`, `APP_DB_PORT`, `APP_DB_NAME`, `APP_DB_USER`, `APP_DB_PASSWORD`: Used by the entrypoint script to create the Airflow connection for the application DB.
-   Airflow Variables (set via UI/CLI or environment variables like `AIRFLOW_VAR_<NAME>`) can also be used, e.g., `shopify_store_domain`, `app_db_conn_id`. The `shopify_common.py` prefers Airflow Variables if available.

## Deployment

These Shopify DAGs are designed to be deployed as part of the existing Airflow instance defined in `services/06_airflow/`.
The `services/06_airflow/docker-compose.yml` and its associated `Dockerfile` have been updated to:
- Build a custom Airflow image that includes the Python dependencies listed in `applications/airflow_dags/requirements.txt`.
- Copy the DAGs from `applications/airflow_dags/dags/` into the custom image.
- Manage necessary environment variables and secrets for Shopify API access and connection to the application database.

Refer to the `README.md` in `services/06_airflow/` for detailed deployment instructions for that Airflow service, now including these Shopify DAGs.
The local development setup described above in this README remains a valid way to test and develop these Shopify DAGs in isolation.

## Testing

This project uses `pytest` for testing DAG integrity and custom logic within DAG tasks and helper modules.

### Prerequisites for Testing

1.  **Python Environment**: Ensure you have a Python environment (e.g., a virtual environment) with Python 3.8+ (matching Airflow's supported versions).
2.  **Install Dependencies**:
    *   Install main dependencies: `pip install -r requirements.txt`
    *   Install development/test dependencies: `pip install -r requirements-dev.txt`

### Running Tests

Navigate to the `applications/airflow_dags` directory in your terminal. Then, run `pytest`:

```bash
cd applications/airflow_dags
pytest
```

Or, to run specific test files:

```bash
pytest tests/test_dag_integrity.py
pytest tests/test_shopify_common.py
# etc.
```

The tests are located in the `applications/airflow_dags/tests/` directory and include:
-   `test_dag_integrity.py`: Checks that DAGs can be imported and have basic structural validity.
-   `test_shopify_common.py`: Unit tests for helper functions in `dags/shopify_common.py`.
-   `test_shopify_get_past_purchases_dag.py`: Integration-style tests for tasks in the past purchases DAG, mocking external Shopify and DB interactions.
-   `test_shopify_get_store_metadata_dag.py`: Integration-style tests for tasks in the store metadata DAG, mocking external Shopify and DB interactions.

### Testing within Docker (Optional)

You can also run tests inside the Docker container built by `Dockerfile` if you prefer, especially to ensure the environment is identical.
1.  Build the Docker image with development dependencies:
    ```bash
    # In applications/airflow_dags/
    docker-compose build --build-arg INSTALL_DEV_DEPS=true airflow-webserver
    # (or any service that uses the base airflow image like airflow-scheduler)
    # Or, if building manually:
    # docker build --build-arg INSTALL_DEV_DEPS=true -t airflow-shopify-dags-dev-testable .
    ```
2.  Run pytest inside the container:
    ```bash
    # Using docker-compose to run a one-off command in a service container (e.g., webserver)
    docker-compose run --rm airflow-webserver pytest /opt/airflow/tests
    # (This assumes you COPY your tests into /opt/airflow/tests in Dockerfile or mount them)

    # Alternatively, if you built manually and have tests copied into the image:
    # docker run --rm airflow-shopify-dags-dev-testable pytest /opt/airflow/tests
    ```
    **Note**: For the `docker-compose run` approach, you might need to adjust volume mounts or `COPY` instructions in the `Dockerfile` to ensure the `tests/` directory is accessible within the container at `/opt/airflow/tests`. The current `Dockerfile` does not copy the `tests` directory. You would need to add:
    `COPY tests/ /opt/airflow/tests/` to the `Dockerfile`.
