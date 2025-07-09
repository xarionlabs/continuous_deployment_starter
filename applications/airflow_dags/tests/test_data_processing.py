"""
Simple tests for database operations.

This test suite validates the basic database functions with the simplified architecture.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

# Import the database functions
from pxy6.utils.database import (
    upsert_customer,
    upsert_product,
    upsert_order,
    execute_query,
    execute_insert,
    get_postgres_hook,
)


class TestDatabaseFunctions:
    """Test the simplified database functions."""

    @pytest.fixture
    def sample_customer_data(self):
        """Sample customer data for testing."""
        return {
            "id": "gid://shopify/Customer/123",
            "email": "test@example.com",
            "firstName": "Test",
            "lastName": "User",
            "phone": "+1234567890",
            "acceptsMarketing": True,
            "state": "ENABLED",
            "totalSpentV2": {"amount": "100.00", "currencyCode": "USD"},
            "numberOfOrders": 5,
            "verifiedEmail": True,
            "taxExempt": False,
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-01T00:00:00Z",
        }

    @pytest.fixture
    def sample_product_data(self):
        """Sample product data for testing."""
        return {
            "id": "gid://shopify/Product/456",
            "title": "Test Product",
            "handle": "test-product",
            "description": "A test product",
            "descriptionHtml": "<p>A test product</p>",
            "productType": "Test Type",
            "vendor": "Test Vendor",
            "tags": ["test", "product"],
            "status": "ACTIVE",
            "totalInventory": 100,
            "onlineStoreUrl": "https://example.com/products/test-product",
            "seo": {"title": "Test Product SEO", "description": "Test product for SEO"},
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-01T00:00:00Z",
            "publishedAt": "2025-01-01T00:00:00Z",
        }

    @patch("pxy6.utils.database.get_postgres_hook")
    def test_execute_query(self, mock_get_hook):
        """Test execute_query function."""
        mock_hook = Mock()
        mock_hook.get_records.return_value = [{"count": 5}]
        mock_get_hook.return_value = mock_hook

        result = execute_query("SELECT COUNT(*) as count FROM customers")

        assert result == [{"count": 5}]
        mock_hook.get_records.assert_called_once()

    @patch("pxy6.utils.database.get_postgres_hook")
    def test_execute_insert(self, mock_get_hook):
        """Test execute_insert function."""
        mock_hook = Mock()
        mock_get_hook.return_value = mock_hook

        execute_insert("INSERT INTO customers (name) VALUES (%(name)s)", {"name": "Test"})

        mock_hook.run.assert_called_once_with(
            "INSERT INTO customers (name) VALUES (%(name)s)", parameters={"name": "Test"}
        )

    @patch("pxy6.utils.database.execute_insert")
    def test_upsert_customer(self, mock_execute_insert, sample_customer_data):
        """Test upsert_customer function."""
        upsert_customer(sample_customer_data, "test-shop.myshopify.com")

        # Verify the function was called
        mock_execute_insert.assert_called_once()

        # Verify the SQL and parameters structure
        args, kwargs = mock_execute_insert.call_args
        query = args[0]
        params = args[1]

        assert "INSERT INTO customers" in query
        assert "ON CONFLICT (id) DO UPDATE SET" in query
        assert params[0] == "gid://shopify/Customer/123"  # Full GID is stored
        assert params[2] == "test@example.com"  # email is 3rd parameter
        assert params[3] == "Test"  # firstName is 4th parameter
        assert params[4] == "User"  # lastName is 5th parameter

    @patch("pxy6.utils.database.execute_insert")
    def test_upsert_product(self, mock_execute_insert, sample_product_data):
        """Test upsert_product function."""
        upsert_product(sample_product_data, "test-shop.myshopify.com")

        # Verify the function was called
        mock_execute_insert.assert_called_once()

        # Verify the SQL and parameters structure
        args, kwargs = mock_execute_insert.call_args
        query = args[0]
        params = args[1]

        assert "INSERT INTO products" in query
        assert "ON CONFLICT (id) DO UPDATE SET" in query
        assert params[0] == "gid://shopify/Product/456"  # Full GID is stored
        assert params[2] == "Test Product"  # title is 3rd parameter
        assert params[3] == "test-product"  # handle is 4th parameter
        assert params[7] == "Test Vendor"  # vendor is 8th parameter

    @patch("pxy6.utils.database.execute_insert")
    def test_upsert_order(self, mock_execute_insert):
        """Test upsert_order function."""
        sample_order_data = {
            "id": "gid://shopify/Order/789",
            "name": "#1001",
            "email": "customer@example.com",
            "customer": {"id": "gid://shopify/Customer/123"},
            "totalPriceSet": {"shopMoney": {"amount": "50.00", "currencyCode": "USD"}},
            "financialStatus": "PAID",
            "fulfillmentStatus": "FULFILLED",
            "cancelled": False,
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-01T00:00:00Z",
        }

        upsert_order(sample_order_data, "test-shop.myshopify.com")

        # Verify the function was called
        mock_execute_insert.assert_called_once()

        # Verify the SQL and parameters structure
        args, kwargs = mock_execute_insert.call_args
        query = args[0]
        params = args[1]

        assert "INSERT INTO orders" in query
        assert "ON CONFLICT (id) DO UPDATE SET" in query
        assert params[0] == "gid://shopify/Order/789"  # Full GID is stored
        assert params[2] == "gid://shopify/Customer/123"  # customer_id is 3rd parameter
        assert params[4] == "#1001"  # name is 5th parameter
        assert params[5] == "customer@example.com"  # email is 6th parameter

    @patch("pxy6.utils.database.PostgresHook")
    def test_get_postgres_hook(self, mock_postgres_hook):
        """Test get_postgres_hook function."""
        mock_hook_instance = Mock()
        mock_postgres_hook.return_value = mock_hook_instance

        result = get_postgres_hook()

        assert result == mock_hook_instance
        mock_postgres_hook.assert_called_once_with(postgres_conn_id="pxy6_postgres")

    @patch("pxy6.utils.database.execute_insert")
    def test_upsert_customer_with_missing_fields(self, mock_execute_insert):
        """Test upsert_customer with minimal data."""
        minimal_customer_data = {"id": "gid://shopify/Customer/999", "email": "minimal@example.com"}

        upsert_customer(minimal_customer_data, "test-shop.myshopify.com")

        # Verify the function was called
        mock_execute_insert.assert_called_once()

        # Verify the parameters handle missing fields gracefully
        args, kwargs = mock_execute_insert.call_args
        params = args[1]

        assert params[0] == "gid://shopify/Customer/999"  # Full GID is stored
        assert params[2] == "minimal@example.com"  # email is 3rd parameter
        assert params[3] is None  # firstName is 4th parameter
        assert params[4] is None  # lastName is 5th parameter
        assert params[11] == 0  # totalSpent is 12th parameter
