"""
Custom Shopify Hook for Airflow 3.0.2

This hook provides a standardized interface for interacting with Shopify's GraphQL API
in Airflow DAGs, with built-in connection management, rate limiting, and error handling.
"""

import time
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta

from airflow.hooks.base import BaseHook
from airflow.exceptions import AirflowException
from airflow.models import Connection
from airflow.configuration import conf

import requests
import structlog
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = structlog.get_logger(__name__)


class ShopifyHook(BaseHook):
    """
    Custom Shopify Hook for Airflow 3.0.2
    
    Provides connection management and GraphQL API interaction capabilities
    for Shopify data synchronization workflows.
    """
    
    conn_name_attr = "shopify_conn_id"
    default_conn_name = "shopify_default"
    conn_type = "shopify"
    hook_name = "Shopify"
    
    def __init__(
        self,
        shopify_conn_id: str = default_conn_name,
        api_version: str = "2023-10",
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit_calls_per_second: float = 2.0,
        enable_metrics: bool = True,
        enable_caching: bool = False,
        cache_ttl: int = 300,  # 5 minutes
        **kwargs
    ):
        """
        Initialize Shopify Hook
        
        Args:
            shopify_conn_id: Airflow connection ID for Shopify
            api_version: Shopify API version
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            rate_limit_calls_per_second: Rate limit for API calls
        """
        super().__init__(**kwargs)
        self.shopify_conn_id = shopify_conn_id
        self.api_version = api_version
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_calls_per_second = rate_limit_calls_per_second
        self.enable_metrics = enable_metrics
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl
        
        # Initialize connection properties
        self._shop_name: Optional[str] = None
        self._access_token: Optional[str] = None
        self._session: Optional[requests.Session] = None
        self._last_call_time: float = 0
        
        # GraphQL endpoint will be set after connection is established
        self._graphql_endpoint: Optional[str] = None
        
        # Performance metrics tracking
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "rate_limit_hits": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Simple in-memory cache (for development/testing)
        self._cache = {} if enable_caching else None
        
        logger.info(
            f"Initialized ShopifyHook with connection: {shopify_conn_id}, "
            f"API version: {api_version}, metrics: {enable_metrics}, caching: {enable_caching}"
        )
    
    def get_connection(self, conn_id: str) -> Connection:
        """Get Airflow connection for Shopify"""
        return super().get_connection(conn_id)
    
    def get_conn(self) -> requests.Session:
        """
        Get or create HTTP session for Shopify API
        
        Returns:
            Configured requests session
        """
        if self._session is None:
            self._setup_connection()
        return self._session
    
    def _setup_connection(self) -> None:
        """Setup connection to Shopify API"""
        try:
            conn = self.get_connection(self.shopify_conn_id)
            
            # Extract connection details
            self._shop_name = conn.host
            self._access_token = conn.password
            
            if not self._shop_name or not self._access_token:
                raise AirflowException(
                    f"Shopify connection '{self.shopify_conn_id}' missing required fields. "
                    "Host should be shop name, Password should be access token."
                )
            
            # Set GraphQL endpoint
            self._graphql_endpoint = f"https://{self._shop_name}.myshopify.com/admin/api/{self.api_version}/graphql.json"
            
            # Setup session with retry strategy
            self._session = requests.Session()
            
            # Configure retry strategy
            retry_strategy = Retry(
                total=self.max_retries,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET", "POST"]
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
            
            # Set default headers
            self._session.headers.update({
                "X-Shopify-Access-Token": self._access_token,
                "Content-Type": "application/json",
                "User-Agent": "PXY6-Airflow-Hook/1.0"
            })
            
            logger.info(f"Successfully connected to Shopify shop: {self._shop_name}")
            
        except Exception as e:
            logger.error(f"Failed to setup Shopify connection: {str(e)}")
            raise AirflowException(f"Failed to setup Shopify connection: {str(e)}")
    
    def _apply_rate_limit(self) -> None:
        """Apply rate limiting between API calls"""
        if self.rate_limit_calls_per_second <= 0:
            return
        
        current_time = time.time()
        time_since_last_call = current_time - self._last_call_time
        min_interval = 1.0 / self.rate_limit_calls_per_second
        
        if time_since_last_call < min_interval:
            sleep_time = min_interval - time_since_last_call
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self._last_call_time = time.time()
    
    def test_connection(self) -> bool:
        """
        Test connection to Shopify API
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            query = """
            query {
                shop {
                    name
                    myshopifyDomain
                    plan {
                        displayName
                    }
                }
            }
            """
            
            result = self.execute_graphql(query)
            shop_data = result.get("data", {}).get("shop", {})
            
            if shop_data:
                logger.info(
                    f"Connection test successful - Shop: {shop_data.get('name')}, "
                    f"Domain: {shop_data.get('myshopifyDomain')}, "
                    f"Plan: {shop_data.get('plan', {}).get('displayName')}"
                )
                return True
            else:
                logger.error("Connection test failed - No shop data returned")
                return False
        
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def execute_graphql(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        use_cache: bool = None
    ) -> Dict[str, Any]:
        """
        Execute GraphQL query against Shopify API
        
        Args:
            query: GraphQL query string
            variables: Query variables
            operation_name: Optional operation name
            
        Returns:
            GraphQL response data
            
        Raises:
            AirflowException: If query execution fails
        """
        # Check cache first if enabled
        cache_key = None
        if (use_cache is None and self.enable_caching) or use_cache:
            cache_key = self._generate_cache_key(query, variables)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                if self.enable_metrics:
                    self._metrics["cache_hits"] += 1
                logger.debug(f"Cache hit for operation: {operation_name}")
                return cached_result
            elif self.enable_metrics:
                self._metrics["cache_misses"] += 1
        
        self._apply_rate_limit()
        
        session = self.get_conn()
        
        # Track metrics
        if self.enable_metrics:
            self._metrics["total_requests"] += 1
        
        payload = {
            "query": query,
            "variables": variables or {},
        }
        
        if operation_name:
            payload["operationName"] = operation_name
        
        try:
            logger.debug(f"Executing GraphQL query: {query[:100]}...")
            
            response = session.post(
                self._graphql_endpoint,
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            result = response.json()
            
            # Check for GraphQL errors
            if "errors" in result:
                error_messages = [error.get("message", "Unknown error") for error in result["errors"]]
                raise AirflowException(f"GraphQL errors: {', '.join(error_messages)}")
            
            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 10))
                logger.warning(f"Rate limited, waiting {retry_after} seconds")
                time.sleep(retry_after)
                return self.execute_graphql(query, variables, operation_name)
            
            logger.debug(f"GraphQL query executed successfully")
            
            # Cache the result if caching is enabled
            if cache_key and self.enable_caching:
                self._store_in_cache(cache_key, result)
            
            # Update metrics
            if self.enable_metrics:
                self._metrics["successful_requests"] += 1
                self._update_avg_response_time(execution_time)
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {str(e)}")
            raise AirflowException(f"HTTP request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise AirflowException(f"Failed to parse JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during GraphQL execution: {str(e)}")
            
            # Update metrics
            if self.enable_metrics:
                self._metrics["failed_requests"] += 1
            
            raise AirflowException(f"Unexpected error during GraphQL execution: {str(e)}")
    
    def get_paginated_data(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        data_path: List[str] = None,
        max_pages: Optional[int] = None,
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get paginated data from Shopify GraphQL API
        
        Args:
            query: GraphQL query with pagination support
            variables: Query variables
            data_path: Path to data in response (e.g., ['data', 'products', 'edges'])
            max_pages: Maximum number of pages to fetch
            page_size: Items per page
            
        Returns:
            List of all fetched items
        """
        all_items = []
        cursor = None
        page_count = 0
        
        if data_path is None:
            data_path = ["data"]
        
        try:
            while True:
                page_count += 1
                
                # Update variables with cursor and page size
                query_vars = (variables or {}).copy()
                query_vars.update({
                    "first": page_size,
                    "after": cursor
                })
                
                logger.debug(f"Fetching page {page_count} with cursor: {cursor}")
                
                result = self.execute_graphql(query, query_vars)
                
                # Navigate to data using path
                data = result
                for path_part in data_path:
                    data = data.get(path_part, {})
                
                # Extract items from edges
                edges = data.get("edges", [])
                if not edges:
                    logger.info(f"No more data found at page {page_count}")
                    break
                
                # Extract nodes from edges
                page_items = [edge["node"] for edge in edges]
                all_items.extend(page_items)
                
                logger.info(f"Page {page_count}: fetched {len(page_items)} items")
                
                # Check pagination
                page_info = data.get("pageInfo", {})
                if not page_info.get("hasNextPage", False):
                    logger.info(f"Reached last page at page {page_count}")
                    break
                
                cursor = page_info.get("endCursor")
                
                # Check max pages limit
                if max_pages and page_count >= max_pages:
                    logger.info(f"Reached max pages limit: {max_pages}")
                    break
                
        except Exception as e:
            logger.error(f"Error during pagination at page {page_count}: {str(e)}")
            raise AirflowException(f"Error during pagination at page {page_count}: {str(e)}")
        
        logger.info(f"Successfully fetched {len(all_items)} items across {page_count} pages")
        return all_items
    
    def get_shop_info(self) -> Dict[str, Any]:
        """
        Get shop information
        
        Returns:
            Shop information dictionary
        """
        query = """
        query {
            shop {
                id
                name
                myshopifyDomain
                email
                description
                createdAt
                updatedAt
                currencyCode
                weightUnit
                plan {
                    displayName
                    partnerDevelopment
                    shopifyPlus
                }
                primaryDomain {
                    url
                    sslEnabled
                }
            }
        }
        """
        
        result = self.execute_graphql(query)
        return result.get("data", {}).get("shop", {})
    
    def get_webhook_subscriptions(self) -> List[Dict[str, Any]]:
        """
        Get webhook subscriptions
        
        Returns:
            List of webhook subscriptions
        """
        query = """
        query {
            webhookSubscriptions(first: 100) {
                edges {
                    node {
                        id
                        topic
                        callbackUrl
                        createdAt
                        updatedAt
                        format
                        includeFields
                        metafieldNamespaces
                    }
                }
            }
        }
        """
        
        result = self.execute_graphql(query)
        edges = result.get("data", {}).get("webhookSubscriptions", {}).get("edges", [])
        return [edge["node"] for edge in edges]
    
    def get_cost_analysis(self) -> Dict[str, Any]:
        """
        Get API cost analysis for the last executed query
        
        Returns:
            Cost analysis data
        """
        query = """
        query {
            cost {
                requestedQueryCost
                actualQueryCost
                throttleStatus {
                    maximumAvailable
                    currentlyAvailable
                    restoreRate
                }
            }
        }
        """
        
        result = self.execute_graphql(query)
        return result.get("data", {}).get("cost", {})
    
    def close(self) -> None:
        """Close the session"""
        if self._session:
            self._session.close()
            self._session = None
            logger.info("Shopify session closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def get_customers_with_orders_query(
        self,
        limit: int = 50,
        cursor: Optional[str] = None,
        include_customer_journey: bool = True
    ) -> str:
        """
        Get the getCustomersWithOrders GraphQL query for comprehensive customer data
        
        Args:
            limit: Number of customers to retrieve
            cursor: Cursor for pagination
            include_customer_journey: Whether to include customer journey data
            
        Returns:
            GraphQL query string
        """
        customer_journey_fields = ""
        if include_customer_journey:
            customer_journey_fields = """
                customerJourneySummary {
                    customerOrderIndex
                    daysToConversion
                    firstVisit {
                        id
                        landingPage
                        landingPageHtml
                        referrer
                        referrerName
                        source
                        sourceDescription
                        sourceType
                        utmParameters {
                            campaign
                            content
                            medium
                            source
                            term
                        }
                    }
                    lastVisit {
                        id
                        landingPage
                        landingPageHtml
                        referrer
                        referrerName
                        source
                        sourceDescription
                        sourceType
                        utmParameters {
                            campaign
                            content
                            medium
                            source
                            term
                        }
                    }
                    momentsCount
                    ready
                }
            """
        
        query = f"""
        query getCustomersWithOrders($first: Int!, $after: String) {{
            customers(first: $first, after: $after) {{
                edges {{
                    node {{
                        id
                        email
                        firstName
                        lastName
                        phone
                        createdAt
                        updatedAt
                        acceptsMarketing
                        acceptsMarketingUpdatedAt
                        state
                        tags
                        note
                        verifiedEmail
                        taxExempt
                        totalSpentV2 {{
                            amount
                            currencyCode
                        }}
                        numberOfOrders
                        addresses {{
                            id
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
                            default
                        }}
                        orders(first: 50) {{
                            edges {{
                                node {{
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
                                    totalPriceV2 {{
                                        amount
                                        currencyCode
                                    }}
                                    subtotalPriceV2 {{
                                        amount
                                        currencyCode
                                    }}
                                    totalTaxV2 {{
                                        amount
                                        currencyCode
                                    }}
                                    totalShippingPriceV2 {{
                                        amount
                                        currencyCode
                                    }}
                                    financialStatus
                                    fulfillmentStatus
                                    tags
                                    note
                                    {customer_journey_fields}
                                    lineItems(first: 100) {{
                                        edges {{
                                            node {{
                                                id
                                                name
                                                quantity
                                                originalTotalSet {{
                                                    shopMoney {{
                                                        amount
                                                        currencyCode
                                                    }}
                                                }}
                                                variant {{
                                                    id
                                                    title
                                                    price
                                                    sku
                                                    product {{
                                                        id
                                                        title
                                                        handle
                                                        productType
                                                        vendor
                                                    }}
                                                }}
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }}
                        metafields(first: 100) {{
                            edges {{
                                node {{
                                    id
                                    namespace
                                    key
                                    value
                                    type
                                    description
                                    createdAt
                                    updatedAt
                                }}
                            }}
                        }}
                    }}
                    cursor
                }}
                pageInfo {{
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }}
            }}
        }}
        """
        
        return query
    
    def get_all_product_data_query(
        self,
        limit: int = 50,
        cursor: Optional[str] = None,
        include_variants: bool = True,
        include_images: bool = True,
        include_metafields: bool = True,
        include_collections: bool = True,
        include_inventory: bool = True
    ) -> str:
        """
        Get the getAllProductData GraphQL query for comprehensive product data
        
        Args:
            limit: Number of products to retrieve
            cursor: Cursor for pagination
            include_variants: Whether to include variant data
            include_images: Whether to include image data
            include_metafields: Whether to include metafield data
            include_collections: Whether to include collection data
            include_inventory: Whether to include inventory data
            
        Returns:
            GraphQL query string
        """
        variants_fields = ""
        if include_variants:
            inventory_fields = ""
            if include_inventory:
                inventory_fields = """
                    inventoryItem {
                        id
                        tracked
                        requiresShipping
                        inventoryLevels(first: 10) {
                            edges {
                                node {
                                    id
                                    available
                                    location {
                                        id
                                        name
                                    }
                                }
                            }
                        }
                    }
                """
            
            variants_fields = f"""
                variants(first: 100) {{
                    edges {{
                        node {{
                            id
                            title
                            sku
                            barcode
                            price
                            compareAtPrice
                            inventoryQuantity
                            weight
                            weightUnit
                            availableForSale
                            createdAt
                            updatedAt
                            selectedOptions {{
                                name
                                value
                            }}
                            {inventory_fields}
                        }}
                    }}
                }}
            """
        
        images_fields = ""
        if include_images:
            images_fields = """
                images(first: 50) {
                    edges {
                        node {
                            id
                            url
                            altText
                            width
                            height
                            originalSrc
                            transformedSrc
                        }
                    }
                }
            """
        
        metafields_fields = ""
        if include_metafields:
            metafields_fields = """
                metafields(first: 100) {
                    edges {
                        node {
                            id
                            namespace
                            key
                            value
                            type
                            description
                            createdAt
                            updatedAt
                        }
                    }
                }
            """
        
        collections_fields = ""
        if include_collections:
            collections_fields = """
                collections(first: 10) {
                    edges {
                        node {
                            id
                            title
                            handle
                        }
                    }
                }
            """
        
        query = f"""
        query getAllProductData($first: Int!, $after: String) {{
            products(first: $first, after: $after) {{
                edges {{
                    node {{
                        id
                        title
                        handle
                        description
                        descriptionHtml
                        productType
                        vendor
                        tags
                        status
                        createdAt
                        updatedAt
                        publishedAt
                        totalInventory
                        onlineStoreUrl
                        seo {{
                            title
                            description
                        }}
                        options {{
                            id
                            name
                            values
                            position
                        }}
                        {variants_fields}
                        {images_fields}
                        {metafields_fields}
                        {collections_fields}
                    }}
                    cursor
                }}
                pageInfo {{
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }}
            }}
        }}
        """
        
        return query
    
    def get_product_images_query(
        self,
        product_id: str,
        limit: int = 50
    ) -> str:
        """
        Get the getProductImages GraphQL query for detailed product image data
        
        Args:
            product_id: Shopify product ID
            limit: Number of images to retrieve
            
        Returns:
            GraphQL query string
        """
        query = f"""
        query getProductImages($productId: ID!, $first: Int!) {{
            product(id: $productId) {{
                id
                title
                images(first: $first) {{
                    edges {{
                        node {{
                            id
                            url
                            altText
                            width
                            height
                            originalSrc
                            transformedSrc
                            createdAt
                            updatedAt
                        }}
                    }}
                    pageInfo {{
                        hasNextPage
                        hasPreviousPage
                        startCursor
                        endCursor
                    }}
                }}
            }}
        }}
        """
        
        return query
    
    def get_customers_with_orders_data(
        self,
        limit: int = 50,
        cursor: Optional[str] = None,
        include_customer_journey: bool = True
    ) -> Dict[str, Any]:
        """
        Execute getCustomersWithOrders query and return data
        
        Args:
            limit: Number of customers to retrieve
            cursor: Cursor for pagination
            include_customer_journey: Whether to include customer journey data
            
        Returns:
            Query result data
        """
        query = self.get_customers_with_orders_query(
            limit=limit,
            cursor=cursor,
            include_customer_journey=include_customer_journey
        )
        
        variables = {"first": limit}
        if cursor:
            variables["after"] = cursor
        
        return self.execute_graphql(query, variables, "getCustomersWithOrders")
    
    def get_all_product_data(
        self,
        limit: int = 50,
        cursor: Optional[str] = None,
        include_variants: bool = True,
        include_images: bool = True,
        include_metafields: bool = True,
        include_collections: bool = True,
        include_inventory: bool = True
    ) -> Dict[str, Any]:
        """
        Execute getAllProductData query and return data
        
        Args:
            limit: Number of products to retrieve
            cursor: Cursor for pagination
            include_variants: Whether to include variant data
            include_images: Whether to include image data
            include_metafields: Whether to include metafield data
            include_collections: Whether to include collection data
            include_inventory: Whether to include inventory data
            
        Returns:
            Query result data
        """
        query = self.get_all_product_data_query(
            limit=limit,
            cursor=cursor,
            include_variants=include_variants,
            include_images=include_images,
            include_metafields=include_metafields,
            include_collections=include_collections,
            include_inventory=include_inventory
        )
        
        variables = {"first": limit}
        if cursor:
            variables["after"] = cursor
        
        return self.execute_graphql(query, variables, "getAllProductData")
    
    def get_product_images_data(
        self,
        product_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Execute getProductImages query and return data
        
        Args:
            product_id: Shopify product ID
            limit: Number of images to retrieve
            
        Returns:
            Query result data
        """
        query = self.get_product_images_query(product_id, limit)
        
        variables = {
            "productId": product_id,
            "first": limit
        }
        
        return self.execute_graphql(query, variables, "getProductImages")
    
    def _generate_cache_key(self, query: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """Generate a cache key for the query and variables"""
        import hashlib
        
        # Create a hash of the query and variables
        content = query + str(sorted((variables or {}).items()))
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get result from cache if available and not expired"""
        if not self._cache or cache_key not in self._cache:
            return None
        
        cached_item = self._cache[cache_key]
        
        # Check if cache has expired
        if time.time() - cached_item["timestamp"] > self.cache_ttl:
            del self._cache[cache_key]
            return None
        
        return cached_item["data"]
    
    def _store_in_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Store result in cache with timestamp"""
        if not self._cache:
            return
        
        self._cache[cache_key] = {
            "data": data,
            "timestamp": time.time()
        }
        
        # Simple cache cleanup - remove old entries if cache gets too big
        if len(self._cache) > 100:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest_key]
    
    def _update_avg_response_time(self, execution_time: float) -> None:
        """Update average response time metric"""
        if not self.enable_metrics:
            return
        
        total_requests = self._metrics["total_requests"]
        current_avg = self._metrics["avg_response_time"]
        
        # Calculate new average
        self._metrics["avg_response_time"] = (
            (current_avg * (total_requests - 1) + execution_time) / total_requests
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the hook
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.enable_metrics:
            return {"metrics_disabled": True}
        
        metrics = self._metrics.copy()
        
        # Calculate additional metrics
        if metrics["total_requests"] > 0:
            metrics["success_rate"] = metrics["successful_requests"] / metrics["total_requests"]
            metrics["failure_rate"] = metrics["failed_requests"] / metrics["total_requests"]
        else:
            metrics["success_rate"] = 0.0
            metrics["failure_rate"] = 0.0
        
        if self.enable_caching:
            total_cache_requests = metrics["cache_hits"] + metrics["cache_misses"]
            if total_cache_requests > 0:
                metrics["cache_hit_rate"] = metrics["cache_hits"] / total_cache_requests
            else:
                metrics["cache_hit_rate"] = 0.0
        
        return metrics
    
    def reset_metrics(self) -> None:
        """Reset performance metrics"""
        if self.enable_metrics:
            self._metrics = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "avg_response_time": 0.0,
                "rate_limit_hits": 0,
                "cache_hits": 0,
                "cache_misses": 0
            }
    
    def clear_cache(self) -> None:
        """Clear the cache"""
        if self._cache:
            self._cache.clear()
            logger.info("Cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information"""
        if not self.enable_caching or not self._cache:
            return {"caching_disabled": True}
        
        return {
            "cache_size": len(self._cache),
            "cache_ttl": self.cache_ttl,
            "oldest_entry_age": min(
                time.time() - item["timestamp"] for item in self._cache.values()
            ) if self._cache else 0
        }
    
    def paginate_customers_with_orders(
        self,
        batch_size: int = 50,
        max_pages: Optional[int] = None,
        include_customer_journey: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Paginate through all customers with orders
        
        Args:
            batch_size: Number of customers to fetch per request
            max_pages: Maximum number of pages to fetch
            include_customer_journey: Whether to include customer journey data
            
        Returns:
            List of all customer data
        """
        all_customers = []
        cursor = None
        page_count = 0
        
        while True:
            page_count += 1
            logger.debug(f"Fetching page {page_count} of customers with orders")
            
            try:
                result = self.get_customers_with_orders_data(
                    limit=batch_size,
                    cursor=cursor,
                    include_customer_journey=include_customer_journey
                )
                
                customers = result.get("customers", {})
                edges = customers.get("edges", [])
                
                if not edges:
                    logger.info(f"No more customers found at page {page_count}")
                    break
                
                # Extract customer nodes
                page_customers = [edge["node"] for edge in edges]
                all_customers.extend(page_customers)
                
                logger.info(f"Page {page_count}: fetched {len(page_customers)} customers")
                
                # Check pagination
                page_info = customers.get("pageInfo", {})
                if not page_info.get("hasNextPage", False):
                    logger.info(f"Reached last page at page {page_count}")
                    break
                
                cursor = page_info.get("endCursor")
                
                # Check max pages limit
                if max_pages and page_count >= max_pages:
                    logger.info(f"Reached max pages limit: {max_pages}")
                    break
                    
            except Exception as e:
                logger.error(f"Error during customer pagination at page {page_count}: {str(e)}")
                break
        
        logger.info(f"Successfully fetched {len(all_customers)} customers across {page_count} pages")
        return all_customers
    
    def paginate_all_product_data(
        self,
        batch_size: int = 50,
        max_pages: Optional[int] = None,
        include_variants: bool = True,
        include_images: bool = True,
        include_metafields: bool = True,
        include_collections: bool = True,
        include_inventory: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Paginate through all products with comprehensive data
        
        Args:
            batch_size: Number of products to fetch per request
            max_pages: Maximum number of pages to fetch
            include_variants: Whether to include variant data
            include_images: Whether to include image data
            include_metafields: Whether to include metafield data
            include_collections: Whether to include collection data
            include_inventory: Whether to include inventory data
            
        Returns:
            List of all product data
        """
        all_products = []
        cursor = None
        page_count = 0
        
        while True:
            page_count += 1
            logger.debug(f"Fetching page {page_count} of products")
            
            try:
                result = self.get_all_product_data(
                    limit=batch_size,
                    cursor=cursor,
                    include_variants=include_variants,
                    include_images=include_images,
                    include_metafields=include_metafields,
                    include_collections=include_collections,
                    include_inventory=include_inventory
                )
                
                products = result.get("products", {})
                edges = products.get("edges", [])
                
                if not edges:
                    logger.info(f"No more products found at page {page_count}")
                    break
                
                # Extract product nodes
                page_products = [edge["node"] for edge in edges]
                all_products.extend(page_products)
                
                logger.info(f"Page {page_count}: fetched {len(page_products)} products")
                
                # Check pagination
                page_info = products.get("pageInfo", {})
                if not page_info.get("hasNextPage", False):
                    logger.info(f"Reached last page at page {page_count}")
                    break
                
                cursor = page_info.get("endCursor")
                
                # Check max pages limit
                if max_pages and page_count >= max_pages:
                    logger.info(f"Reached max pages limit: {max_pages}")
                    break
                    
            except Exception as e:
                logger.error(f"Error during product pagination at page {page_count}: {str(e)}")
                break
        
        logger.info(f"Successfully fetched {len(all_products)} products across {page_count} pages")
        return all_products
    
    def get_incremental_updates(
        self,
        data_type: str,
        updated_since: datetime,
        batch_size: int = 50,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get incremental updates for a specific data type since a given time
        
        Args:
            data_type: Type of data to fetch (products, customers, orders)
            updated_since: Fetch data updated since this time
            batch_size: Number of items to fetch per request
            max_pages: Maximum number of pages to fetch
            
        Returns:
            List of updated items
        """
        if data_type == "customers":
            all_customers = self.paginate_customers_with_orders(
                batch_size=batch_size,
                max_pages=max_pages
            )
            
            # Filter for items updated since the given time
            filtered_customers = []
            for customer in all_customers:
                try:
                    updated_at = datetime.fromisoformat(
                        customer.get("updatedAt", "").replace("Z", "+00:00")
                    )
                    if updated_at >= updated_since:
                        filtered_customers.append(customer)
                except (ValueError, TypeError):
                    # Include items if we can't parse the date
                    filtered_customers.append(customer)
            
            logger.info(f"Filtered {len(filtered_customers)} customers updated since {updated_since}")
            return filtered_customers
        
        elif data_type == "products":
            all_products = self.paginate_all_product_data(
                batch_size=batch_size,
                max_pages=max_pages
            )
            
            # Filter for items updated since the given time
            filtered_products = []
            for product in all_products:
                try:
                    updated_at = datetime.fromisoformat(
                        product.get("updatedAt", "").replace("Z", "+00:00")
                    )
                    if updated_at >= updated_since:
                        filtered_products.append(product)
                except (ValueError, TypeError):
                    # Include items if we can't parse the date
                    filtered_products.append(product)
            
            logger.info(f"Filtered {len(filtered_products)} products updated since {updated_since}")
            return filtered_products
        
        else:
            logger.warning(f"Incremental updates not implemented for data type: {data_type}")
            return []