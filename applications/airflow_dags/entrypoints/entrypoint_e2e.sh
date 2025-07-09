#!/bin/bash
set -e

echo "Running e2e tests for Airflow DAGs..."

# Activate virtual environment if it exists
if [ -d "/opt/venv" ]; then
    echo "Activating virtual environment..."
    source /opt/venv/bin/activate
    echo "Virtual environment activated: $(which python)"
else
    echo "No virtual environment found, using system Python"
fi

# Set PYTHONPATH to include src directory
export PYTHONPATH=/app/src:$PYTHONPATH

# Test that all DAGs can be imported and parsed
echo "Testing DAG parsing and validation..."
python -c "
import sys
import os
sys.path.insert(0, '/app/src')

# Test DAG structure and syntax
try:
    from dags import *
    print('✓ All DAGs parsed successfully')
except Exception as e:
    print(f'✗ DAG parsing failed: {e}')
    sys.exit(1)

# Test that DAGs have required attributes
import importlib
import glob

dag_files = glob.glob('/app/src/dags/*.py')
dag_files = [f for f in dag_files if not f.endswith('__init__.py')]

for dag_file in dag_files:
    module_name = os.path.splitext(os.path.basename(dag_file))[0]
    try:
        spec = importlib.util.spec_from_file_location(module_name, dag_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Check for 'dag' attribute
        if hasattr(module, 'dag'):
            print(f'✓ {module_name} has dag attribute')
        else:
            print(f'✗ {module_name} missing dag attribute')
            sys.exit(1)
            
    except Exception as e:
        print(f'✗ Error loading {module_name}: {e}')
        sys.exit(1)

print('✓ All DAGs have required structure')
"

# Test basic connection capabilities (without actual connections)
echo "Testing connection utilities..."
python -c "
import sys
sys.path.insert(0, '/app/src')

# Test Shopify hook initialization (without actual API calls)
try:
    from hooks.shopify_hook import ShopifyHook
    # Test that we can create hook instance
    hook = ShopifyHook(conn_id='shopify_default')
    print('✓ Shopify hook can be instantiated')
except Exception as e:
    print(f'✗ Shopify hook error: {e}')
    sys.exit(1)

# Test database connection utilities
try:
    from utils.database import get_postgres_hook
    print('✓ Database utilities available')
except Exception as e:
    print(f'✗ Database utilities error: {e}')
    sys.exit(1)
"

echo "E2E tests completed successfully!"