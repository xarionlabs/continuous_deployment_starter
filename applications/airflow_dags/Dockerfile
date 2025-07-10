# Dockerfile for testing and packaging Airflow DAGs
# This image is used for CI/CD testing of DAGs, not for running Airflow itself
# The actual Airflow service is in services/06_airflow/
# Updated with proper entrypoint copying - testing hook

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for some Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Copy DAGs and tests
COPY dags/ ./dags/
COPY tests/ ./tests/
COPY *.sh ./
COPY pytest.ini ./
COPY requirements.txt ./
COPY setup.py ./
COPY pyproject.toml ./

# Copy entrypoints (they should already be executable)
COPY entrypoints/ ./entrypoints/

# Default working directory for tests
WORKDIR /app
