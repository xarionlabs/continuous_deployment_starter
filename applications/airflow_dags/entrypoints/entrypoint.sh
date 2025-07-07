#!/bin/bash
set -e

echo "Starting Airflow DAGs package..."

# Set PYTHONPATH to include src directory
export PYTHONPATH=/app/src:$PYTHONPATH

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