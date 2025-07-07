#!/bin/bash
set -e

echo "Running Airflow DAGs test suite..."

# Set PYTHONPATH to include dags directory
export PYTHONPATH="/app/dags:/app:$PYTHONPATH"

# Run pytest with coverage
python -m pytest /app/tests/ -v --tb=short --no-header

echo "All tests passed!"