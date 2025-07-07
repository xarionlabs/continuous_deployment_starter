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

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime environment
FROM python:3.9-slim as runtime

# Environment variables for runtime
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r airflow && useradd -r -g airflow airflow

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/airflow/.local

# Copy application code
COPY . .

# Set correct ownership and permissions
RUN chown -R airflow:airflow /app /home/airflow/.local && \
    chmod +x /app/entrypoints/*.sh

# Switch to non-root user
USER airflow

# Add user packages to PATH
ENV PATH="/home/airflow/.local/bin:$PATH"

# Default entrypoint
ENTRYPOINT ["./entrypoints/entrypoint.sh"]