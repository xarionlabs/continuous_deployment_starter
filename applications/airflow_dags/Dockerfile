# Start with the official Apache Airflow image
# This Dockerfile is for when you need to build a CUSTOM image.
# If you are using the official apache/airflow:3.0.2 image directly in docker-compose.yaml,
# then this Dockerfile is not strictly used unless you change the image source back to a build context.
FROM apache/airflow:3.0.2-python3.9

# Set the Airflow home directory (already set in base image, but good for clarity)
ENV AIRFLOW_HOME=/opt/airflow

# Example: Add OS-level dependencies if needed by your custom Python packages
# USER root
# RUN apt-get update && \
#     apt-get install -y --no-install-recommends \
#     libpq-dev gcc \
#     # Add other build-essential or runtime dependencies here
#     && apt-get clean && \
#     rm -rf /var/lib/apt/lists/*
# USER airflow

# Copy requirements.txt and install Python dependencies
# These are dependencies BEYOND what's in the base Airflow image or if you need specific versions.
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# --- Development/Testing Dependencies (Optional) ---
# Argument to control installation of development dependencies
ARG INSTALL_DEV_DEPS=false
# Copy dev requirements if they exist and INSTALL_DEV_DEPS is true
COPY requirements-dev.txt /requirements-dev.txt
RUN if [ "$INSTALL_DEV_DEPS" = "true" ]; then \
        pip install --no-cache-dir -r /requirements-dev.txt && \
        echo "Development dependencies installed."; \
    else \
        echo "Skipping installation of development dependencies."; \
    fi
# Clean up requirements files if they were copied, to keep image clean
RUN rm -f /requirements.txt /requirements-dev.txt


# Copy DAGs, plugins, and any other custom scripts/configs into the image
# Note: docker-compose.yaml also mounts ./dags and ./plugins as volumes for development,
# which will override these COPY instructions if the paths are the same.
# For a production image build, you'd typically rely on these COPY statements.
COPY dags/ /opt/airflow/dags/
COPY plugins/ /opt/airflow/plugins/

# Expose Airflow webserver port (already exposed in base image)
# EXPOSE 8080

# Default command is handled by the base image or docker-compose.
# CMD ["airflow", "standalone"]

# Healthcheck is also often part of the base image or managed by compose.
# HEALTHCHECK CMD ["airflow", "jobs", "check", "--job-type", "SchedulerJob", "--local"]

# Ensure the Airflow user is the default
USER airflow
