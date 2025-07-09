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
project_root = current_dir.parent
src_dir = project_root / 'src'
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(project_root))

# Set Airflow environment for testing
os.environ.setdefault("AIRFLOW__CORE__LOAD_EXAMPLES", "False")
os.environ.setdefault("AIRFLOW__CORE__UNIT_TEST_MODE", "True")
os.environ.setdefault("AIRFLOW__CORE__EXECUTOR", "SequentialExecutor")

# Set up a test database path
import tempfile
test_db_path = tempfile.mktemp(suffix='.db')
os.environ.setdefault("AIRFLOW__DATABASE__SQL_ALCHEMY_CONN", f"sqlite:///{test_db_path}")
os.environ.setdefault("AIRFLOW_HOME", tempfile.mkdtemp())

# Initialize Airflow DB before any imports
try:
    from airflow.utils.db import initdb
    from airflow import settings
    # Ensure we're using the test database
    settings.configure_orm()
    initdb()
except Exception:
    # If initialization fails, it's okay for unit tests
    pass


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
    # Return a mock client since we removed the actual client
    from unittest.mock import Mock
    
    client = Mock()
    return client


@pytest.fixture
def mock_database_config():
    """Create a mock database configuration for testing."""
    return {
        "host": "test-db",
        "port": 5432,
        "database": "test_pxy6",
        "user": "test_pxy6_airflow",
        "password": "test_password"
    }


@pytest.fixture
def mock_database_manager():
    """Create a mock database manager for testing."""
    from pxy6.utils.database import DatabaseManager
    
    # Return a mock instance since we don't want to connect to a real database
    mock_manager = Mock(spec=DatabaseManager)
    mock_manager.connect = AsyncMock()
    mock_manager.close = AsyncMock()
    mock_manager.create_tables = AsyncMock()
    mock_manager.get_customers_count = AsyncMock(return_value=10)
    mock_manager.get_orders_count = AsyncMock(return_value=20)
    mock_manager.get_products_count = AsyncMock(return_value=30)
    mock_manager.upsert_customer = AsyncMock()
    mock_manager.upsert_order = AsyncMock()
    mock_manager.upsert_product = AsyncMock()
    mock_manager.execute_query = AsyncMock(return_value=[{"count": 5}])
    
    return mock_manager


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