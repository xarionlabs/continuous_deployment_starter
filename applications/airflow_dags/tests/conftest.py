"""
Pytest configuration and fixtures for Airflow DAGs tests.

This module provides shared test configuration, fixtures, and utilities
for testing DAGs with real Shopify data.
"""

import pytest
import os
import sys
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Add the src directory to the Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent / 'src'
sys.path.insert(0, str(src_dir))


@pytest.fixture(scope="session")
def test_fixtures_dir():
    """Return the path to test fixtures directory."""
    return Path(__file__).parent / 'fixtures' / 'shopify_responses'


@pytest.fixture(scope="session")
def products_fixture(test_fixtures_dir):
    """Load products test fixture."""
    with open(test_fixtures_dir / 'products_response.json', 'r') as f:
        return json.load(f)


@pytest.fixture(scope="session")
def customers_fixture(test_fixtures_dir):
    """Load customers test fixture."""
    with open(test_fixtures_dir / 'customers_with_orders_response.json', 'r') as f:
        return json.load(f)


@pytest.fixture(scope="session")
def product_images_fixture(test_fixtures_dir):
    """Load product images test fixture."""
    with open(test_fixtures_dir / 'product_images_response.json', 'r') as f:
        return json.load(f)


@pytest.fixture
def mock_shopify_client():
    """Create a mock Shopify client for testing."""
    from src.utils.shopify_graphql import ShopifyGraphQLClient
    
    client = ShopifyGraphQLClient(
        shop_name="test-shop",
        access_token="test-token"
    )
    return client


@pytest.fixture
def mock_database_config():
    """Create a mock database configuration for testing."""
    from src.utils.database import DatabaseConfig
    
    return DatabaseConfig(
        host="test-db",
        port=5432,
        database="test_pxy6",
        user="test_pxy6_airflow",
        password="test_password"
    )


@pytest.fixture
def mock_database_manager(mock_database_config):
    """Create a mock database manager for testing."""
    from src.utils.database import DatabaseManager
    
    return DatabaseManager(mock_database_config)


@pytest.fixture
def mock_asyncpg_pool():
    """Create a mock asyncpg connection pool."""
    mock_pool = Mock()
    mock_connection = AsyncMock()
    mock_connection.execute.return_value = "INSERT 1"
    mock_connection.fetch.return_value = [{"test": 1}]
    mock_connection.fetchrow.return_value = {"test": 1}
    
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock()
    
    return mock_pool, mock_connection


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    # Set test environment variables
    test_env = {
        'SHOPIFY_SHOP_NAME': 'test-shop',
        'SHOPIFY_ACCESS_TOKEN': 'test-token',
        'PXY6_POSTGRES_HOST': 'test-db',
        'PXY6_POSTGRES_PORT': '5432',
        'PXY6_POSTGRES_DB': 'test_pxy6',
        'PXY6_POSTGRES_USER': 'test_pxy6_airflow',
        'PXY6_POSTGRES_PASSWORD': 'test_password'
    }
    
    # Store original values
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original values
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add integration marker to tests that use real API calls
        if "real_shopify" in item.name or "real_database" in item.name:
            item.add_marker(pytest.mark.integration)
        # Add unit marker to other tests
        else:
            item.add_marker(pytest.mark.unit)
        
        # Add slow marker to integration tests
        if hasattr(item, 'get_closest_marker') and item.get_closest_marker('integration'):
            item.add_marker(pytest.mark.slow)