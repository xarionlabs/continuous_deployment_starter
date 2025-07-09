#!/bin/bash
set -e

echo "🐳 Building and testing Airflow DAGs Docker image..."

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t airflow-dags-test .

# Run basic tests inside the container
echo "🧪 Running basic tests inside Docker container..."
docker run --rm airflow-dags-test ./entrypoints/entrypoint_test.sh

# Run tests with mock environment variables
echo "🧪 Running tests with mock environment variables..."
docker run --rm \
  -e SHOPIFY_SHOP_NAME="test-shop" \
  -e SHOPIFY_ACCESS_TOKEN="test-token" \
  -e PXY6_POSTGRES_HOST="test-db" \
  -e PXY6_POSTGRES_PASSWORD="test-password" \
  airflow-dags-test ./entrypoints/entrypoint_test.sh

# Run specific test suites
echo "🧪 Running specific test suites..."

# Run unit tests
echo "Running unit tests..."
docker run --rm airflow-dags-test pytest tests/ -v -k "not real_"

# Test the Shopify Hook module directly
echo "🧪 Testing Shopify Hook module..."
docker run --rm airflow-dags-test python -c "
import sys
sys.path.insert(0, '/app/src')
from hooks.shopify_hook import ShopifyHook

# Test initialization
hook = ShopifyHook(conn_id='shopify_default')
print('✓ Shopify Hook initialized successfully')

# Test that methods exist
assert hasattr(hook, 'get_conn'), 'Missing get_conn method'
assert hasattr(hook, 'execute_query'), 'Missing execute_query method'
print('✓ Shopify Hook methods validated successfully')
print('✓ All basic functionality tests passed')
"

# Test database module
echo "🧪 Testing database module..."
docker run --rm \
  -e PXY6_POSTGRES_HOST="test-db" \
  -e PXY6_POSTGRES_PASSWORD="test-password" \
  airflow-dags-test python -c "
import sys
sys.path.insert(0, '/app/src')
from utils.database import DatabaseConfig, get_pxy6_database_manager

# Test configuration
config = DatabaseConfig.from_environment()
print(f'✓ Database config: {config.host}:{config.port}/{config.database}')

# Test manager creation
manager = get_pxy6_database_manager()
print('✓ Database manager created successfully')
print('✓ All database tests passed')
"

echo "✅ All Docker tests completed successfully!"
echo ""
echo "📝 Usage examples:"
echo "  # Run all tests:"
echo "  ./test_docker.sh"
echo ""
echo "  # Run with real Shopify credentials:"
echo "  SHOPIFY_SHOP_NAME=your-shop SHOPIFY_ACCESS_TOKEN=your-token ./test_docker.sh"
echo ""
echo "  # Run specific test file:"
echo "  docker run --rm airflow-dags-test pytest tests/test_shopify_integration.py::TestShopifyGraphQLClient::test_client_initialization -v"
echo ""
echo "  # Run with real database connection:"
echo "  docker run --rm -e PXY6_POSTGRES_HOST=db -e PXY6_POSTGRES_PASSWORD=password airflow-dags-test pytest tests/test_shopify_integration.py -k real_database -v"