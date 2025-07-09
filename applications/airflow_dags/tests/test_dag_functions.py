"""
Simple tests for Shopify DAG functions.

This test suite validates the basic DAG functionality with the simplified architecture.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any

# Import the actual operators from current codebase
from pxy6.operators.shopify_operator import ShopifyToPostgresOperator
from pxy6.hooks.shopify_hook import ShopifyHook
from pxy6.utils.database import upsert_customer, upsert_product, upsert_order, execute_query


class TestShopifyToPostgresOperator:
    """Test the simplified ShopifyToPostgresOperator."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock Airflow context."""
        mock_dag_run = Mock()
        mock_dag_run.conf = {"shop_domain": "test-shop.myshopify.com"}
        return {
            "task_instance": Mock(),
            "ds": "2025-01-01",
            "execution_date": datetime(2025, 1, 1),
            "dag_run": mock_dag_run,
        }

    @pytest.fixture
    def sample_products_data(self):
        """Sample products data for testing."""
        return [
            {
                "id": "gid://shopify/Product/1",
                "title": "Test Product",
                "handle": "test-product",
                "vendor": "Test Vendor",
                "status": "ACTIVE",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-01-01T00:00:00Z",
            }
        ]

    @patch("pxy6.operators.shopify_operator.ShopifyHook")
    @patch("pxy6.operators.shopify_operator.upsert_product")
    def test_products_sync_operator(self, mock_upsert_product, mock_hook_class, mock_context, sample_products_data):
        """Test product sync operator execution."""
        # Setup mocks
        mock_hook = Mock()
        mock_hook.test_connection.return_value = True
        mock_hook.paginate_all_product_data.return_value = sample_products_data
        mock_hook_class.return_value = mock_hook

        # Create and execute operator
        operator = ShopifyToPostgresOperator(task_id="sync_products", data_type="products", batch_size=50)

        result = operator.execute(mock_context)

        # Assertions
        assert result["data_type"] == "products"
        assert result["extracted_count"] == 1
        assert result["loaded_count"] == 1
        assert result["error_count"] == 0
        assert result["success_rate"] == 1.0

        mock_hook.test_connection.assert_called_once()
        mock_upsert_product.assert_called_once_with(sample_products_data[0], "test-shop.myshopify.com")
        mock_hook.close.assert_called_once()

    @patch("pxy6.operators.shopify_operator.ShopifyHook")
    @patch("pxy6.operators.shopify_operator.upsert_customer")
    def test_customers_sync_operator(self, mock_upsert_customer, mock_hook_class, mock_context):
        """Test customer sync operator execution."""
        # Setup mocks
        mock_hook = Mock()
        mock_hook.test_connection.return_value = True
        sample_customers_data = [
            {"id": "gid://shopify/Customer/1", "email": "test@example.com", "firstName": "Test", "lastName": "User"}
        ]
        mock_hook.paginate_customers_with_orders.return_value = sample_customers_data
        mock_hook_class.return_value = mock_hook

        # Create and execute operator
        operator = ShopifyToPostgresOperator(task_id="sync_customers", data_type="customers", batch_size=25)

        result = operator.execute(mock_context)

        # Assertions
        assert result["data_type"] == "customers"
        assert result["extracted_count"] == 1
        assert result["loaded_count"] == 1
        assert result["error_count"] == 0

        mock_hook.test_connection.assert_called_once()
        mock_upsert_customer.assert_called_once_with(sample_customers_data[0], "test-shop.myshopify.com")

    def test_invalid_data_type_raises_error(self):
        """Test that invalid data type raises AirflowException."""
        from airflow.exceptions import AirflowException

        with pytest.raises(AirflowException, match="Invalid data_type"):
            ShopifyToPostgresOperator(task_id="invalid_sync", data_type="invalid_type")

    @patch("pxy6.operators.shopify_operator.ShopifyHook")
    def test_connection_failure_raises_error(self, mock_hook_class, mock_context):
        """Test that connection failure raises AirflowException."""
        from airflow.exceptions import AirflowException

        # Setup mocks
        mock_hook = Mock()
        mock_hook.test_connection.return_value = False
        mock_hook_class.return_value = mock_hook

        operator = ShopifyToPostgresOperator(task_id="sync_products", data_type="products")

        with pytest.raises(AirflowException, match="Failed to connect to Shopify API"):
            operator.execute(mock_context)
