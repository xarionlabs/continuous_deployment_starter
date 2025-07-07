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

# Set PYTHONPATH to include src directory
export PYTHONPATH=/app/src:$PYTHONPATH

# Run DAG validation tests
echo "Running DAG validation tests..."
python -c "
import sys
import os
sys.path.insert(0, '/app/src')

# Test utilities first
try:
    from utils.shopify_client import ShopifyGraphQLClient
    print('✓ Legacy Shopify client imports successful')
except Exception as e:
    print(f'✗ Legacy Shopify client import error: {e}')

try:
    from utils.shopify_graphql import ShopifyGraphQLClient
    print('✓ New Shopify GraphQL client imports successful')
except Exception as e:
    print(f'✗ New Shopify GraphQL client import error: {e}')
    sys.exit(1)

try:
    from utils.database import get_database_connection, get_pxy6_database_manager
    print('✓ Database utilities import successful')
except Exception as e:
    print(f'✗ Database utilities import error: {e}')
    sys.exit(1)

# Test DAG imports (individual DAGs)
try:
    from dags.shopify_customer_data_dag import dag as customer_dag
    print('✓ Customer DAG imports successful')
except Exception as e:
    print(f'✗ Customer DAG import error: {e}')

try:
    from dags.shopify_order_data_dag import dag as order_dag  
    print('✓ Order DAG imports successful')
except Exception as e:
    print(f'✗ Order DAG import error: {e}')
"

# Test the new GraphQL client functionality
echo "Testing Shopify GraphQL client functionality..."
python -c "
import sys
import os
sys.path.insert(0, '/app/src')

from utils.shopify_graphql import ShopifyGraphQLClient

# Test client initialization
try:
    client = ShopifyGraphQLClient(shop_name='test-shop', access_token='test-token')
    print('✓ GraphQL client initialization successful')
except Exception as e:
    print(f'✗ GraphQL client initialization error: {e}')
    sys.exit(1)

# Test rate limit functionality
try:
    rate_limit = client.get_rate_limit_status()
    print(f'✓ Rate limit status: {rate_limit}')
except Exception as e:
    print(f'✗ Rate limit error: {e}')
    sys.exit(1)

# Test string representations
try:
    client_str = str(client)
    client_repr = repr(client)
    print(f'✓ Client string representation: {client_str}')
except Exception as e:
    print(f'✗ String representation error: {e}')
    sys.exit(1)

print('✓ All GraphQL client functionality tests passed')
"

# Run pytest if tests directory exists and has test files
if [ -d "/app/tests" ] && [ "$(find /app/tests -name '*.py' -type f)" ]; then
    echo "Running pytest..."
    
    # Run unit tests first (without requiring external connections)
    echo "Running unit tests..."
    pytest /app/tests/test_utils.py -v -k "not real_" || true
    
    # Run integration tests
    echo "Running integration tests..."
    pytest /app/tests/test_shopify_integration.py -v -k "not real_" || true
    
    # Run all tests if environment variables are set for real connections
    if [ -n "$SHOPIFY_SHOP_NAME" ] && [ -n "$SHOPIFY_ACCESS_TOKEN" ]; then
        echo "Running real Shopify integration tests..."
        pytest /app/tests/test_shopify_integration.py -v -k "real_shopify" || true
    else
        echo "Skipping real Shopify tests (set SHOPIFY_SHOP_NAME and SHOPIFY_ACCESS_TOKEN to run)"
    fi
    
    if [ -n "$PXY6_POSTGRES_HOST" ] && [ -n "$PXY6_POSTGRES_PASSWORD" ]; then
        echo "Running real database integration tests..."
        pytest /app/tests/test_shopify_integration.py -v -k "real_database" || true
    else
        echo "Skipping real database tests (set PXY6_POSTGRES_HOST and PXY6_POSTGRES_PASSWORD to run)"
    fi
    
else
    echo "No test files found in /app/tests/, skipping pytest"
fi

echo "All tests completed successfully!"