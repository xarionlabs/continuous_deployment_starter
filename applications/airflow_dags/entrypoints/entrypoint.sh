#!/bin/bash
set -e

echo "Validating Airflow DAGs can be imported..."

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