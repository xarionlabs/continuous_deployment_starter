#!/bin/bash
set -e

# Check if this is a deployment operation
if [ "$1" = "deploy" ]; then
    echo 'Deploying DAGs and package files to Airflow...'
    
    # Clear existing DAGs to prevent stale files
    rm -rf /opt/airflow/dags/*
    rm -rf /opt/airflow/plugins/*
    
    # Copy DAGs and package files needed for installation
    cp -r /app/dags/* /opt/airflow/dags/
    cp -r /app/src /opt/airflow/
    cp /app/requirements.txt /opt/airflow/
    cp /app/setup.py /opt/airflow/
    
    # Set proper permissions
    chown -R 50000:0 /opt/airflow/dags
    chown -R 50000:0 /opt/airflow/plugins
    chown -R 50000:0 /opt/airflow/src
    chmod -R 755 /opt/airflow/dags
    chmod -R 755 /opt/airflow/plugins
    chmod -R 755 /opt/airflow/src
    
    echo 'DAGs and package files deployment completed successfully'
    ls -la /opt/airflow/dags/
    exit 0
fi

echo "Starting Airflow DAGs package..."

# Activate virtual environment if it exists
if [ -d "/opt/venv" ]; then
    echo "Activating virtual environment..."
    source /opt/venv/bin/activate
    echo "Virtual environment activated: $(which python)"
    echo "Python version: $(python --version)"
    echo "Pip version: $(pip --version)"
else
    echo "No virtual environment found, using system Python"
fi

# Set PYTHONPATH to include src directory
export PYTHONPATH=/app/src:$PYTHONPATH

# Validate environment
echo "Validating environment..."
python -c "
import sys
import os
print(f'Python executable: {sys.executable}')
print(f'Python version: {sys.version}')
print(f'Python path: {sys.path[:3]}...')

# Test key dependencies
try:
    import gql
    print('✓ GQL (GraphQL client) available')
except ImportError:
    print('✗ GQL not available')

try:
    import asyncpg
    print('✓ AsyncPG (PostgreSQL driver) available')
except ImportError:
    print('✗ AsyncPG not available')

try:
    import airflow
    print(f'✓ Airflow available: {airflow.__version__}')
except ImportError:
    print('✗ Airflow not available')
"

# Validate DAGs by importing them
echo "Validating DAGs..."
python -c "
import sys
import os
sys.path.insert(0, '/app/src')

# Try to import all DAGs to validate syntax
try:
    from dags import *
    print('✓ All DAGs imported successfully')
except Exception as e:
    print(f'✗ Error importing DAGs: {e}')
    sys.exit(1)
"

echo "DAGs validation completed successfully"
echo "This package contains DAGs and utilities for Airflow deployment"
echo "Use this container to package and deploy DAGs to Airflow service"

# Keep container running in interactive mode
if [ "$1" = "--interactive" ]; then
    echo "Starting in interactive mode..."
    exec /bin/bash
fi

echo "Airflow DAGs package ready"