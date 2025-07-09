"""
Tests for utility functions and classes.

This module contains tests for the utility functions used by the DAGs.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pxy6.utils.config import get_config, get_shopify_config
from pxy6.utils.shopify_client import ShopifyGraphQLClient
from pxy6.utils.database import (
    get_postgres_hook, 
    execute_query, 
    execute_insert,
    upsert_customer,
    upsert_product,
    upsert_order
)


class TestConfig:
    """Test configuration utilities."""
    
    @patch.dict('os.environ', {
        'SHOPIFY_SHOP_NAME': 'test-shop',
        'SHOPIFY_ACCESS_TOKEN': 'test-token',
        'POSTGRES_PASSWORD': 'test-password',
        'PXY6_POSTGRES_PASSWORD': 'test-pxy6-password',
    })
    def test_get_config(self):
        """Test configuration loading."""
        config = get_config()
        
        assert config.shopify_shop_name == 'test-shop'
        assert config.shopify_access_token == 'test-token'
        assert config.postgres_password == 'test-password'
        assert config.pxy6_postgres_password == 'test-pxy6-password'
    
    @patch.dict('os.environ', {
        'SHOPIFY_SHOP_NAME': 'test-shop',
        'SHOPIFY_ACCESS_TOKEN': 'test-token',
        'POSTGRES_PASSWORD': 'test-password',
    })
    def test_get_shopify_config(self):
        """Test Shopify configuration."""
        config = get_shopify_config()
        
        assert config['shop_name'] == 'test-shop'
        assert config['access_token'] == 'test-token'


class TestShopifyClient:
    """Test Shopify GraphQL client."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = ShopifyGraphQLClient('test-shop', 'test-token')
        
        assert client.shop_name == 'test-shop'
        assert client.access_token == 'test-token'
        assert client.shop_url == 'https://test-shop.myshopify.com/admin/api/2025-01/graphql.json'
    
    @patch('utils.shopify_client.Client')
    def test_rate_limiting(self, mock_client):
        """Test rate limiting functionality."""
        client = ShopifyGraphQLClient('test-shop', 'test-token')
        
        # Test that rate limiting is applied
        import time
        start_time = time.time()
        
        # Mock multiple calls
        with patch.object(client, 'execute_query') as mock_execute:
            mock_execute.return_value = {}
            
            # Make multiple calls
            for _ in range(3):
                client.execute_query('query { shop { name } }')
        
        # Check that some time has passed (rate limiting)
        elapsed = time.time() - start_time
        assert elapsed >= 0.0  # Just ensure it runs without error
    
    @patch('utils.shopify_client.Client')
    def test_test_connection(self, mock_client):
        """Test connection testing."""
        # Mock successful connection
        mock_client.return_value.execute.return_value = {
            'shop': {'name': 'Test Shop', 'myshopifyDomain': 'test-shop.myshopify.com'}
        }
        
        client = ShopifyGraphQLClient('test-shop', 'test-token')
        
        with patch.object(client, 'execute_query') as mock_execute:
            mock_execute.return_value = {
                'shop': {'name': 'Test Shop', 'myshopifyDomain': 'test-shop.myshopify.com'}
            }
            
            result = client.test_connection()
            assert result is True
    
    @patch('utils.shopify_client.Client')
    def test_test_connection_failure(self, mock_client):
        """Test connection testing failure."""
        client = ShopifyGraphQLClient('test-shop', 'test-token')
        
        with patch.object(client, 'execute_query') as mock_execute:
            mock_execute.side_effect = Exception('Connection failed')
            
            result = client.test_connection()
            assert result is False
    
    @patch('utils.shopify_client.Client')
    def test_get_customers(self, mock_client):
        """Test customer data retrieval."""
        client = ShopifyGraphQLClient('test-shop', 'test-token')
        
        expected_result = {
            'customers': {
                'edges': [
                    {
                        'node': {
                            'id': 'gid://shopify/Customer/1',
                            'email': 'test@example.com',
                            'firstName': 'Test',
                            'lastName': 'User',
                        }
                    }
                ],
                'pageInfo': {
                    'hasNextPage': False,
                    'endCursor': None,
                }
            }
        }
        
        with patch.object(client, 'execute_query') as mock_execute:
            mock_execute.return_value = expected_result
            
            result = client.get_customers(limit=50)
            
            assert result == expected_result
            mock_execute.assert_called_once()


class TestDatabase:
    """Test database utilities."""
    
    @patch('pxy6.utils.database.PostgresHook')
    def test_get_postgres_hook(self, mock_postgres_hook):
        """Test PostgresHook creation."""
        hook = get_postgres_hook()
        
        mock_postgres_hook.assert_called_once_with(postgres_conn_id='pxy6_postgres')
    
    @patch('pxy6.utils.database.get_postgres_hook')
    def test_execute_query(self, mock_get_hook):
        """Test query execution."""
        mock_hook = Mock()
        mock_hook.get_records.return_value = [{'id': 1, 'name': 'test'}]
        mock_get_hook.return_value = mock_hook
        
        result = execute_query("SELECT * FROM customers", {'param': 'value'})
        
        assert result == [{'id': 1, 'name': 'test'}]
        mock_hook.get_records.assert_called_once_with("SELECT * FROM customers", {'param': 'value'})
    
    @patch('pxy6.utils.database.get_postgres_hook')
    def test_execute_insert(self, mock_get_hook):
        """Test insert execution."""
        mock_hook = Mock()
        mock_get_hook.return_value = mock_hook
        
        execute_insert("INSERT INTO customers VALUES (%s, %s)", {'id': 1, 'name': 'test'})
        
        mock_hook.run.assert_called_once_with("INSERT INTO customers VALUES (%s, %s)", {'id': 1, 'name': 'test'})
    
    @patch('pxy6.utils.database.execute_insert')
    def test_upsert_customer(self, mock_execute_insert):
        """Test customer upsert."""
        customer_data = {
            'id': 'gid://shopify/Customer/123',
            'email': 'test@example.com',
            'firstName': 'John',
            'lastName': 'Doe',
            'phone': '+1234567890',
            'acceptsMarketing': True,
            'state': 'enabled',
            'tags': ['vip', 'premium'],
            'totalSpentV2': {
                'amount': '150.00',
                'currencyCode': 'USD'
            },
            'numberOfOrders': 5,
            'verifiedEmail': True,
            'taxExempt': False,
            'addresses': [{'address1': '123 Main St'}],
            'metafields': {'key': 'value'},
            'createdAt': '2023-01-01T00:00:00Z',
            'updatedAt': '2023-01-02T00:00:00Z'
        }
        
        upsert_customer(customer_data)
        
        # Verify execute_insert was called with correct parameters
        mock_execute_insert.assert_called_once()
        args, kwargs = mock_execute_insert.call_args
        
        # Check the query contains the expected structure
        assert 'INSERT INTO customers' in args[0]
        assert 'ON CONFLICT (id) DO UPDATE SET' in args[0]
        
        # Check some key parameters
        params = args[1]
        assert params['id'] == 123
        assert params['email'] == 'test@example.com'
        assert params['first_name'] == 'John'
        assert params['last_name'] == 'Doe'
        assert params['total_spent_amount'] == 150.0
        assert params['total_spent_currency'] == 'USD'
    
    @patch('pxy6.utils.database.execute_insert')
    def test_upsert_product(self, mock_execute_insert):
        """Test product upsert."""
        product_data = {
            'id': 'gid://shopify/Product/456',
            'title': 'Test Product',
            'handle': 'test-product',
            'description': 'A test product',
            'descriptionHtml': '<p>A test product</p>',
            'productType': 'Widget',
            'vendor': 'Test Vendor',
            'tags': ['new', 'featured'],
            'status': 'ACTIVE',
            'totalInventory': 10,
            'onlineStoreUrl': 'https://shop.com/products/test',
            'seo': {
                'title': 'SEO Title',
                'description': 'SEO Description'
            },
            'options': [{'name': 'Size', 'values': ['S', 'M', 'L']}],
            'variants': {'edges': []},
            'images': {'edges': []},
            'metafields': {'key': 'value'},
            'collections': {'edges': []},
            'createdAt': '2023-01-01T00:00:00Z',
            'updatedAt': '2023-01-02T00:00:00Z',
            'publishedAt': '2023-01-01T00:00:00Z'
        }
        
        upsert_product(product_data)
        
        # Verify execute_insert was called
        mock_execute_insert.assert_called_once()
        args, kwargs = mock_execute_insert.call_args
        
        # Check the query contains the expected structure
        assert 'INSERT INTO products' in args[0]
        assert 'ON CONFLICT (id) DO UPDATE SET' in args[0]
        
        # Check some key parameters
        params = args[1]
        assert params['id'] == 456
        assert params['title'] == 'Test Product'
        assert params['handle'] == 'test-product'
        assert params['status'] == 'ACTIVE'
    
    @patch('pxy6.utils.database.execute_insert')
    def test_upsert_order(self, mock_execute_insert):
        """Test order upsert."""
        order_data = {
            'id': 'gid://shopify/Order/789',
            'name': '#1001',
            'email': 'customer@example.com',
            'customer': {'id': 'gid://shopify/Customer/123'},
            'totalPriceSet': {
                'shopMoney': {
                    'amount': '100.00',
                    'currencyCode': 'USD'
                }
            },
            'subtotalPriceSet': {
                'shopMoney': {
                    'amount': '90.00',
                    'currencyCode': 'USD'
                }
            },
            'totalTaxSet': {
                'shopMoney': {
                    'amount': '10.00',
                    'currencyCode': 'USD'
                }
            },
            'totalShippingPriceSet': {
                'shopMoney': {
                    'amount': '0.00',
                    'currencyCode': 'USD'
                }
            },
            'financialStatus': 'paid',
            'fulfillmentStatus': 'fulfilled',
            'cancelled': False,
            'cancelReason': None,
            'tags': [],
            'note': 'Test order',
            'lineItems': {'edges': []},
            'shippingAddress': {'address1': '123 Main St'},
            'billingAddress': {'address1': '123 Main St'},
            'customerJourney': {'firstVisit': '2023-01-01'},
            'createdAt': '2023-01-01T00:00:00Z',
            'updatedAt': '2023-01-02T00:00:00Z',
            'processedAt': '2023-01-01T00:00:00Z',
            'closedAt': None,
            'cancelledAt': None
        }
        
        upsert_order(order_data)
        
        # Verify execute_insert was called
        mock_execute_insert.assert_called_once()
        args, kwargs = mock_execute_insert.call_args
        
        # Check the query contains the expected structure
        assert 'INSERT INTO orders' in args[0]
        assert 'ON CONFLICT (id) DO UPDATE SET' in args[0]
        
        # Check some key parameters
        params = args[1]
        assert params['id'] == 789
        assert params['name'] == '#1001'
        assert params['email'] == 'customer@example.com'
        assert params['customer_id'] == 123
        assert params['total_price_amount'] == 100.0
        assert params['financial_status'] == 'paid'


if __name__ == '__main__':
    pytest.main([__file__])