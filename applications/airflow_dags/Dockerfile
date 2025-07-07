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

# Copy application code
COPY . .

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