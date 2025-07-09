"""
Shopify GraphQL client for Airflow DAGs.

Provides a GraphQL client for interacting with Shopify's Admin API:
- GraphQL query execution
- Rate limiting and retry logic
- Error handling and logging
- Data transformation utilities
"""

import time
from typing import Dict, Any, Optional, List
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import structlog

from .config import get_shopify_config

logger = structlog.get_logger(__name__)


class ShopifyGraphQLClient:
    """
    Shopify GraphQL API client with built-in rate limiting and error handling.
    """
    
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
        transport = RequestsHTTPTransport(
            url=self.shop_url,
            headers={
                'X-Shopify-Access-Token': self.access_token,
                'Content-Type': 'application/json',
            },
            retries=3,
        )
        
        self.client = Client(transport=transport, fetch_schema_from_transport=True)
        
        # Rate limiting configuration
        self.max_calls_per_second = 2  # Shopify REST API limit
        self.last_call_time = 0
        
        logger.info(f"Initialized Shopify GraphQL client for shop: {self.shop_name}")
    
    def _rate_limit(self):
        """Apply rate limiting between API calls."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        min_interval = 1.0 / self.max_calls_per_second
        
        if time_since_last_call < min_interval:
            sleep_time = min_interval - time_since_last_call
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()
    
    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query with rate limiting and error handling.
        
        Args:
            query: GraphQL query string
            variables: Query variables
            
        Returns:
            Query result data
            
        Raises:
            Exception: If query execution fails
        """
        self._rate_limit()
        
        try:
            gql_query = gql(query)
            result = self.client.execute(gql_query, variable_values=variables)
            
            logger.debug("GraphQL query executed successfully", 
                        query_length=len(query),
                        variables=variables)
            
            return result
            
        except Exception as e:
            logger.error(f"GraphQL query failed: {e}", 
                        query=query[:100] + "..." if len(query) > 100 else query,
                        variables=variables)
            raise
    
    def get_customers(self, limit: int = 50, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Get customers with pagination support.
        
        Args:
            limit: Number of customers to retrieve
            cursor: Cursor for pagination
            
        Returns:
            Customers data with pagination info
        """
        query = """
        query getCustomers($limit: Int!, $cursor: String) {
            customers(first: $limit, after: $cursor) {
                edges {
                    node {
                        id
                        email
                        firstName
                        lastName
                        createdAt
                        updatedAt
                        ordersCount
                        totalSpent
                        tags
                        phone
                        acceptsMarketing
                        acceptsMarketingUpdatedAt
                        addresses {
                            address1
                            address2
                            city
                            province
                            zip
                            country
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
        
        variables = {"limit": limit}
        if cursor:
            variables["cursor"] = cursor
        
        return self.execute_query(query, variables)
    
    def get_orders(self, limit: int = 50, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Get orders with pagination support.
        
        Args:
            limit: Number of orders to retrieve
            cursor: Cursor for pagination
            
        Returns:
            Orders data with pagination info
        """
        query = """
        query getOrders($limit: Int!, $cursor: String) {
            orders(first: $limit, after: $cursor) {
                edges {
                    node {
                        id
                        name
                        email
                        createdAt
                        updatedAt
                        processedAt
                        totalPrice
                        subtotalPrice
                        totalTax
                        currencyCode
                        financialStatus
                        fulfillmentStatus
                        tags
                        customer {
                            id
                            email
                            firstName
                            lastName
                        }
                        lineItems(first: 100) {
                            edges {
                                node {
                                    id
                                    title
                                    quantity
                                    price
                                    product {
                                        id
                                        title
                                        handle
                                    }
                                    variant {
                                        id
                                        title
                                        sku
                                    }
                                }
                            }
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
        
        variables = {"limit": limit}
        if cursor:
            variables["cursor"] = cursor
        
        return self.execute_query(query, variables)
    
    def get_products(self, limit: int = 50, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Get products with pagination support.
        
        Args:
            limit: Number of products to retrieve
            cursor: Cursor for pagination
            
        Returns:
            Products data with pagination info
        """
        query = """
        query getProducts($limit: Int!, $cursor: String) {
            products(first: $limit, after: $cursor) {
                edges {
                    node {
                        id
                        title
                        handle
                        description
                        createdAt
                        updatedAt
                        status
                        productType
                        vendor
                        tags
                        variants(first: 100) {
                            edges {
                                node {
                                    id
                                    title
                                    sku
                                    price
                                    inventoryQuantity
                                    weight
                                    weightUnit
                                }
                            }
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
        
        variables = {"limit": limit}
        if cursor:
            variables["cursor"] = cursor
        
        return self.execute_query(query, variables)
    
    def test_connection(self) -> bool:
        """
        Test the Shopify API connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            query = """
            query {
                shop {
                    name
                    myshopifyDomain
                }
            }
            """
            
            result = self.execute_query(query)
            shop_name = result.get('shop', {}).get('name')
            
            logger.info(f"Shopify connection test successful for shop: {shop_name}")
            return True
            
        except Exception as e:
            logger.error(f"Shopify connection test failed: {e}")
            return False