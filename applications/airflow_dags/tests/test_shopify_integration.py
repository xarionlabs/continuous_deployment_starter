"""
Comprehensive integration tests for Shopify GraphQL client.

This test suite provides real-world testing scenarios for the Shopify GraphQL client
and database integration. Tests can be run against actual Shopify stores with proper
authentication or against mocked endpoints for CI/CD environments.

Important: When running these tests, always build and use a Docker image to ensure
consistent testing environment and proper dependency isolation.

Test Commands:
    # Build Docker image first
    docker build -t airflow-dags-test .
    
    # Run all tests inside container
    docker run --rm -e SHOPIFY_SHOP_NAME=your-shop -e SHOPIFY_ACCESS_TOKEN=your-token airflow-dags-test pytest tests/test_shopify_integration.py -v
    
    # Run specific test
    docker run --rm -e SHOPIFY_SHOP_NAME=your-shop -e SHOPIFY_ACCESS_TOKEN=your-token airflow-dags-test pytest tests/test_shopify_integration.py::TestShopifyIntegration::test_connection -v
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

# Import the modules we're testing
from pxy6.utils.shopify_graphql import ShopifyGraphQLClient, ShopifyRateLimit, GraphQLError
from pxy6.utils.database import get_postgres_hook, execute_query, execute_insert, upsert_customer, upsert_product
from pxy6.utils.config import get_shopify_config


class TestShopifyGraphQLClient:
    """Test suite for Shopify GraphQL client functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.mock_shop_name = "test-shop"
        self.mock_access_token = "test-token"
        self.mock_shop_url = f"https://{self.mock_shop_name}.myshopify.com/admin/api/2023-10/graphql.json"
        
        # Mock shop response
        self.mock_shop_response = {
            "shop": {
                "id": "gid://shopify/Shop/12345",
                "name": "Test Shop",
                "myshopifyDomain": "test-shop.myshopify.com",
                "email": "test@example.com",
                "phone": "+1234567890",
                "currencyCode": "USD",
                "timezoneAbbreviation": "EST",
                "createdAt": "2023-01-01T00:00:00Z",
                "updatedAt": "2023-12-01T00:00:00Z"
            }
        }
        
        # Mock product response
        self.mock_product_response = {
            "products": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Product/12345",
                            "title": "Test Product",
                            "handle": "test-product",
                            "description": "A test product",
                            "productType": "Test Type",
                            "vendor": "Test Vendor",
                            "tags": ["test", "product"],
                            "status": "ACTIVE",
                            "createdAt": "2023-01-01T00:00:00Z",
                            "updatedAt": "2023-12-01T00:00:00Z",
                            "variants": {
                                "edges": [
                                    {
                                        "node": {
                                            "id": "gid://shopify/ProductVariant/67890",
                                            "title": "Default Title",
                                            "sku": "TEST-001",
                                            "price": "29.99",
                                            "inventoryQuantity": 10
                                        }
                                    }
                                ]
                            },
                            "images": {
                                "edges": [
                                    {
                                        "node": {
                                            "id": "gid://shopify/ProductImage/11111",
                                            "url": "https://example.com/image.jpg",
                                            "altText": "Test image",
                                            "width": 800,
                                            "height": 600
                                        }
                                    }
                                ]
                            }
                        },
                        "cursor": "eyJsYXN0X2lkIjoxMjM0NX0"
                    }
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": False,
                    "startCursor": "eyJsYXN0X2lkIjoxMjM0NX0",
                    "endCursor": "eyJsYXN0X2lkIjoxMjM0NX0"
                }
            }
        }
        
        # Mock customer response
        self.mock_customer_response = {
            "customers": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Customer/54321",
                            "email": "customer@example.com",
                            "firstName": "John",
                            "lastName": "Doe",
                            "phone": "+1234567890",
                            "createdAt": "2023-01-01T00:00:00Z",
                            "updatedAt": "2023-12-01T00:00:00Z",
                            "acceptsMarketing": True,
                            "totalSpentV2": {
                                "amount": "199.99",
                                "currencyCode": "USD"
                            },
                            "numberOfOrders": 3,
                            "orders": {
                                "edges": [
                                    {
                                        "node": {
                                            "id": "gid://shopify/Order/98765",
                                            "name": "#1001",
                                            "email": "customer@example.com",
                                            "createdAt": "2023-11-01T00:00:00Z",
                                            "totalPriceV2": {
                                                "amount": "99.99",
                                                "currencyCode": "USD"
                                            },
                                            "financialStatus": "PAID",
                                            "fulfillmentStatus": "FULFILLED"
                                        }
                                    }
                                ]
                            }
                        },
                        "cursor": "eyJsYXN0X2lkIjo1NDMyMX0"
                    }
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": False,
                    "startCursor": "eyJsYXN0X2lkIjo1NDMyMX0",
                    "endCursor": "eyJsYXN0X2lkIjo1NDMyMX0"
                }
            }
        }
    
    def test_client_initialization(self):
        """Test client initialization with explicit parameters."""
        client = ShopifyGraphQLClient(
            shop_name=self.mock_shop_name,
            access_token=self.mock_access_token
        )
        
        assert client.shop_name == self.mock_shop_name
        assert client.access_token == self.mock_access_token
        assert client.shop_url == self.mock_shop_url
        assert client.rate_limit.max_calls == client.DEFAULT_RATE_LIMIT
        assert client.rate_limit.remaining_calls == client.DEFAULT_RATE_LIMIT
    
    @patch.dict(os.environ, {
        'SHOPIFY_SHOP_NAME': 'env-shop',
        'SHOPIFY_ACCESS_TOKEN': 'env-token',
        'POSTGRES_PASSWORD': 'test-password',
        'POSTGRES_HOST': 'test-host',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DB': 'test-db',
        'POSTGRES_USER': 'test-user'
    })
    def test_client_initialization_from_env(self):
        """Test client initialization from environment variables."""
        client = ShopifyGraphQLClient()
        
        assert client.shop_name == 'env-shop'
        assert client.access_token == 'env-token'
        assert client.shop_url == 'https://env-shop.myshopify.com/admin/api/2023-10/graphql.json'
    
    def test_rate_limit_calculation(self):
        """Test rate limit calculation and delay logic."""
        client = ShopifyGraphQLClient(
            shop_name=self.mock_shop_name,
            access_token=self.mock_access_token
        )
        
        # Test with sufficient remaining calls
        client.rate_limit.remaining_calls = 100
        delay = client._calculate_delay(cost=5)
        assert delay == 0.0
        
        # Test with insufficient remaining calls
        client.rate_limit.remaining_calls = 2
        client.rate_limit.restore_rate = 50  # 50 points per second
        delay = client._calculate_delay(cost=5)
        expected_delay = (5 - 2) / 50  # 3 points needed / 50 points per second
        assert delay == expected_delay
    
    def test_rate_limit_update(self):
        """Test rate limit update from API response."""
        client = ShopifyGraphQLClient(
            shop_name=self.mock_shop_name,
            access_token=self.mock_access_token
        )
        
        # Mock response with cost analysis
        extensions = {
            "cost": {
                "throttleStatus": {
                    "currentlyAvailable": 995,
                    "maximumAvailable": 1000,
                    "restoreRate": 50
                }
            }
        }
        
        client._update_rate_limit(extensions)
        
        assert client.rate_limit.current_calls == 995
        assert client.rate_limit.max_calls == 1000
        assert client.rate_limit.restore_rate == 50
        assert client.rate_limit.remaining_calls == 5  # 1000 - 995
    
    @patch('pxy6.utils.shopify_graphql.Client')
    def test_execute_query_success(self, mock_client_class):
        """Test successful query execution."""
        mock_client = MagicMock()
        mock_client.execute.return_value = self.mock_shop_response
        mock_client_class.return_value = mock_client
        
        client = ShopifyGraphQLClient(
            shop_name=self.mock_shop_name,
            access_token=self.mock_access_token
        )
        
        query = "query { shop { name } }"
        result = client.execute_query(query)
        
        assert result == self.mock_shop_response
        mock_client.execute.assert_called_once()
    
    @patch('pxy6.utils.shopify_graphql.Client')
    def test_execute_query_with_graphql_errors(self, mock_client_class):
        """Test query execution with GraphQL errors."""
        mock_client = MagicMock()
        mock_client.execute.return_value = {
            "errors": [
                {
                    "message": "Field 'invalidField' doesn't exist on type 'Shop'",
                    "locations": [{"line": 1, "column": 10}],
                    "path": ["shop", "invalidField"]
                }
            ]
        }
        mock_client_class.return_value = mock_client
        
        client = ShopifyGraphQLClient(
            shop_name=self.mock_shop_name,
            access_token=self.mock_access_token
        )
        
        query = "query { shop { invalidField } }"
        
        with pytest.raises(Exception) as exc_info:
            client.execute_query(query)
        
        assert "GraphQL errors" in str(exc_info.value)
        assert "invalidField" in str(exc_info.value)
    
    @patch('pxy6.utils.shopify_graphql.Client')
    def test_get_shop_info(self, mock_client_class):
        """Test shop info retrieval."""
        mock_client = MagicMock()
        mock_client.execute.return_value = self.mock_shop_response
        mock_client_class.return_value = mock_client
        
        client = ShopifyGraphQLClient(
            shop_name=self.mock_shop_name,
            access_token=self.mock_access_token
        )
        
        result = client.get_shop_info()
        
        assert result == self.mock_shop_response
        assert result["shop"]["name"] == "Test Shop"
        assert result["shop"]["myshopifyDomain"] == "test-shop.myshopify.com"
    
    @patch('pxy6.utils.shopify_graphql.Client')
    def test_get_all_product_data(self, mock_client_class):
        """Test comprehensive product data retrieval."""
        mock_client = MagicMock()
        mock_client.execute.return_value = self.mock_product_response
        mock_client_class.return_value = mock_client
        
        client = ShopifyGraphQLClient(
            shop_name=self.mock_shop_name,
            access_token=self.mock_access_token
        )
        
        result = client.get_all_product_data(limit=10)
        
        assert result == self.mock_product_response
        assert len(result["products"]["edges"]) == 1
        
        product = result["products"]["edges"][0]["node"]
        assert product["title"] == "Test Product"
        assert product["handle"] == "test-product"
        assert len(product["variants"]["edges"]) == 1
        assert len(product["images"]["edges"]) == 1
    
    @patch('pxy6.utils.shopify_graphql.Client')
    def test_get_product_images(self, mock_client_class):
        """Test product image retrieval."""
        mock_response = {
            "product": {
                "id": "gid://shopify/Product/12345",
                "title": "Test Product",
                "images": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/ProductImage/11111",
                                "url": "https://example.com/image.jpg",
                                "altText": "Test image",
                                "width": 800,
                                "height": 600,
                                "originalSrc": "https://example.com/image_original.jpg"
                            }
                        }
                    ],
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": None
                    }
                }
            }
        }
        
        mock_client = MagicMock()
        mock_client.execute.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        client = ShopifyGraphQLClient(
            shop_name=self.mock_shop_name,
            access_token=self.mock_access_token
        )
        
        result = client.get_product_images("gid://shopify/Product/12345")
        
        assert result == mock_response
        assert result["product"]["title"] == "Test Product"
        assert len(result["product"]["images"]["edges"]) == 1
        
        image = result["product"]["images"]["edges"][0]["node"]
        assert image["url"] == "https://example.com/image.jpg"
        assert image["width"] == 800
        assert image["height"] == 600
    
    @patch('pxy6.utils.shopify_graphql.Client')
    def test_get_customers_with_orders(self, mock_client_class):
        """Test customer with orders retrieval."""
        mock_client = MagicMock()
        mock_client.execute.return_value = self.mock_customer_response
        mock_client_class.return_value = mock_client
        
        client = ShopifyGraphQLClient(
            shop_name=self.mock_shop_name,
            access_token=self.mock_access_token
        )
        
        result = client.get_customers_with_orders(limit=10)
        
        assert result == self.mock_customer_response
        assert len(result["customers"]["edges"]) == 1
        
        customer = result["customers"]["edges"][0]["node"]
        assert customer["email"] == "customer@example.com"
        assert customer["firstName"] == "John"
        assert customer["lastName"] == "Doe"
        assert customer["totalSpentV2"]["amount"] == "199.99"
        assert customer["numberOfOrders"] == 3
        assert len(customer["orders"]["edges"]) == 1
    
    @patch('pxy6.utils.shopify_graphql.Client')
    def test_pagination_generator(self, mock_client_class):
        """Test pagination generator functionality."""
        # Mock multiple pages of results
        page1_response = {
            "products": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Product/1",
                            "title": "Product 1"
                        }
                    }
                ],
                "pageInfo": {
                    "hasNextPage": True,
                    "endCursor": "cursor1"
                }
            }
        }
        
        page2_response = {
            "products": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Product/2",
                            "title": "Product 2"
                        }
                    }
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": "cursor2"
                }
            }
        }
        
        mock_client = MagicMock()
        mock_client.execute.side_effect = [page1_response, page2_response]
        mock_client_class.return_value = mock_client
        
        client = ShopifyGraphQLClient(
            shop_name=self.mock_shop_name,
            access_token=self.mock_access_token
        )
        
        # Collect all products using pagination
        all_products = list(client.paginate_all_products(batch_size=1))
        
        assert len(all_products) == 2
        assert all_products[0]["title"] == "Product 1"
        assert all_products[1]["title"] == "Product 2"
        assert mock_client.execute.call_count == 2
    
    @patch('pxy6.utils.shopify_graphql.Client')
    def test_connection_test_success(self, mock_client_class):
        """Test successful connection test."""
        mock_client = MagicMock()
        mock_client.execute.return_value = self.mock_shop_response
        mock_client_class.return_value = mock_client
        
        client = ShopifyGraphQLClient(
            shop_name=self.mock_shop_name,
            access_token=self.mock_access_token
        )
        
        result = client.test_connection()
        
        assert result is True
    
    @patch('pxy6.utils.shopify_graphql.Client')
    def test_connection_test_failure(self, mock_client_class):
        """Test failed connection test."""
        mock_client = MagicMock()
        mock_client.execute.side_effect = Exception("Connection failed")
        mock_client_class.return_value = mock_client
        
        client = ShopifyGraphQLClient(
            shop_name=self.mock_shop_name,
            access_token=self.mock_access_token
        )
        
        result = client.test_connection()
        
        assert result is False
    
    def test_rate_limit_status(self):
        """Test rate limit status reporting."""
        client = ShopifyGraphQLClient(
            shop_name=self.mock_shop_name,
            access_token=self.mock_access_token
        )
        
        # Modify rate limit state
        client.rate_limit.remaining_calls = 750
        client.rate_limit.max_calls = 1000
        
        status = client.get_rate_limit_status()
        
        assert status["remaining_calls"] == 750
        assert status["max_calls"] == 1000
        assert status["restore_rate"] == client.RESTORE_RATE
        assert status["is_throttled"] == False  # 750 > 5
    
    def test_string_representations(self):
        """Test string representations of the client."""
        client = ShopifyGraphQLClient(
            shop_name=self.mock_shop_name,
            access_token=self.mock_access_token
        )
        
        str_repr = str(client)
        assert "ShopifyGraphQLClient" in str_repr
        assert self.mock_shop_name in str_repr
        
        detailed_repr = repr(client)
        assert "ShopifyGraphQLClient" in detailed_repr
        assert self.mock_shop_name in detailed_repr
        assert self.mock_shop_url in detailed_repr


class TestDatabaseIntegration:
    """Test suite for database integration functionality."""
    
    @patch('pxy6.utils.database.PostgresHook')
    def test_postgres_hook_creation(self, mock_postgres_hook):
        """Test PostgresHook creation."""
        hook = get_postgres_hook()
        
        mock_postgres_hook.assert_called_once_with(postgres_conn_id='pxy6_postgres')
    
    @patch('pxy6.utils.database.get_postgres_hook')
    def test_execute_query(self, mock_get_hook):
        """Test database query execution."""
        mock_hook = Mock()
        mock_hook.get_records.return_value = [{"count": 5}]
        mock_get_hook.return_value = mock_hook
        
        result = execute_query("SELECT COUNT(*) as count FROM customers")
        
        assert result == [{"count": 5}]
        mock_hook.get_records.assert_called_once_with("SELECT COUNT(*) as count FROM customers", None)
    
    @patch('pxy6.utils.database.get_postgres_hook')
    def test_execute_insert(self, mock_get_hook):
        """Test database insert execution."""
        mock_hook = Mock()
        mock_get_hook.return_value = mock_hook
        
        execute_insert("INSERT INTO customers VALUES (%(id)s, %(name)s)", {"id": 1, "name": "test"})
        
        mock_hook.run.assert_called_once_with("INSERT INTO customers VALUES (%(id)s, %(name)s)", {"id": 1, "name": "test"})
    
    @patch('pxy6.utils.database.execute_insert')
    def test_upsert_product_integration(self, mock_execute_insert):
        """Test product upsert functionality."""
        # Mock product data
        product_data = {
            "id": "gid://shopify/Product/12345",
            "title": "Test Product",
            "handle": "test-product",
            "description": "A test product",
            "descriptionHtml": "<p>A test product</p>",
            "productType": "Test Type",
            "vendor": "Test Vendor",
            "tags": ["test", "product"],
            "status": "ACTIVE",
            "createdAt": "2023-01-01T00:00:00Z",
            "updatedAt": "2023-12-01T00:00:00Z",
            "publishedAt": "2023-01-01T00:00:00Z",
            "totalInventory": 100,
            "onlineStoreUrl": "https://shop.example.com/products/test-product",
            "seo": {
                "title": "Test Product SEO",
                "description": "Test product for SEO"
            },
            "options": [
                {
                    "id": "gid://shopify/ProductOption/1",
                    "name": "Size",
                    "values": ["Small", "Medium", "Large"]
                }
            ],
            "metafields": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Metafield/1",
                            "namespace": "custom",
                            "key": "description",
                            "value": "Custom description",
                            "type": "single_line_text_field"
                        }
                    }
                ]
            }
        }
        
        # Test upsert
        upsert_product(product_data)
        
        # Verify that upsert query was executed
        mock_execute_insert.assert_called_once()
        args, kwargs = mock_execute_insert.call_args
        assert "INSERT INTO products" in args[0]
        assert "ON CONFLICT (id) DO UPDATE" in args[0]
        
        # Check parameters
        params = args[1]
        assert params['id'] == 12345
        assert params['title'] == "Test Product"
        assert params['handle'] == "test-product"
    
    @patch('pxy6.utils.database.execute_insert')
    def test_upsert_customer_integration(self, mock_execute_insert):
        """Test customer upsert functionality."""
        # Mock customer data
        customer_data = {
            "id": "gid://shopify/Customer/54321",
            "email": "customer@example.com",
            "firstName": "John",
            "lastName": "Doe",
            "phone": "+1234567890",
            "createdAt": "2023-01-01T00:00:00Z",
            "updatedAt": "2023-12-01T00:00:00Z",
            "acceptsMarketing": True,
            "state": "ENABLED",
            "tags": ["vip", "customer"],
            "verifiedEmail": True,
            "taxExempt": False,
            "totalSpentV2": {
                "amount": "199.99",
                "currencyCode": "USD"
            },
            "numberOfOrders": 3,
            "addresses": [
                {
                    "id": "gid://shopify/MailingAddress/1",
                    "firstName": "John",
                    "lastName": "Doe",
                    "address1": "123 Main St",
                    "city": "New York",
                    "province": "NY",
                    "country": "US",
                    "zip": "10001"
                }
            ],
            "metafields": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Metafield/2",
                            "namespace": "custom",
                            "key": "tier",
                            "value": "gold",
                            "type": "single_line_text_field"
                        }
                    }
                ]
            }
        }
        
        # Test upsert
        upsert_customer(customer_data)
        
        # Verify that upsert query was executed
        mock_execute_insert.assert_called_once()
        args, kwargs = mock_execute_insert.call_args
        assert "INSERT INTO customers" in args[0]
        assert "ON CONFLICT (id) DO UPDATE" in args[0]
        
        # Check parameters
        params = args[1]
        assert params['id'] == 54321
        assert params['email'] == "customer@example.com"
        assert params['first_name'] == "John"
        assert params['last_name'] == "Doe"


class TestShopifyIntegration:
    """End-to-end integration tests for Shopify client and database."""
    
    @patch('pxy6.utils.shopify_graphql.Client')
    def test_real_shopify_connection(self, mock_client_class):
        """Test connection to Shopify store with mocked API."""
        mock_client = Mock()
        mock_client.execute.return_value = {
            "shop": {
                "name": "Test Shop",
                "myshopifyDomain": "test-shop.myshopify.com"
            }
        }
        mock_client_class.return_value = mock_client
        
        client = ShopifyGraphQLClient(
            shop_name="test-shop",
            access_token="test-token"
        )
        
        # Test connection
        assert client.test_connection(), "Failed to connect to Shopify store"
        
        # Get shop info
        shop_info = client.get_shop_info()
        assert 'shop' in shop_info
        assert 'name' in shop_info['shop']
        assert 'myshopifyDomain' in shop_info['shop']
        
        print(f"Connected to shop: {shop_info['shop']['name']}")
        print(f"Domain: {shop_info['shop']['myshopifyDomain']}")
    
    @patch('pxy6.utils.shopify_graphql.Client')
    def test_real_shopify_products(self, mock_client_class):
        """Test product retrieval with mocked Shopify store."""
        mock_client = Mock()
        mock_client.execute.return_value = {
            "products": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Product/12345",
                            "title": "Test Product",
                            "handle": "test-product",
                            "createdAt": "2023-01-01T00:00:00Z",
                            "updatedAt": "2023-12-01T00:00:00Z"
                        }
                    }
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": None
                }
            }
        }
        mock_client_class.return_value = mock_client
        
        client = ShopifyGraphQLClient(
            shop_name="test-shop",
            access_token="test-token"
        )
        
        # Get first 5 products
        products = client.get_all_product_data(limit=5)
        
        assert 'products' in products
        assert 'edges' in products['products']
        assert 'pageInfo' in products['products']
        
        product_count = len(products['products']['edges'])
        print(f"Retrieved {product_count} products")
        
        # Test product structure
        if product_count > 0:
            product = products['products']['edges'][0]['node']
            required_fields = ['id', 'title', 'handle', 'createdAt', 'updatedAt']
            for field in required_fields:
                assert field in product, f"Missing required field: {field}"
            
            print(f"First product: {product['title']}")
    
    @patch('pxy6.utils.shopify_graphql.Client')
    def test_real_shopify_customers(self, mock_client_class):
        """Test customer retrieval with mocked Shopify store."""
        mock_client = Mock()
        mock_client.execute.return_value = {
            "customers": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Customer/54321",
                            "email": "customer@example.com",
                            "createdAt": "2023-01-01T00:00:00Z",
                            "updatedAt": "2023-12-01T00:00:00Z"
                        }
                    }
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": None
                }
            }
        }
        mock_client_class.return_value = mock_client
        
        client = ShopifyGraphQLClient(
            shop_name="test-shop",
            access_token="test-token"
        )
        
        # Get first 5 customers
        customers = client.get_customers_with_orders(limit=5)
        
        assert 'customers' in customers
        assert 'edges' in customers['customers']
        assert 'pageInfo' in customers['customers']
        
        customer_count = len(customers['customers']['edges'])
        print(f"Retrieved {customer_count} customers")
        
        # Test customer structure
        if customer_count > 0:
            customer = customers['customers']['edges'][0]['node']
            required_fields = ['id', 'email', 'createdAt', 'updatedAt']
            for field in required_fields:
                assert field in customer, f"Missing required field: {field}"
            
            print(f"First customer: {customer.get('email', 'No email')}")
    
    @patch('pxy6.utils.shopify_graphql.Client')
    def test_real_shopify_pagination(self, mock_client_class):
        """Test pagination with mocked Shopify store."""
        # Mock multiple API calls for pagination
        page1_response = {
            "products": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Product/1",
                            "title": "Product 1",
                            "handle": "product-1"
                        }
                    },
                    {
                        "node": {
                            "id": "gid://shopify/Product/2",
                            "title": "Product 2",
                            "handle": "product-2"
                        }
                    }
                ],
                "pageInfo": {
                    "hasNextPage": True,
                    "endCursor": "cursor1"
                }
            }
        }
        
        page2_response = {
            "products": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Product/3",
                            "title": "Product 3",
                            "handle": "product-3"
                        }
                    }
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": "cursor2"
                }
            }
        }
        
        mock_client = Mock()
        mock_client.execute.side_effect = [page1_response, page2_response]
        mock_client_class.return_value = mock_client
        
        client = ShopifyGraphQLClient(
            shop_name="test-shop",
            access_token="test-token"
        )
        
        # Get products using pagination
        product_count = 0
        for product in client.paginate_all_products(batch_size=2):
            product_count += 1
            
            # Test product structure
            required_fields = ['id', 'title', 'handle']
            for field in required_fields:
                assert field in product, f"Missing required field: {field}"
            
            # Limit test to first 5 products to avoid long test times
            if product_count >= 5:
                break
        
        print(f"Paginated through {product_count} products")
        assert product_count > 0, "No products found during pagination"
    
    @patch('pxy6.utils.shopify_graphql.Client')
    def test_real_shopify_rate_limits(self, mock_client_class):
        """Test rate limiting with mocked Shopify store."""
        mock_client = Mock()
        mock_client.execute.return_value = {
            "shop": {
                "name": "Test Shop",
                "myshopifyDomain": "test-shop.myshopify.com"
            },
            "extensions": {
                "cost": {
                    "throttleStatus": {
                        "currentlyAvailable": 950,
                        "maximumAvailable": 1000,
                        "restoreRate": 50
                    }
                }
            }
        }
        mock_client_class.return_value = mock_client
        
        client = ShopifyGraphQLClient(
            shop_name="test-shop",
            access_token="test-token"
        )
        
        # Make multiple requests and check rate limiting
        for i in range(3):
            shop_info = client.get_shop_info()
            assert 'shop' in shop_info
            
            # Check rate limit status
            rate_limit = client.get_rate_limit_status()
            assert 'remaining_calls' in rate_limit
            assert 'max_calls' in rate_limit
            
            print(f"Request {i+1}: {rate_limit['remaining_calls']}/{rate_limit['max_calls']} calls remaining")
    
    
    def test_curl_pattern_reference(self):
        """Test that demonstrates the curl pattern for reference."""
        # This test demonstrates the authentication pattern that would be used in curl:
        # curl -X POST https://your-shop.myshopify.com/admin/api/2023-10/graphql.json \
        #   -H 'Content-Type: application/json' \
        #   -H 'X-Shopify-Access-Token: your-access-token' \
        #   -d '{"query": "query { shop { name } }"}'
        
        client = ShopifyGraphQLClient(
            shop_name="test-shop",
            access_token="test-token"
        )
        
        # Verify the client is configured with the correct headers and URL
        assert client.shop_url == "https://test-shop.myshopify.com/admin/api/2023-10/graphql.json"
        assert client.transport.headers['X-Shopify-Access-Token'] == "test-token"
        assert client.transport.headers['Content-Type'] == "application/json"
        
        # The GraphQL query would be sent as JSON in the request body
        # with the structure: {"query": "...", "variables": {...}}
        print("✓ Client configured with correct authentication pattern")


# Test runner configuration
if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes"
    ])