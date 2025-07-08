"""
Tests for utility functions and classes.

This module contains tests for the utility functions used by the DAGs.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pxy6.utils.config import get_config, get_shopify_config, get_database_config
from pxy6.utils.shopify_client import ShopifyGraphQLClient
from pxy6.utils.database import DatabaseManager, get_database_connection


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
    })
    def test_get_shopify_config(self):
        """Test Shopify configuration."""
        config = get_shopify_config()
        
        assert config['shop_name'] == 'test-shop'
        assert config['access_token'] == 'test-token'
    
    @patch.dict('os.environ', {
        'POSTGRES_USER': 'test-user',
        'POSTGRES_PASSWORD': 'test-password',
        'POSTGRES_HOST': 'test-host',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DB': 'test-db',
    })
    def test_get_database_config(self):
        """Test database configuration."""
        config = get_database_config()
        
        assert config['user'] == 'test-user'
        assert config['password'] == 'test-password'
        assert config['host'] == 'test-host'
        assert config['port'] == 5432
        assert config['database'] == 'test-db'


class TestShopifyClient:
    """Test Shopify GraphQL client."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = ShopifyGraphQLClient('test-shop', 'test-token')
        
        assert client.shop_name == 'test-shop'
        assert client.access_token == 'test-token'
        assert client.shop_url == 'https://test-shop.myshopify.com/admin/api/2023-10/graphql.json'
    
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
        assert elapsed >= 1.0  # Should take at least 1 second for 3 calls at 2 calls/second
    
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
    
    @patch('utils.database.DatabaseConfig.from_environment')
    def test_database_manager_initialization(self, mock_config):
        """Test DatabaseManager initialization."""
        mock_config.return_value = Mock(
            host='test-host',
            port=5432,
            database='test-db',
            user='test-user',
            password='test-password'
        )
        
        db_manager = DatabaseManager()
        assert db_manager.config.host == 'test-host'
        assert db_manager.config.database == 'test-db'
    
    @patch('utils.database.asyncpg.create_pool')
    async def test_database_connection_success(self, mock_create_pool):
        """Test successful database connection."""
        mock_pool = Mock()
        mock_create_pool.return_value = mock_pool
        
        db_manager = DatabaseManager()
        await db_manager.connect()
        
        assert db_manager.pool == mock_pool
        mock_create_pool.assert_called_once()
    
    async def test_database_test_connection_success(self):
        """Test successful database connection test."""
        db_manager = DatabaseManager()
        
        with patch.object(db_manager, 'execute_query') as mock_execute:
            mock_execute.return_value = [{'test': 1}]
            
            result = await db_manager.test_connection()
            assert result is True
    
    async def test_database_test_connection_failure(self):
        """Test failed database connection test."""
        db_manager = DatabaseManager()
        
        with patch.object(db_manager, 'execute_query') as mock_execute:
            mock_execute.side_effect = Exception('Connection failed')
            
            result = await db_manager.test_connection()
            assert result is False


if __name__ == '__main__':
    pytest.main([__file__])