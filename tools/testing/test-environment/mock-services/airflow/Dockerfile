FROM apache/airflow:2.7.1-python3.11

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Copy requirements and install Python dependencies
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
USER root
RUN chmod +x /entrypoint.sh
USER airflow

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=5 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start the application
CMD ["/entrypoint.sh"]