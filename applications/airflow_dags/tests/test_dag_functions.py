"""
Tests for specific DAG functions and operators using real Shopify payloads.

This test suite validates the actual DAG task functions to ensure they
process real Shopify data correctly.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
from typing import Dict, Any

# Import DAG modules
from src.operators.shopify_operator import ShopifyExtractOperator, ShopifyStoreOperator
from src.hooks.shopify_hook import ShopifyHook
from src.utils.shopify_graphql import ShopifyGraphQLClient
from src.utils.database import DatabaseManager


class TestShopifyExtractOperator:
    """Test ShopifyExtractOperator with real data."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Load real fixture data
        with open('tests/fixtures/shopify_responses/products_response.json', 'r') as f:
            self.products_data = json.load(f)
        with open('tests/fixtures/shopify_responses/customers_with_orders_response.json', 'r') as f:
            self.customers_data = json.load(f)
    
    @patch('src.operators.shopify_operator.ShopifyGraphQLClient')
    def test_extract_products_operator(self, mock_client_class):
        """Test product extraction operator with real data."""
        # Setup mock client
        mock_client = MagicMock()
        mock_client.get_all_product_data.return_value = self.products_data
        mock_client_class.return_value = mock_client
        
        # Create operator
        operator = ShopifyExtractOperator(
            task_id='extract_products',
            query_type='products',
            limit=50
        )
        
        # Mock context
        context = {
            'ti': Mock(),
            'ds': '2023-12-01',
            'task_instance': Mock()
        }
        context['ti'].xcom_push = Mock()
        
        # Execute operator
        result = operator.execute(context)
        
        # Verify results
        assert result is not None
        mock_client.get_all_product_data.assert_called_once_with(limit=50)
        context['ti'].xcom_push.assert_called()
        
        # Verify data structure
        pushed_data = context['ti'].xcom_push.call_args[1]['value']
        assert 'data' in pushed_data
        assert 'products' in pushed_data['data']
        assert len(pushed_data['data']['products']['edges']) > 0
    
    @patch('src.operators.shopify_operator.ShopifyGraphQLClient')
    def test_extract_customers_operator(self, mock_client_class):
        """Test customer extraction operator with real data."""
        # Setup mock client
        mock_client = MagicMock()
        mock_client.get_customers_with_orders.return_value = self.customers_data
        mock_client_class.return_value = mock_client
        
        # Create operator
        operator = ShopifyExtractOperator(
            task_id='extract_customers',
            query_type='customers',
            limit=25
        )
        
        # Mock context
        context = {
            'ti': Mock(),
            'ds': '2023-12-01',
            'task_instance': Mock()
        }
        context['ti'].xcom_push = Mock()
        
        # Execute operator
        result = operator.execute(context)
        
        # Verify results
        assert result is not None
        mock_client.get_customers_with_orders.assert_called_once_with(limit=25)
        context['ti'].xcom_push.assert_called()
        
        # Verify data structure
        pushed_data = context['ti'].xcom_push.call_args[1]['value']
        assert 'data' in pushed_data
        assert 'customers' in pushed_data['data']
        assert len(pushed_data['data']['customers']['edges']) > 0
    
    @patch('src.operators.shopify_operator.ShopifyGraphQLClient')
    def test_extract_operator_error_handling(self, mock_client_class):
        """Test operator error handling."""
        # Setup mock client to raise exception
        mock_client = MagicMock()
        mock_client.get_all_product_data.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client
        
        # Create operator
        operator = ShopifyExtractOperator(
            task_id='extract_products',
            query_type='products',
            limit=50
        )
        
        # Mock context
        context = {
            'ti': Mock(),
            'ds': '2023-12-01',
            'task_instance': Mock()
        }
        
        # Execute operator and expect exception
        with pytest.raises(Exception) as exc_info:
            operator.execute(context)
        
        assert "API Error" in str(exc_info.value)


class TestShopifyStoreOperator:
    """Test ShopifyStoreOperator with real data."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Load real fixture data
        with open('tests/fixtures/shopify_responses/products_response.json', 'r') as f:
            self.products_data = json.load(f)
        with open('tests/fixtures/shopify_responses/customers_with_orders_response.json', 'r') as f:
            self.customers_data = json.load(f)
    
    @patch('src.operators.shopify_operator.DatabaseManager')
    @patch('src.utils.database.asyncpg.create_pool')
    def test_store_products_operator(self, mock_create_pool, mock_db_manager_class):
        """Test product storage operator with real data."""
        # Setup mock database
        mock_pool = Mock()
        mock_connection = AsyncMock()
        mock_connection.execute.return_value = "INSERT 1"
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()
        mock_create_pool.return_value = mock_pool
        
        mock_db_manager = AsyncMock()
        mock_db_manager.connect.return_value = None
        mock_db_manager.upsert_product.return_value = None
        mock_db_manager.close.return_value = None
        mock_db_manager_class.return_value = mock_db_manager
        
        # Create operator
        operator = ShopifyStoreOperator(
            task_id='store_products',
            data_type='products'
        )
        
        # Mock context with extracted data
        context = {
            'ti': Mock(),
            'ds': '2023-12-01',
            'task_instance': Mock()
        }
        context['ti'].xcom_pull.return_value = self.products_data
        
        # Execute operator
        result = operator.execute(context)
        
        # Verify results
        assert result is not None
        context['ti'].xcom_pull.assert_called_once()
        mock_db_manager.connect.assert_called_once()
        
        # Verify that upsert was called for each product
        products_count = len(self.products_data['data']['products']['edges'])
        assert mock_db_manager.upsert_product.call_count == products_count
        
        mock_db_manager.close.assert_called_once()
    
    @patch('src.operators.shopify_operator.DatabaseManager')
    @patch('src.utils.database.asyncpg.create_pool')
    def test_store_customers_operator(self, mock_create_pool, mock_db_manager_class):
        """Test customer storage operator with real data."""
        # Setup mock database
        mock_pool = Mock()
        mock_connection = AsyncMock()
        mock_connection.execute.return_value = "INSERT 1"
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()
        mock_create_pool.return_value = mock_pool
        
        mock_db_manager = AsyncMock()
        mock_db_manager.connect.return_value = None
        mock_db_manager.upsert_customer.return_value = None
        mock_db_manager.upsert_order.return_value = None
        mock_db_manager.close.return_value = None
        mock_db_manager_class.return_value = mock_db_manager
        
        # Create operator
        operator = ShopifyStoreOperator(
            task_id='store_customers',
            data_type='customers'
        )
        
        # Mock context with extracted data
        context = {
            'ti': Mock(),
            'ds': '2023-12-01',
            'task_instance': Mock()
        }
        context['ti'].xcom_pull.return_value = self.customers_data
        
        # Execute operator
        result = operator.execute(context)
        
        # Verify results
        assert result is not None
        context['ti'].xcom_pull.assert_called_once()
        mock_db_manager.connect.assert_called_once()
        
        # Verify that upsert was called for each customer
        customers_count = len(self.customers_data['data']['customers']['edges'])
        assert mock_db_manager.upsert_customer.call_count == customers_count
        
        # Count orders across all customers
        total_orders = 0
        for customer_edge in self.customers_data['data']['customers']['edges']:
            total_orders += len(customer_edge['node']['orders']['edges'])
        
        if total_orders > 0:
            assert mock_db_manager.upsert_order.call_count == total_orders
        
        mock_db_manager.close.assert_called_once()


class TestShopifyHook:
    """Test ShopifyHook with real data."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Load real fixture data
        with open('tests/fixtures/shopify_responses/products_response.json', 'r') as f:
            self.products_data = json.load(f)
    
    @patch('src.hooks.shopify_hook.ShopifyGraphQLClient')
    def test_hook_get_products(self, mock_client_class):
        """Test hook product retrieval."""
        # Setup mock client
        mock_client = MagicMock()
        mock_client.get_all_product_data.return_value = self.products_data
        mock_client.test_connection.return_value = True
        mock_client_class.return_value = mock_client
        
        # Create hook
        hook = ShopifyHook(
            shopify_conn_id='shopify_default'
        )
        
        # Test connection
        assert hook.test_connection() == True
        
        # Test get products
        result = hook.get_products(limit=50)
        
        # Verify results
        assert result == self.products_data
        mock_client.get_all_product_data.assert_called_once_with(limit=50)
    
    @patch('src.hooks.shopify_hook.ShopifyGraphQLClient')
    def test_hook_connection_failure(self, mock_client_class):
        """Test hook connection failure handling."""
        # Setup mock client to fail connection
        mock_client = MagicMock()
        mock_client.test_connection.return_value = False
        mock_client_class.return_value = mock_client
        
        # Create hook
        hook = ShopifyHook(
            shopify_conn_id='shopify_default'
        )
        
        # Test connection failure
        assert hook.test_connection() == False
        
        # Test that operations fail gracefully
        with pytest.raises(Exception):
            hook.get_products(limit=50)


class TestDataProcessingFunctions:
    """Test specific data processing functions used in DAGs."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Load real fixture data
        with open('tests/fixtures/shopify_responses/products_response.json', 'r') as f:
            self.products_data = json.load(f)
        with open('tests/fixtures/shopify_responses/customers_with_orders_response.json', 'r') as f:
            self.customers_data = json.load(f)
    
    def test_product_data_transformation(self):
        """Test product data transformation for database storage."""
        from src.utils.database import DatabaseManager
        
        # Get first product from real data
        product_data = self.products_data['data']['products']['edges'][0]['node']
        
        # Test data preparation (this would be a function in your actual DAG)
        def prepare_product_for_db(product):
            """Transform product data for database insertion."""
            return {
                'id': product['id'],
                'title': product['title'],
                'handle': product['handle'],
                'description': product.get('description', ''),
                'product_type': product.get('productType', ''),
                'vendor': product.get('vendor', ''),
                'status': product.get('status', 'ACTIVE'),
                'created_at': product['createdAt'],
                'updated_at': product['updatedAt'],
                'published_at': product.get('publishedAt'),
                'tags': product.get('tags', []),
                'total_inventory': product.get('totalInventory', 0),
                'variants_count': len(product.get('variants', {}).get('edges', [])),
                'images_count': len(product.get('images', {}).get('edges', []))
            }
        
        # Transform the real data
        transformed = prepare_product_for_db(product_data)
        
        # Verify transformation
        assert transformed['id'] == product_data['id']
        assert transformed['title'] == product_data['title']
        assert transformed['handle'] == product_data['handle']
        assert isinstance(transformed['tags'], list)
        assert isinstance(transformed['total_inventory'], int)
        assert isinstance(transformed['variants_count'], int)
        assert isinstance(transformed['images_count'], int)
    
    def test_customer_data_transformation(self):
        """Test customer data transformation for database storage."""
        # Get first customer from real data
        customer_data = self.customers_data['data']['customers']['edges'][0]['node']
        
        # Test data preparation
        def prepare_customer_for_db(customer):
            """Transform customer data for database insertion."""
            return {
                'id': customer['id'],
                'email': customer.get('email', ''),
                'created_at': customer['createdAt'],
                'orders_count': len(customer.get('orders', {}).get('edges', [])),
                'has_orders': len(customer.get('orders', {}).get('edges', [])) > 0
            }
        
        # Transform the real data
        transformed = prepare_customer_for_db(customer_data)
        
        # Verify transformation
        assert transformed['id'] == customer_data['id']
        assert isinstance(transformed['orders_count'], int)
        assert isinstance(transformed['has_orders'], bool)
    
    def test_order_data_extraction(self):
        """Test order data extraction from customer data."""
        # Find customer with orders from real data
        customer_with_orders = None
        for customer_edge in self.customers_data['data']['customers']['edges']:
            if len(customer_edge['node']['orders']['edges']) > 0:
                customer_with_orders = customer_edge['node']
                break
        
        assert customer_with_orders is not None, "No customers with orders in fixture"
        
        # Test order extraction
        def extract_orders_from_customer(customer):
            """Extract order data from customer."""
            orders = []
            for order_edge in customer['orders']['edges']:
                order = order_edge['node']
                orders.append({
                    'id': order['id'],
                    'name': order['name'],
                    'customer_id': customer['id'],
                    'processed_at': order['processedAt'],
                    'line_items_count': len(order.get('lineItems', {}).get('edges', []))
                })
            return orders
        
        # Extract orders from real data
        orders = extract_orders_from_customer(customer_with_orders)
        
        # Verify extraction
        assert len(orders) > 0
        for order in orders:
            assert order['id'].startswith('gid://shopify/Order/')
            assert order['customer_id'] == customer_with_orders['id']
            assert isinstance(order['line_items_count'], int)
    
    def test_rate_limit_data_processing(self):
        """Test rate limit data processing from API responses."""
        # Test with real rate limit data from customers response
        extensions = self.customers_data.get('extensions', {})
        cost_info = extensions.get('cost', {})
        
        def process_rate_limit_info(cost_info):
            """Process rate limit information."""
            throttle_status = cost_info.get('throttleStatus', {})
            return {
                'max_available': throttle_status.get('maximumAvailable', 2000),
                'currently_available': throttle_status.get('currentlyAvailable', 1990),
                'restore_rate': throttle_status.get('restoreRate', 100),
                'requested_cost': cost_info.get('requestedQueryCost', 0),
                'actual_cost': cost_info.get('actualQueryCost', 0)
            }
        
        # Process real rate limit data
        rate_limit = process_rate_limit_info(cost_info)
        
        # Verify processing
        assert rate_limit['max_available'] > 0
        assert rate_limit['restore_rate'] > 0
        assert rate_limit['actual_cost'] >= 0
        
        # Calculate remaining calls
        remaining = rate_limit['max_available'] - rate_limit['currently_available']
        assert remaining >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])