# Dockerfile for custom Airflow service image in services/06_airflow/
# This image extends the official Airflow image to include Shopify DAG dependencies and the DAGs themselves.

ARG AIRFLOW_VERSION="3.0.2"
ARG PYTHON_VERSION="3.9" # Ensure this matches the Python version of the base image
# Official image: apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION}
# For 3.0.2, python 3.8, 3.9, 3.10, 3.11 are available. Let's stick to 3.9 as used before.
FROM docker.io/apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION}

# Set by docker-compose 'user' directive at runtime.
# ARG AIRFLOW_UID=50000
# ARG AIRFLOW_GID=0

USER root
# Install build dependencies if any Python packages need compilation (e.g., psycopg2 from source)
# The official image often has common ones like gcc, libpq-dev.
# RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*
USER airflow

# Copy requirements file from the applications/airflow_dags directory.
# The build context for this Dockerfile is services/06_airflow/
COPY ../../applications/airflow_dags/requirements.txt /requirements.txt

# Install Python dependencies for the Shopify DAGs
RUN pip install --no-cache-dir -r /requirements.txt

# Copy Shopify DAGs and common utility into the image's DAGs folder.
# It's good practice to put them in a subdirectory for better organization if other DAGs exist.
# The existing services/06_airflow/docker-compose.yml mounts a volume at /opt/airflow/dags.
# If DAGs are baked into the image AND a volume is mounted at /opt/airflow/dags, the volume mount will
# overlay and hide the DAGs baked into the image at that exact path.
# To avoid this, either:
# 1. Ensure the volume `airflow_dags` is populated correctly from an external source that includes these DAGs.
# 2. Bake DAGs into a subdirectory (e.g., /opt/airflow/dags/shopify_dags) and ensure Airflow scans it,
#    OR modify the volume mount to also be a subdirectory if only Shopify DAGs go there.
# 3. Remove the volume mount if DAGs are solely managed via the image.

# For now, let's copy them into a subfolder within the standard DAGs folder.
# Airflow will scan subfolders by default.
RUN mkdir -p /opt/airflow/dags/shopify_dags
COPY ../../applications/airflow_dags/dags/ /opt/airflow/dags/shopify_dags/

# The configure-db-entrypoint.sh and webserver_config.py are mounted via docker-compose.yml,
# so no need to COPY them here unless they were to become part of the base custom image.

# Ensure the airflow user owns the DAGs directory and files if created as root or copied from host.
# USER root
# RUN chown -R ${AIRFLOW_UID}:${AIRFLOW_GID} /opt/airflow/dags/shopify_dags
# USER airflow

WORKDIR /opt/airflow
# The base image's entrypoint will be used.
# The entrypoint is overridden in the docker-compose.yml to use configure-db-entrypoint.sh
