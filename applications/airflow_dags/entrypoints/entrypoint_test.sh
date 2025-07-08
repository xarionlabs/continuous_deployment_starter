#!/bin/bash
set -e

echo "Running tests for Airflow DAGs..."

# Activate virtual environment if it exists
if [ -d "/opt/venv" ]; then
    echo "Activating virtual environment..."
    source /opt/venv/bin/activate
    echo "Virtual environment activated: $(which python)"
else
    echo "No virtual environment found, using system Python"
fi

# Set PYTHONPATH to include src directory and current directory
export PYTHONPATH=/app/src:/app:$PYTHONPATH

# Ensure pxy6 module can be found (it's installed in editable mode)
cd /app

# Run pytest if tests directory exists
if [ -d "/app/tests" ]; then
    echo ""
    echo "Running pytest..."
    echo "================"
    
    # Run all tests
    pytest /app/tests/ -v --tb=short
    
    echo ""
    echo "All tests completed successfully"
    echo "================================"
else
    echo "No test directory found at /app/tests/"
    exit 1
fi

echo ""
echo "Test script completed!"