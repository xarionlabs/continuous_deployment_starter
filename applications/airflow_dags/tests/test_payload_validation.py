"""
Simple payload validation tests using real Shopify data.

This test suite validates the structure and content of real Shopify API responses
to ensure our DAGs can process the data correctly.
"""

import pytest
import json
import os
from datetime import datetime
from typing import Dict, Any, List


class TestShopifyPayloads:
    """Test real Shopify API response payloads."""
    
    def setup_method(self):
        """Load test fixtures."""
        # Load real Shopify response payloads
        fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures', 'shopify_responses')
        
        with open(os.path.join(fixtures_dir, 'products_response.json'), 'r') as f:
            self.products_data = json.load(f)
        
        with open(os.path.join(fixtures_dir, 'customers_with_orders_response.json'), 'r') as f:
            self.customers_data = json.load(f)
        
        with open(os.path.join(fixtures_dir, 'product_images_response.json'), 'r') as f:
            self.product_images_data = json.load(f)
    
    def test_products_payload_structure(self):
        """Test that products payload has expected structure."""
        # Test top-level structure
        assert 'data' in self.products_data
        assert 'products' in self.products_data['data']
        assert 'edges' in self.products_data['data']['products']
        assert 'pageInfo' in self.products_data['data']['products']
        
        # Test products array is not empty
        products = self.products_data['data']['products']['edges']
        assert len(products) > 0
        
        # Test first product structure
        first_product = products[0]['node']
        required_fields = [
            'id', 'handle', 'title', 'description', 'productType', 
            'vendor', 'status', 'createdAt', 'updatedAt', 'variants'
        ]
        
        for field in required_fields:
            assert field in first_product, f"Missing required field: {field}"
        
        # Test product ID format
        assert first_product['id'].startswith('gid://shopify/Product/')
        
        # Test variants structure
        variants = first_product['variants']['edges']
        if len(variants) > 0:
            variant = variants[0]['node']
            variant_fields = ['id', 'title', 'price', 'availableForSale']
            for field in variant_fields:
                assert field in variant, f"Missing variant field: {field}"
    
    def test_customers_payload_structure(self):
        """Test that customers payload has expected structure."""
        # Test top-level structure
        assert 'data' in self.customers_data
        assert 'customers' in self.customers_data['data']
        assert 'edges' in self.customers_data['data']['customers']
        assert 'pageInfo' in self.customers_data['data']['customers']
        
        # Test customers array is not empty
        customers = self.customers_data['data']['customers']['edges']
        assert len(customers) > 0
        
        # Test first customer structure
        first_customer = customers[0]['node']
        required_fields = ['id', 'email', 'createdAt', 'orders']
        
        for field in required_fields:
            assert field in first_customer, f"Missing required field: {field}"
        
        # Test customer ID format
        assert first_customer['id'].startswith('gid://shopify/Customer/')
        
        # Test orders structure
        orders = first_customer['orders']['edges']
        # Orders might be empty, but structure should exist
        assert isinstance(orders, list)
    
    def test_product_images_payload_structure(self):
        """Test that product images payload has expected structure."""
        # Test top-level structure
        assert 'data' in self.product_images_data
        assert 'products' in self.product_images_data['data']
        assert 'edges' in self.product_images_data['data']['products']
        
        # Test products array is not empty
        products = self.product_images_data['data']['products']['edges']
        assert len(products) > 0
        
        # Test first product structure
        first_product = products[0]['node']
        required_fields = ['id', 'title', 'images', 'variants']
        
        for field in required_fields:
            assert field in first_product, f"Missing required field: {field}"
        
        # Test images structure
        images = first_product['images']['edges']
        if len(images) > 0:
            image = images[0]['node']
            image_fields = ['id', 'url', 'width', 'height']
            for field in image_fields:
                assert field in image, f"Missing image field: {field}"
            
            # Test image URL is valid
            assert image['url'].startswith('https://')
            assert isinstance(image['width'], int)
            assert isinstance(image['height'], int)
    
    def test_rate_limiting_data(self):
        """Test rate limiting information in API responses."""
        # Test rate limit data in customers response
        assert 'extensions' in self.customers_data
        assert 'cost' in self.customers_data['extensions']
        
        cost_info = self.customers_data['extensions']['cost']
        rate_limit_fields = ['requestedQueryCost', 'actualQueryCost', 'throttleStatus']
        
        for field in rate_limit_fields:
            assert field in cost_info, f"Missing rate limit field: {field}"
        
        # Test throttle status structure
        throttle_status = cost_info['throttleStatus']
        throttle_fields = ['maximumAvailable', 'currentlyAvailable', 'restoreRate']
        
        for field in throttle_fields:
            assert field in throttle_status, f"Missing throttle field: {field}"
            assert isinstance(throttle_status[field], int)
    
    def test_pagination_cursors(self):
        """Test pagination cursor structure."""
        # Test products pagination
        products_page_info = self.products_data['data']['products']['pageInfo']
        pagination_fields = ['hasNextPage', 'hasPreviousPage', 'startCursor', 'endCursor']
        
        for field in pagination_fields:
            assert field in products_page_info, f"Missing pagination field: {field}"
        
        # Test customers pagination
        customers_page_info = self.customers_data['data']['customers']['pageInfo']
        
        for field in pagination_fields:
            assert field in customers_page_info, f"Missing pagination field: {field}"
        
        # Test cursor consistency
        products_edges = self.products_data['data']['products']['edges']
        if len(products_edges) > 0:
            first_cursor = products_edges[0]['cursor']
            last_cursor = products_edges[-1]['cursor']
            assert products_page_info['startCursor'] == first_cursor
            assert products_page_info['endCursor'] == last_cursor
    
    def test_shopify_id_formats(self):
        """Test that Shopify IDs follow expected format."""
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
            
            # Test order IDs if present
            for order_edge in customer['orders']['edges']:
                order = order_edge['node']
                assert order['id'].startswith('gid://shopify/Order/')
    
    def test_timestamp_formats(self):
        """Test that timestamps are properly formatted."""
        # Test product timestamps
        products = self.products_data['data']['products']['edges']
        first_product = products[0]['node']
        
        for timestamp_field in ['createdAt', 'updatedAt']:
            if first_product.get(timestamp_field):
                timestamp = first_product[timestamp_field]
                # Should be ISO format with Z suffix
                assert timestamp.endswith('Z')
                # Should be parseable as datetime
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Test customer timestamps
        customers = self.customers_data['data']['customers']['edges']
        first_customer = customers[0]['node']
        
        if first_customer.get('createdAt'):
            timestamp = first_customer['createdAt']
            assert timestamp.endswith('Z')
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    def test_currency_data(self):
        """Test currency data structure."""
        # Test product pricing
        products = self.products_data['data']['products']['edges']
        for product_edge in products:
            product = product_edge['node']
            
            if product.get('priceRangeV2'):
                price_range = product['priceRangeV2']
                min_price = price_range['minVariantPrice']
                max_price = price_range['maxVariantPrice']
                
                # Both prices should have amount and currency code
                assert 'amount' in min_price
                assert 'currencyCode' in min_price
                assert 'amount' in max_price
                assert 'currencyCode' in max_price
                
                # Currency codes should match
                assert min_price['currencyCode'] == max_price['currencyCode']
                
                # Amounts should be valid numbers
                float(min_price['amount'])
                float(max_price['amount'])
    
    def test_data_completeness(self):
        """Test that the payloads contain meaningful data."""
        # Products should have meaningful content
        products = self.products_data['data']['products']['edges']
        assert len(products) >= 5, "Should have at least 5 products for testing"
        
        # At least one product should have variants
        has_variants = any(
            len(product['node']['variants']['edges']) > 0 
            for product in products
        )
        assert has_variants, "At least one product should have variants"
        
        # At least one product should have images
        has_images = any(
            len(product['node'].get('images', {}).get('edges', [])) > 0 
            for product in self.product_images_data['data']['products']['edges']
        )
        assert has_images, "At least one product should have images"
        
        # At least one customer should have orders
        customers = self.customers_data['data']['customers']['edges']
        has_orders = any(
            len(customer['node']['orders']['edges']) > 0 
            for customer in customers
        )
        assert has_orders, "At least one customer should have orders"
    
    def test_data_processing_readiness(self):
        """Test that data is ready for DAG processing."""
        # Test that we can extract key information for database storage
        
        # From products
        products = self.products_data['data']['products']['edges']
        first_product = products[0]['node']
        
        # Essential product fields for database
        product_data = {
            'shopify_id': first_product['id'],
            'title': first_product['title'],
            'handle': first_product['handle'],
            'vendor': first_product.get('vendor', ''),
            'product_type': first_product.get('productType', ''),
            'created_at': first_product['createdAt'],
            'updated_at': first_product['updatedAt']
        }
        
        # Verify all essential fields are present and valid
        assert all(product_data.values()), "All essential product fields should be present"
        
        # From customers
        customers = self.customers_data['data']['customers']['edges']
        first_customer = customers[0]['node']
        
        customer_data = {
            'shopify_id': first_customer['id'],
            'email': first_customer.get('email', ''),
            'created_at': first_customer['createdAt'],
            'orders_count': len(first_customer['orders']['edges'])
        }
        
        # Verify customer data is extractable
        assert customer_data['shopify_id']
        assert customer_data['created_at']
        assert isinstance(customer_data['orders_count'], int)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])