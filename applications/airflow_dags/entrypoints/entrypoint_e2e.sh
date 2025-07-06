#!/bin/bash
set -e

echo "Running Airflow DAGs E2E validation..."

# Set PYTHONPATH to include dags directory
export PYTHONPATH="/app/dags:/app:$PYTHONPATH"

# Run DAG integrity tests
python -m pytest /app/tests/test_dag_integrity.py -v --tb=short --no-header

# Additional validation - check DAG structure
python -c "
import sys
sys.path.insert(0, '/app/dags')

from shopify_get_past_purchases_dag import dag as dag1
from shopify_get_store_metadata_dag import dag as dag2

print('=== DAG Validation Results ===')
for dag in [dag1, dag2]:
    print(f'DAG: {dag.dag_id}')
    print(f'  - Tasks: {len(dag.tasks)}')
    print(f'  - Schedule: {dag.schedule_interval}')
    print(f'  - Description: {dag.description or \"None\"}')
    print()
"

echo "E2E validation completed successfully!"