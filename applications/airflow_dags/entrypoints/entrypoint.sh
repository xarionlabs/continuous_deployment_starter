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
    chown -R airflow:root /opt/airflow/dags
    chown -R airflow:root /opt/airflow/plugins
    chown -R airflow:root /opt/airflow/src
    chmod -R 755 /opt/airflow/dags
    chmod -R 755 /opt/airflow/plugins
    chmod -R 755 /opt/airflow/src
    
    echo 'DAGs and package files deployment completed successfully'
    ls -la /opt/airflow/dags/
    exit 0
fi

echo "Starting Airflow DAGs package..."

# Set PYTHONPATH to include dags directory
export PYTHONPATH="/app/dags:$PYTHONPATH"

# Basic DAG validation - check if they can be imported
python -c "
import sys
import os
sys.path.insert(0, '/app/dags')

try:
    # Import each DAG file to check for syntax errors
    from shopify_get_past_purchases_dag import dag as dag1
    from shopify_get_store_metadata_dag import dag as dag2
    print('✅ All DAGs imported successfully')
    print(f'  - {dag1.dag_id}')
    print(f'  - {dag2.dag_id}')
except Exception as e:
    print(f'❌ Error importing DAGs: {e}')
    sys.exit(1)
"

echo "DAG validation completed successfully!"