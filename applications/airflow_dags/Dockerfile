# Dockerfile for testing and packaging Airflow DAGs
# This image is used for CI/CD testing of DAGs, not for running Airflow itself
# The actual Airflow service is in services/06_airflow/
# Updated with proper entrypoint copying - testing hook

FROM apache/airflow:3.0.2-python3.9

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Copy DAGs and tests
COPY dags/ ./dags/
COPY tests/ ./tests/
COPY plugins/ ./plugins/

# Copy entrypoints (they should already be executable)
COPY entrypoints/ ./entrypoints/

# Default working directory for tests
WORKDIR /app
