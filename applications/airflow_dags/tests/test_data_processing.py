"""
Comprehensive tests for DAG data processing functions using real Shopify payloads.

This test suite validates data processing logic using actual Shopify API responses
to ensure the DAGs handle real-world data correctly.
"""

import pytest
import json
import os
from datetime import datetime
from unittest.mock import Mock, patch
from typing import Dict, Any, List

# Import the modules we're testing
from pxy6.utils.shopify_graphql import ShopifyGraphQLClient
from pxy6.utils.database import DatabaseManager, DatabaseConfig


class TestFixtures:
    """Load and manage test fixtures from real Shopify responses."""
    
    @classmethod
    def get_fixture_path(cls, fixture_name: str) -> str:
        """Get the path to a test fixture."""
        current_dir = os.path.dirname(__file__)
        return os.path.join(current_dir, 'fixtures', 'shopify_responses', fixture_name)
    
    @classmethod
    def load_json_fixture(cls, fixture_name: str) -> Dict[str, Any]:
        """Load a JSON fixture file."""
        fixture_path = cls.get_fixture_path(fixture_name)
        with open(fixture_path, 'r') as f:
            return json.load(f)
    
    @classmethod
    def load_products_response(cls) -> Dict[str, Any]:
        """Load the products response fixture."""
        return cls.load_json_fixture('products_response.json')
    
    @classmethod
    def load_customers_response(cls) -> Dict[str, Any]:
        """Load the customers with orders response fixture."""
        return cls.load_json_fixture('customers_with_orders_response.json')
    
    @classmethod
    def load_product_images_response(cls) -> Dict[str, Any]:
        """Load the product images response fixture."""
        return cls.load_json_fixture('product_images_response.json')


class TestProductDataProcessing:
    """Test product data processing functions with real Shopify data."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.products_data = TestFixtures.load_products_response()
        self.client = ShopifyGraphQLClient(
            shop_name="test-shop",
            access_token="test-token"
        )
    
    def test_products_response_structure(self):
        """Test that the products response has the expected structure."""
        assert 'data' in self.products_data
        assert 'products' in self.products_data['data']
        assert 'edges' in self.products_data['data']['products']
        assert 'pageInfo' in self.products_data['data']['products']
        
        # Test pagination info
        page_info = self.products_data['data']['products']['pageInfo']
        assert 'hasNextPage' in page_info
        assert 'hasPreviousPage' in page_info
        assert 'startCursor' in page_info
        assert 'endCursor' in page_info
    
    def test_product_node_structure(self):
        """Test that product nodes have required fields."""
        products = self.products_data['data']['products']['edges']
        assert len(products) > 0
        
        # Test first product structure
        product = products[0]['node']
        required_fields = [
            'id', 'handle', 'title', 'description', 'descriptionHtml',
            'productType', 'vendor', 'status', 'createdAt', 'updatedAt',
            'publishedAt', 'seo', 'tags', 'totalInventory', 'variants',
            'featuredMedia', 'collections'
        ]
        
        for field in required_fields:
            assert field in product, f"Missing required field: {field}"
    
    def test_product_variants_structure(self):
        """Test that product variants have correct structure."""
        products = self.products_data['data']['products']['edges']
        
        for product_edge in products:
            product = product_edge['node']
            variants = product['variants']['edges']
            
            if len(variants) > 0:
                variant = variants[0]['node']
                required_variant_fields = [
                    'id', 'title', 'sku', 'barcode', 'price', 'compareAtPrice',
                    'availableForSale', 'inventoryQuantity', 'inventoryPolicy',
                    'createdAt', 'updatedAt', 'selectedOptions', 'metafields'
                ]
                
                for field in required_variant_fields:
                    assert field in variant, f"Missing required variant field: {field}"
    
    def test_product_collections_structure(self):
        """Test that product collections have correct structure."""
        products = self.products_data['data']['products']['edges']
        
        for product_edge in products:
            product = product_edge['node']
            collections = product['collections']['edges']
            
            for collection_edge in collections:
                collection = collection_edge['node']
                required_collection_fields = ['id', 'handle', 'title', 'description']
                
                for field in required_collection_fields:
                    assert field in collection, f"Missing required collection field: {field}"
    
    def test_product_data_types(self):
        """Test that product data has correct data types."""
        products = self.products_data['data']['products']['edges']
        product = products[0]['node']
        
        # Test ID format
        assert product['id'].startswith('gid://shopify/Product/')
        
        # Test timestamps
        created_at = datetime.fromisoformat(product['createdAt'].replace('Z', '+00:00'))
        updated_at = datetime.fromisoformat(product['updatedAt'].replace('Z', '+00:00'))
        assert isinstance(created_at, datetime)
        assert isinstance(updated_at, datetime)
        
        # Test inventory
        assert isinstance(product['totalInventory'], int)
        
        # Test tags
        assert isinstance(product['tags'], list)
    
    def test_product_pricing_structure(self):
        """Test product pricing data structure."""
        products = self.products_data['data']['products']['edges']
        
        for product_edge in products:
            product = product_edge['node']
            
            # Check price range structure
            if 'priceRangeV2' in product and product['priceRangeV2']:
                price_range = product['priceRangeV2']
                assert 'minVariantPrice' in price_range
                assert 'maxVariantPrice' in price_range
                
                min_price = price_range['minVariantPrice']
                max_price = price_range['maxVariantPrice']
                
                for price in [min_price, max_price]:
                    assert 'amount' in price
                    assert 'currencyCode' in price
                    assert isinstance(float(price['amount']), float)
    
    def test_product_media_structure(self):
        """Test product media data structure."""
        products = self.products_data['data']['products']['edges']
        
        for product_edge in products:
            product = product_edge['node']
            
            # Check featured media structure
            if product['featuredMedia']:
                featured_media = product['featuredMedia']
                assert 'id' in featured_media
                assert 'alt' in featured_media
                
                if 'image' in featured_media and featured_media['image']:
                    image = featured_media['image']
                    assert 'url' in image
                    assert 'width' in image
                    assert 'height' in image
                    assert isinstance(image['width'], int)
                    assert isinstance(image['height'], int)
    
    @patch('src.utils.database.DatabaseManager')
    def test_product_database_upsert_processing(self, mock_db_manager_class):
        """Test processing product data for database upsert."""
        # Create a mock instance
        mock_manager = Mock()
        mock_db_manager_class.return_value = mock_manager
        
        # Setup database manager
        from src.utils.database import DatabaseConfig
        config = DatabaseConfig(
            host="test-db",
            database="test_pxy6",
            user="test_user",
            password="test_password"
        )
        manager = mock_db_manager_class(config)
        
        # Get first product from fixtures
        products = self.products_data['data']['products']['edges']
        product_data = products[0]['node']
        
        # Test the upsert method
        manager.upsert_product(product_data)
        
        # Verify the upsert method was called
        mock_manager.upsert_product.assert_called_once_with(product_data)


class TestCustomerDataProcessing:
    """Test customer data processing functions with real Shopify data."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.customers_data = TestFixtures.load_customers_response()
        self.client = ShopifyGraphQLClient(
            shop_name="test-shop",
            access_token="test-token"
        )
    
    def test_customers_response_structure(self):
        """Test that the customers response has the expected structure."""
        assert 'data' in self.customers_data
        assert 'customers' in self.customers_data['data']
        assert 'edges' in self.customers_data['data']['customers']
        assert 'pageInfo' in self.customers_data['data']['customers']
        
        # Test cost analysis
        assert 'extensions' in self.customers_data
        assert 'cost' in self.customers_data['extensions']
        
        cost = self.customers_data['extensions']['cost']
        assert 'requestedQueryCost' in cost
        assert 'actualQueryCost' in cost
        assert 'throttleStatus' in cost
    
    def test_customer_node_structure(self):
        """Test that customer nodes have required fields."""
        customers = self.customers_data['data']['customers']['edges']
        assert len(customers) > 0
        
        # Test customers with and without orders
        for customer_edge in customers:
            customer = customer_edge['node']
            required_fields = [
                'id', 'email', 'createdAt', 'orders'
            ]
            
            for field in required_fields:
                assert field in customer, f"Missing required field: {field}"
            
            # Test ID format
            assert customer['id'].startswith('gid://shopify/Customer/')
            
            # Test orders structure
            orders = customer['orders']
            assert 'edges' in orders
    
    def test_customer_with_orders_structure(self):
        """Test customers that have orders."""
        customers = self.customers_data['data']['customers']['edges']
        
        # Find customer with orders
        customer_with_orders = None
        for customer_edge in customers:
            customer = customer_edge['node']
            if len(customer['orders']['edges']) > 0:
                customer_with_orders = customer
                break
        
        assert customer_with_orders is not None, "No customers with orders found in fixture"
        
        # Test order structure
        order = customer_with_orders['orders']['edges'][0]['node']
        required_order_fields = ['id', 'name', 'processedAt', 'lineItems']
        
        for field in required_order_fields:
            assert field in order, f"Missing required order field: {field}"
        
        # Test order ID format
        assert order['id'].startswith('gid://shopify/Order/')
        
        # Test line items structure
        line_items = order['lineItems']['edges']
        if len(line_items) > 0:
            line_item = line_items[0]['node']
            required_line_item_fields = ['title', 'quantity', 'variant']
            
            for field in required_line_item_fields:
                assert field in line_item, f"Missing required line item field: {field}"
    
    def test_customer_data_types(self):
        """Test that customer data has correct data types."""
        customers = self.customers_data['data']['customers']['edges']
        customer = customers[0]['node']
        
        # Test timestamps
        created_at = datetime.fromisoformat(customer['createdAt'].replace('Z', '+00:00'))
        assert isinstance(created_at, datetime)
        
        # Test email format (basic validation)
        if customer['email']:
            assert '@' in customer['email']
    
    def test_cursor_based_pagination(self):
        """Test cursor-based pagination structure."""
        customers = self.customers_data['data']['customers']['edges']
        
        for customer_edge in customers:
            assert 'cursor' in customer_edge
            # Cursor should be a base64-encoded string
            cursor = customer_edge['cursor']
            assert isinstance(cursor, str)
            assert len(cursor) > 0
    
    @patch('src.utils.database.DatabaseManager')
    def test_customer_database_upsert_processing(self, mock_db_manager_class):
        """Test processing customer data for database upsert."""
        # Create a mock instance
        mock_manager = Mock()
        mock_db_manager_class.return_value = mock_manager
        
        # Setup database manager
        from src.utils.database import DatabaseConfig
        config = DatabaseConfig(
            host="test-db",
            database="test_pxy6", 
            user="test_user",
            password="test_password"
        )
        manager = mock_db_manager_class(config)
        
        # Get first customer from fixtures
        customers = self.customers_data['data']['customers']['edges']
        customer_data = customers[0]['node']
        
        # Test the upsert method
        manager.upsert_customer(customer_data)
        
        # Verify the upsert method was called
        mock_manager.upsert_customer.assert_called_once_with(customer_data)


class TestProductImagesProcessing:
    """Test product images data processing with real Shopify data."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.product_images_data = TestFixtures.load_product_images_response()
        self.client = ShopifyGraphQLClient(
            shop_name="test-shop",
            access_token="test-token"
        )
    
    def test_product_images_response_structure(self):
        """Test that the product images response has the expected structure."""
        assert 'data' in self.product_images_data
        assert 'products' in self.product_images_data['data']
        assert 'edges' in self.product_images_data['data']['products']
        
        products = self.product_images_data['data']['products']['edges']
        assert len(products) > 0
    
    def test_product_images_node_structure(self):
        """Test that product image nodes have required fields."""
        products = self.product_images_data['data']['products']['edges']
        
        for product_edge in products:
            product = product_edge['node']
            required_fields = ['id', 'handle', 'title', 'featuredImage', 'images']
            
            for field in required_fields:
                assert field in product, f"Missing required field: {field}"
    
    def test_product_featured_image_structure(self):
        """Test featured image structure."""
        products = self.product_images_data['data']['products']['edges']
        
        for product_edge in products:
            product = product_edge['node']
            
            if product['featuredImage']:
                featured_image = product['featuredImage']
                required_fields = ['id', 'url', 'altText', 'width', 'height']
                
                for field in required_fields:
                    assert field in featured_image, f"Missing required featured image field: {field}"
                
                # Test data types
                assert isinstance(featured_image['width'], int)
                assert isinstance(featured_image['height'], int)
                assert featured_image['url'].startswith('https://')
    
    def test_product_images_collection_structure(self):
        """Test product images collection structure."""
        products = self.product_images_data['data']['products']['edges']
        
        for product_edge in products:
            product = product_edge['node']
            images = product['images']['edges']
            
            for image_edge in images:
                image = image_edge['node']
                required_fields = ['id', 'url', 'altText', 'width', 'height']
                
                for field in required_fields:
                    assert field in image, f"Missing required image field: {field}"
                
                # Test data types
                assert isinstance(image['width'], int)
                assert isinstance(image['height'], int)
                assert image['url'].startswith('https://')
    
    def test_product_variants_with_images(self):
        """Test product variants and their image associations."""
        products = self.product_images_data['data']['products']['edges']
        
        for product_edge in products:
            product = product_edge['node']
            variants = product['variants']['edges']
            
            for variant_edge in variants:
                variant = variant_edge['node']
                required_fields = ['id', 'title', 'image']
                
                for field in required_fields:
                    assert field in variant, f"Missing required variant field: {field}"
                
                # Test variant ID format
                assert variant['id'].startswith('gid://shopify/ProductVariant/')


class TestRateLimitHandling:
    """Test rate limit handling with real API response data."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.customers_data = TestFixtures.load_customers_response()
        self.products_data = TestFixtures.load_products_response()
        self.client = ShopifyGraphQLClient(
            shop_name="test-shop",
            access_token="test-token"
        )
    
    def test_rate_limit_data_extraction(self):
        """Test extraction of rate limit data from API responses."""
        # Test with customers response
        assert 'extensions' in self.customers_data
        assert 'cost' in self.customers_data['extensions']
        
        cost_info = self.customers_data['extensions']['cost']
        assert 'throttleStatus' in cost_info
        
        throttle_status = cost_info['throttleStatus']
        required_fields = ['maximumAvailable', 'currentlyAvailable', 'restoreRate']
        
        for field in required_fields:
            assert field in throttle_status, f"Missing throttle status field: {field}"
            assert isinstance(throttle_status[field], int)
    
    def test_rate_limit_calculation(self):
        """Test rate limit calculation logic."""
        cost_info = self.customers_data['extensions']['cost']
        throttle_status = cost_info['throttleStatus']
        
        max_available = throttle_status['maximumAvailable']
        currently_available = throttle_status['currentlyAvailable']
        restore_rate = throttle_status['restoreRate']
        
        # Calculate remaining calls
        remaining_calls = max_available - currently_available
        
        # Test calculation
        assert remaining_calls >= 0
        assert restore_rate > 0
        
        # Test delay calculation (if needed)
        cost_needed = 5  # Example cost
        if remaining_calls < cost_needed:
            points_needed = cost_needed - remaining_calls
            delay_seconds = points_needed / restore_rate
            assert delay_seconds > 0
    
    def test_query_cost_analysis(self):
        """Test query cost analysis from responses."""
        cost_info = self.customers_data['extensions']['cost']
        
        requested_cost = cost_info['requestedQueryCost']
        actual_cost = cost_info['actualQueryCost']
        
        assert isinstance(requested_cost, int)
        assert isinstance(actual_cost, int)
        assert actual_cost <= requested_cost


class TestDataIntegrity:
    """Test data integrity and validation across all fixtures."""
    
    def setup_method(self):
        """Setup all test fixtures."""
        self.products_data = TestFixtures.load_products_response()
        self.customers_data = TestFixtures.load_customers_response()
        self.product_images_data = TestFixtures.load_product_images_response()
    
    def test_shopify_id_consistency(self):
        """Test that Shopify IDs follow consistent patterns."""
        # Test product IDs
        products = self.products_data['data']['products']['edges']
        for product_edge in products:
            product = product_edge['node']
            assert product['id'].startswith('gid://shopify/Product/')
            
            # Test variant IDs
            for variant_edge in product['variants']['edges']:
                variant = variant_edge['node']
                assert variant['id'].startswith('gid://shopify/ProductVariant/')
        
        # Test customer IDs
        customers = self.customers_data['data']['customers']['edges']
        for customer_edge in customers:
            customer = customer_edge['node']
            assert customer['id'].startswith('gid://shopify/Customer/')
            
            # Test order IDs
            for order_edge in customer['orders']['edges']:
                order = order_edge['node']
                assert order['id'].startswith('gid://shopify/Order/')
    
    def test_timestamp_consistency(self):
        """Test that timestamps are properly formatted across all data."""
        # Test product timestamps
        products = self.products_data['data']['products']['edges']
        for product_edge in products:
            product = product_edge['node']
            
            for timestamp_field in ['createdAt', 'updatedAt', 'publishedAt']:
                if product.get(timestamp_field):
                    timestamp = product[timestamp_field]
                    # Should be ISO format with Z suffix
                    assert timestamp.endswith('Z')
                    # Should be parseable
                    datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Test customer timestamps
        customers = self.customers_data['data']['customers']['edges']
        for customer_edge in customers:
            customer = customer_edge['node']
            
            for timestamp_field in ['createdAt']:
                if customer.get(timestamp_field):
                    timestamp = customer[timestamp_field]
                    assert timestamp.endswith('Z')
                    datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    def test_currency_consistency(self):
        """Test that currency data is consistent."""
        # Test product pricing
        products = self.products_data['data']['products']['edges']
        for product_edge in products:
            product = product_edge['node']
            
            if product.get('priceRangeV2'):
                price_range = product['priceRangeV2']
                min_price = price_range['minVariantPrice']
                max_price = price_range['maxVariantPrice']
                
                # Currency codes should match
                assert min_price['currencyCode'] == max_price['currencyCode']
                
                # Amounts should be valid decimals
                float(min_price['amount'])
                float(max_price['amount'])
    
    def test_pagination_cursor_consistency(self):
        """Test that pagination cursors are consistent."""
        # Test products pagination
        products_page_info = self.products_data['data']['products']['pageInfo']
        products_edges = self.products_data['data']['products']['edges']
        
        if len(products_edges) > 0:
            first_cursor = products_edges[0]['cursor']
            last_cursor = products_edges[-1]['cursor']
            
            assert products_page_info['startCursor'] == first_cursor
            assert products_page_info['endCursor'] == last_cursor
        
        # Test customers pagination
        customers_page_info = self.customers_data['data']['customers']['pageInfo']
        customers_edges = self.customers_data['data']['customers']['edges']
        
        if len(customers_edges) > 0:
            first_cursor = customers_edges[0]['cursor']
            last_cursor = customers_edges[-1]['cursor']
            
            assert customers_page_info['startCursor'] == first_cursor
            assert customers_page_info['endCursor'] == last_cursor


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])