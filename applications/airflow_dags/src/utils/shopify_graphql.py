"""
Comprehensive Shopify GraphQL client for Airflow DAGs.

This module provides a robust GraphQL client for interacting with Shopify's Admin API:
- Authentication with Shopify access tokens
- Rate limiting and pagination
- Comprehensive GraphQL queries for products, customers, and orders
- Proper error handling and retry logic
- Support for cursor-based pagination
- Production-ready logging and monitoring

Example usage:
    client = ShopifyGraphQLClient()
    
    # Test connection
    if client.test_connection():
        print("Connected to Shopify successfully")
    
    # Get all product data
    products = client.get_all_product_data(limit=10)
    
    # Get product images
    images = client.get_product_images(product_id="gid://shopify/Product/123")
    
    # Get customers with orders
    customers = client.get_customers_with_orders(limit=50)

Authentication patterns based on curl examples:
    curl -X POST https://your-shop.myshopify.com/admin/api/2025-01/graphql.json \
      -H 'Content-Type: application/json' \
      -H 'X-Shopify-Access-Token: your-access-token' \
      -d '{"query": "query { shop { name } }"}'
"""

import time
import logging
from typing import Dict, Any, Optional, List, Union, Iterator
from datetime import datetime, timedelta
import json
import asyncio
from dataclasses import dataclass
from contextlib import asynccontextmanager

import aiohttp
import backoff
import structlog
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from gql.transport.exceptions import TransportError

from .config import get_shopify_config
from .query_loader import load_query

# Configure structured logging
logger = structlog.get_logger(__name__)


@dataclass
class ShopifyRateLimit:
    """Shopify rate limit information."""
    current_calls: int
    max_calls: int
    restore_rate: float
    remaining_calls: int
    
    @property
    def is_throttled(self) -> bool:
        """Check if we're being throttled."""
        return self.remaining_calls <= 5  # Leave buffer


@dataclass
class GraphQLError:
    """GraphQL error information."""
    message: str
    locations: Optional[List[Dict[str, Any]]] = None
    path: Optional[List[Union[str, int]]] = None
    extensions: Optional[Dict[str, Any]] = None


class ShopifyGraphQLClient:
    """
    Production-ready Shopify GraphQL API client with built-in rate limiting and error handling.
    
    Features:
    - Automatic rate limiting based on Shopify's cost analysis
    - Cursor-based pagination for large datasets
    - Comprehensive error handling with retry logic
    - Production-ready logging and monitoring
    - Support for both sync and async operations
    """
    
    # Shopify GraphQL API rate limits
    DEFAULT_RATE_LIMIT = 1000  # Default bucket size
    RESTORE_RATE = 50  # Points per second
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # Base delay in seconds
    
    def __init__(self, shop_name: Optional[str] = None, access_token: Optional[str] = None):
        """
        Initialize Shopify GraphQL client.
        
        Args:
            shop_name: Shopify shop name (without .myshopify.com)
            access_token: Shopify Admin API access token
        """
        if shop_name and access_token:
            self.shop_name = shop_name
            self.access_token = access_token
        else:
            config = get_shopify_config()
            self.shop_name = config['shop_name']
            self.access_token = config['access_token']
        
        self.shop_url = f"https://{self.shop_name}.myshopify.com/admin/api/2025-01/graphql.json"
        
        # Configure transport with authentication
        self.transport = RequestsHTTPTransport(
            url=self.shop_url,
            headers={
                'X-Shopify-Access-Token': self.access_token,
                'Content-Type': 'application/json',
            },
            retries=self.MAX_RETRIES,
            timeout=30,
        )
        
        self.client = Client(
            transport=self.transport,
            fetch_schema_from_transport=False  # Disable schema fetching for performance
        )
        
        # Rate limiting state
        self.rate_limit = ShopifyRateLimit(
            current_calls=0,
            max_calls=self.DEFAULT_RATE_LIMIT,
            restore_rate=self.RESTORE_RATE,
            remaining_calls=self.DEFAULT_RATE_LIMIT
        )
        self.last_call_time = 0.0
        
        logger.info(f"Initialized Shopify GraphQL client for shop: {self.shop_name}")
    
    def _update_rate_limit(self, extensions: Optional[Dict[str, Any]] = None) -> None:
        """Update rate limit information from response extensions."""
        if not extensions or 'cost' not in extensions:
            return
        
        cost_info = extensions['cost']
        throttle_status = cost_info.get('throttleStatus', {})
        
        if throttle_status:
            self.rate_limit.current_calls = throttle_status.get('currentlyAvailable', 0)
            self.rate_limit.max_calls = throttle_status.get('maximumAvailable', self.DEFAULT_RATE_LIMIT)
            self.rate_limit.restore_rate = throttle_status.get('restoreRate', self.RESTORE_RATE)
            self.rate_limit.remaining_calls = self.rate_limit.max_calls - self.rate_limit.current_calls
        
        logger.debug(
            "Rate limit updated",
            remaining=self.rate_limit.remaining_calls,
            max_calls=self.rate_limit.max_calls,
            restore_rate=self.rate_limit.restore_rate
        )
    
    def _calculate_delay(self, cost: int = 1) -> float:
        """Calculate delay needed to respect rate limits."""
        if self.rate_limit.remaining_calls > cost:
            return 0.0
        
        # Calculate time needed to restore enough points
        points_needed = cost - self.rate_limit.remaining_calls
        delay = points_needed / self.rate_limit.restore_rate
        
        logger.debug(f"Rate limit delay calculated: {delay:.2f} seconds")
        return delay
    
    @backoff.on_exception(
        backoff.expo,
        (TransportError, aiohttp.ClientError, Exception),
        max_tries=MAX_RETRIES,
        max_time=300,
        factor=2
    )
    def execute_query(
        self, 
        query: str, 
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query with rate limiting and error handling.
        
        Args:
            query: GraphQL query string
            variables: Query variables
            operation_name: Optional operation name for logging
            
        Returns:
            Query result data
            
        Raises:
            Exception: If query execution fails after retries
        """
        # Apply rate limiting
        delay = self._calculate_delay()
        if delay > 0:
            logger.info(f"Rate limiting: waiting {delay:.2f} seconds")
            time.sleep(delay)
        
        try:
            start_time = time.time()
            gql_query = gql(query)
            result = self.client.execute(gql_query, variable_values=variables)
            execution_time = time.time() - start_time
            
            # Update rate limit from response
            if hasattr(result, 'extensions'):
                self._update_rate_limit(result.extensions)
            
            logger.debug(
                "GraphQL query executed successfully",
                operation=operation_name,
                execution_time=f"{execution_time:.2f}s",
                query_length=len(query),
                variables=bool(variables)
            )
            
            # Check for GraphQL errors
            if 'errors' in result:
                errors = [GraphQLError(**error) for error in result['errors']]
                logger.error(
                    "GraphQL query returned errors",
                    operation=operation_name,
                    errors=[e.message for e in errors]
                )
                raise Exception(f"GraphQL errors: {[e.message for e in errors]}")
            
            return result
            
        except Exception as e:
            logger.error(
                "GraphQL query failed",
                operation=operation_name,
                error=str(e),
                query=query[:100] + "..." if len(query) > 100 else query,
                variables=variables
            )
            raise
    
    def get_all_product_data(
        self, 
        limit: int = 50, 
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive product data including variants, images, and metafields.
        
        This implements the exact GraphQL query structure for complete product data.
        
        Args:
            limit: Number of products to retrieve (max 250)
            cursor: Cursor for pagination
            
        Returns:
            Products data with pagination info
        """
        query = load_query("getAllProductData")
        
        variables = {"limit": min(limit, 250)}  # Shopify max limit
        if cursor:
            variables["cursor"] = cursor
        
        return self.execute_query(query, variables, "getAllProductData")
    
    def get_product_images(
        self, 
        product_id: str, 
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get detailed product image information.
        
        Args:
            product_id: Shopify product ID (e.g., "gid://shopify/Product/123")
            limit: Number of images to retrieve
            
        Returns:
            Product images data
        """
        query = load_query("getProductImagesById")
        
        variables = {
            "productId": product_id,
            "limit": limit
        }
        
        return self.execute_query(query, variables, "getProductImages")
    
    def get_customers_with_orders(
        self, 
        limit: int = 50, 
        cursor: Optional[str] = None,
        orders_limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get customers with their order history and detailed information.
        
        Args:
            limit: Number of customers to retrieve
            cursor: Cursor for pagination
            orders_limit: Number of orders to retrieve per customer
            
        Returns:
            Customers data with orders and pagination info
        """
        query = load_query("getCustomersWithOrders")
        
        variables = {
            "limit": min(limit, 250),  # Shopify max limit
            "ordersFirst": orders_limit
        }
        if cursor:
            variables["cursor"] = cursor
        
        return self.execute_query(query, variables, "getCustomersWithOrders")
    
    def get_all_product_images(
        self, 
        limit: int = 50, 
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get product images for all products using bulk query.
        
        Args:
            limit: Number of products to retrieve
            cursor: Cursor for pagination
            
        Returns:
            Product images data with pagination info
        """
        query = load_query("getProductImages")
        
        variables = {"limit": min(limit, 250)}  # Shopify max limit
        if cursor:
            variables["cursor"] = cursor
        
        return self.execute_query(query, variables, "getProductImages")
    
    def get_orders_with_details(
        self, 
        limit: int = 50, 
        cursor: Optional[str] = None,
        created_at_min: Optional[datetime] = None,
        created_at_max: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get orders with comprehensive details including line items and customer data.
        
        Args:
            limit: Number of orders to retrieve
            cursor: Cursor for pagination
            created_at_min: Minimum creation date filter
            created_at_max: Maximum creation date filter
            
        Returns:
            Orders data with pagination info
        """
        query = """
        query getOrdersWithDetails($limit: Int!, $cursor: String, $createdAtMin: DateTime, $createdAtMax: DateTime) {
            orders(first: $limit, after: $cursor, query: $query) {
                edges {
                    node {
                        id
                        name
                        email
                        createdAt
                        updatedAt
                        processedAt
                        closedAt
                        cancelled
                        cancelledAt
                        cancelReason
                        totalPriceV2 {
                            amount
                            currencyCode
                        }
                        subtotalPriceV2 {
                            amount
                            currencyCode
                        }
                        totalTaxV2 {
                            amount
                            currencyCode
                        }
                        totalShippingPriceV2 {
                            amount
                            currencyCode
                        }
                        financialStatus
                        fulfillmentStatus
                        tags
                        note
                        customer {
                            id
                            email
                            firstName
                            lastName
                            phone
                            acceptsMarketing
                            totalSpentV2 {
                                amount
                                currencyCode
                            }
                            numberOfOrders
                        }
                        lineItems(first: 100) {
                            edges {
                                node {
                                    id
                                    name
                                    quantity
                                    originalTotalSet {
                                        shopMoney {
                                            amount
                                            currencyCode
                                        }
                                    }
                                    variant {
                                        id
                                        title
                                        price
                                        sku
                                        product {
                                            id
                                            title
                                            handle
                                            productType
                                            vendor
                                        }
                                    }
                                }
                            }
                        }
                        shippingAddress {
                            firstName
                            lastName
                            company
                            address1
                            address2
                            city
                            province
                            country
                            zip
                            phone
                            name
                            provinceCode
                            countryCodeV2
                        }
                        billingAddress {
                            firstName
                            lastName
                            company
                            address1
                            address2
                            city
                            province
                            country
                            zip
                            phone
                            name
                            provinceCode
                            countryCodeV2
                        }
                    }
                    cursor
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
            }
        }
        """
        
        variables = {"limit": min(limit, 250)}  # Shopify max limit
        if cursor:
            variables["cursor"] = cursor
        
        # Build query string for date filters
        query_parts = []
        if created_at_min:
            query_parts.append(f"created_at:>={created_at_min.isoformat()}")
        if created_at_max:
            query_parts.append(f"created_at:<={created_at_max.isoformat()}")
        
        if query_parts:
            variables["query"] = " AND ".join(query_parts)
        
        return self.execute_query(query, variables, "getOrdersWithDetails")
    
    def get_shop_info(self) -> Dict[str, Any]:
        """
        Get shop information for connection testing and basic details.
        
        Returns:
            Shop information
        """
        query = """
        query getShopInfo {
            shop {
                id
                name
                myshopifyDomain
                description
                email
                phone
                primaryDomain {
                    id
                    url
                    host
                }
                currencyCode
                enabledPresentmentCurrencies
                timezoneAbbreviation
                ianaTimezone
                createdAt
                updatedAt
                plan {
                    displayName
                    partnerDevelopment
                    shopifyPlus
                }
                features {
                    avalaraAvatax
                    branding
                    captcha
                    captchaExternalDomains
                    dynamicRemarketing
                    giftCards
                    harmonizedSystemCode
                    internationalDomains
                    internationalPriceOverrides
                    internationalPriceRules
                    legacySubscriptionGatewayEnabled
                    liveChat
                    multiLocation
                    onboardingVisual
                    paypalExpressSubscriptionGateway
                    reports
                    sellsSubscriptions
                    skipBillingAddress
                    skipShippingAddress
                    smsMarketing
                    usingShopifyBalance
                }
            }
        }
        """
        
        return self.execute_query(query, operation_name="getShopInfo")
    
    def test_connection(self) -> bool:
        """
        Test the Shopify API connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            result = self.get_shop_info()
            shop_info = result.get('shop', {})
            shop_name = shop_info.get('name')
            
            if shop_name:
                logger.info(f"Shopify connection test successful for shop: {shop_name}")
                return True
            else:
                logger.error("Shopify connection test failed: no shop data returned")
                return False
                
        except Exception as e:
            logger.error(f"Shopify connection test failed: {e}")
            return False
    
    def paginate_all_products(self, batch_size: int = 50) -> Iterator[Dict[str, Any]]:
        """
        Generator to paginate through all products in the store.
        
        Args:
            batch_size: Number of products to fetch per request
            
        Yields:
            Product data dictionaries
        """
        cursor = None
        has_next_page = True
        
        while has_next_page:
            try:
                result = self.get_all_product_data(limit=batch_size, cursor=cursor)
                products = result.get('products', {})
                edges = products.get('edges', [])
                
                for edge in edges:
                    yield edge['node']
                
                # Check pagination
                page_info = products.get('pageInfo', {})
                has_next_page = page_info.get('hasNextPage', False)
                cursor = page_info.get('endCursor')
                
                if not has_next_page:
                    break
                    
            except Exception as e:
                logger.error(f"Error during product pagination: {e}")
                break
    
    def paginate_all_customers(self, batch_size: int = 50) -> Iterator[Dict[str, Any]]:
        """
        Generator to paginate through all customers in the store.
        
        Args:
            batch_size: Number of customers to fetch per request
            
        Yields:
            Customer data dictionaries
        """
        cursor = None
        has_next_page = True
        
        while has_next_page:
            try:
                result = self.get_customers_with_orders(limit=batch_size, cursor=cursor)
                customers = result.get('customers', {})
                edges = customers.get('edges', [])
                
                for edge in edges:
                    yield edge['node']
                
                # Check pagination
                page_info = customers.get('pageInfo', {})
                has_next_page = page_info.get('hasNextPage', False)
                cursor = page_info.get('endCursor')
                
                if not has_next_page:
                    break
                    
            except Exception as e:
                logger.error(f"Error during customer pagination: {e}")
                break
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status.
        
        Returns:
            Rate limit information
        """
        return {
            "remaining_calls": self.rate_limit.remaining_calls,
            "max_calls": self.rate_limit.max_calls,
            "restore_rate": self.rate_limit.restore_rate,
            "is_throttled": self.rate_limit.is_throttled,
            "current_calls": self.rate_limit.current_calls
        }
    
    def __str__(self) -> str:
        """String representation of the client."""
        return f"ShopifyGraphQLClient(shop={self.shop_name}, rate_limit={self.rate_limit.remaining_calls}/{self.rate_limit.max_calls})"
    
    def __repr__(self) -> str:
        """Detailed representation of the client."""
        return f"ShopifyGraphQLClient(shop_name='{self.shop_name}', shop_url='{self.shop_url}', rate_limit={self.rate_limit})"


# Example usage and testing
if __name__ == "__main__":
    # This section is for testing and demonstration
    import os
    
    # Set up test environment
    os.environ['SHOPIFY_SHOP_NAME'] = 'your-test-shop'
    os.environ['SHOPIFY_ACCESS_TOKEN'] = 'your-test-token'
    
    # Initialize client
    client = ShopifyGraphQLClient()
    
    # Test connection
    if client.test_connection():
        print("✓ Connection successful")
        
        # Get shop info
        shop_info = client.get_shop_info()
        print(f"Shop: {shop_info.get('shop', {}).get('name', 'Unknown')}")
        
        # Test rate limit status
        rate_limit = client.get_rate_limit_status()
        print(f"Rate limit: {rate_limit}")
        
        # Get first 5 products
        products = client.get_all_product_data(limit=5)
        product_count = len(products.get('products', {}).get('edges', []))
        print(f"Retrieved {product_count} products")
        
        # Get first 5 customers
        customers = client.get_customers_with_orders(limit=5)
        customer_count = len(customers.get('customers', {}).get('edges', []))
        print(f"Retrieved {customer_count} customers")
        
    else:
        print("✗ Connection failed")