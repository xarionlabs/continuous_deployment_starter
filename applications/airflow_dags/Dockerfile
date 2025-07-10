# Multi-stage Dockerfile for Airflow DAGs package
# Stage 1: Build environment
FROM python:3.9-slim as builder

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file first for better caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy package files and install the pxy6 package
COPY setup.py pyproject.toml ./
COPY src/ ./src/

# Install the pxy6 package in development mode
RUN /opt/venv/bin/pip install --no-cache-dir -e .

# Stage 2: Runtime environment
FROM python:3.9-slim as runtime

# Environment variables for runtime
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r airflow && useradd -r -g airflow airflow

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code and DAGs
COPY src/ ./src/
COPY dags/ ./dags/
COPY entrypoints/ ./entrypoints/
COPY tests/ ./tests/
COPY *.sh ./
COPY pytest.ini ./
COPY requirements.txt ./
COPY setup.py ./
COPY pyproject.toml ./

# Set correct ownership and permissions
RUN chown -R airflow:airflow /app /opt/venv && \
    chmod +x /app/entrypoints/*.sh

# Switch to non-root user
USER airflow

# Verify virtual environment is working
RUN python -c "import sys; print('Python executable:', sys.executable)" && \
    python -c "import site; print('Site packages:', site.getsitepackages())" && \
    pip list --format=freeze | head -5

# Default entrypoint
ENTRYPOINT ["./entrypoints/entrypoint.sh"]