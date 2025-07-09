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

from ..utils.query_loader import load_query

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
        shop_domain: str = None,
        access_token: str = None,
        api_version: str = "2025-01",
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit_calls_per_second: float = 2.0,
        enable_metrics: bool = True,
        enable_caching: bool = False,
        cache_ttl: int = 300,  # 5 minutes
        **kwargs,
    ):
        """
        Initialize Shopify Hook

        Args:
            shopify_conn_id: Airflow connection ID for Shopify (fallback)
            shop_domain: Shopify shop domain (without .myshopify.com)
            access_token: Shopify access token
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
        self._shop_name: Optional[str] = shop_domain
        self._access_token: Optional[str] = access_token
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
            "cache_misses": 0,
        }

        # Simple in-memory cache (for development/testing)
        self._cache = {} if enable_caching else None

        logger.info(
            f"Initialized ShopifyHook with connection: {shopify_conn_id}, "
            f"shop_domain: {shop_domain}, API version: {api_version}, "
            f"metrics: {enable_metrics}, caching: {enable_caching}"
        )

    def get_connection(self, conn_id: str) -> Connection:
        """Get Airflow connection for Shopify"""
        return super().get_connection(conn_id)

    def get_conn(self, dag_run_conf: Optional[Dict[str, Any]] = None) -> requests.Session:
        """
        Get or create HTTP session for Shopify API

        Args:
            dag_run_conf: Optional DAG run configuration with shop credentials

        Returns:
            Configured requests session
        """
        if self._session is None:
            self._setup_connection(dag_run_conf)
        return self._session

    def _setup_connection(self, dag_run_conf: Optional[Dict[str, Any]] = None) -> None:
        """Setup connection to Shopify API using DAG config or Airflow connection"""
        try:
            # Priority order: DAG run config > direct parameters > Airflow connection

            # 1. Try DAG run configuration first (for multi-tenant apps)
            if dag_run_conf:
                shop_domain = dag_run_conf.get("shop_domain")
                access_token = dag_run_conf.get("access_token")

                if shop_domain and access_token:
                    self._shop_name = shop_domain
                    self._access_token = access_token
                    logger.info(f"Using shop credentials from DAG config: {shop_domain}")

            # 2. Use direct parameters if provided and not already set
            if not self._shop_name or not self._access_token:
                if hasattr(self, "_shop_name") and hasattr(self, "_access_token"):
                    # Already set in __init__
                    pass

            # 3. Fall back to Airflow connection
            if not self._shop_name or not self._access_token:
                conn = self.get_connection(self.shopify_conn_id)
                self._shop_name = self._shop_name or conn.host
                self._access_token = self._access_token or conn.password
                logger.info(f"Using shop credentials from Airflow connection: {self.shopify_conn_id}")

            if not self._shop_name or not self._access_token:
                raise AirflowException(
                    "Missing shop_domain or access_token. Provide via DAG config, "
                    "direct parameters, or Airflow connection."
                )

            # Set GraphQL endpoint
            self._graphql_endpoint = (
                f"https://{self._shop_name}.myshopify.com/admin/api/{self.api_version}/graphql.json"
            )

            # Setup session with retry strategy
            self._session = requests.Session()

            # Configure retry strategy
            retry_strategy = Retry(
                total=self.max_retries,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET", "POST"],
            )

            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)

            # Set default headers
            self._session.headers.update(
                {
                    "X-Shopify-Access-Token": self._access_token,
                    "Content-Type": "application/json",
                    "User-Agent": "PXY6-Airflow-Hook/1.0",
                }
            )

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
        use_cache: bool = None,
        dag_run_conf: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute GraphQL query against Shopify API

        Args:
            query: GraphQL query string
            variables: Query variables
            operation_name: Optional operation name
            dag_run_conf: Optional DAG run configuration with shop credentials

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

        session = self.get_conn(dag_run_conf)

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

            start_time = time.time()
            response = session.post(self._graphql_endpoint, json=payload, timeout=self.timeout)
            execution_time = time.time() - start_time

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
            logger.error(f"Failed query: {query[:500]}{'...' if len(query) > 500 else ''}")
            logger.error(f"Variables: {variables}")
            raise AirflowException(f"HTTP request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Failed query: {query[:500]}{'...' if len(query) > 500 else ''}")
            logger.error(f"Variables: {variables}")
            raise AirflowException(f"Failed to parse JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during GraphQL execution: {str(e)}")
            logger.error(f"Failed query: {query[:500]}{'...' if len(query) > 500 else ''}")
            logger.error(f"Variables: {variables}")

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
        page_size: int = 100,
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
                query_vars.update({"first": page_size, "after": cursor})

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

    def setup_with_dag_config(self, dag_run_conf: Dict[str, Any]) -> None:
        """
        Setup hook with DAG run configuration

        Args:
            dag_run_conf: DAG run configuration containing shop credentials
        """
        if self._session:
            self.close()

        self._setup_connection(dag_run_conf)
        logger.info(f"ShopifyHook configured for shop: {self._shop_name}")

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

    def get_customers_with_orders_query(self) -> str:
        """
        Get the getCustomersWithOrders GraphQL query for comprehensive customer data

        Returns:
            GraphQL query string loaded from .gql file
        """
        return load_query("getCustomersWithOrders")

    def get_all_product_data_query(self) -> str:
        """
        Get the getAllProductData GraphQL query for comprehensive product data

        Returns:
            GraphQL query string loaded from .gql file
        """
        return load_query("getAllProductData")

    def get_product_images_query(self) -> str:
        """
        Get the getProductImagesById GraphQL query for detailed product image data

        Returns:
            GraphQL query string loaded from .gql file
        """
        return load_query("getProductImagesById")

    def get_customers_with_orders_data(
        self, limit: int = 50, cursor: Optional[str] = None, orders_limit: int = 50
    ) -> Dict[str, Any]:
        """
        Execute getCustomersWithOrders query and return data

        Args:
            limit: Number of customers to retrieve
            cursor: Cursor for pagination
            orders_limit: Number of orders to retrieve per customer

        Returns:
            Query result data
        """
        query = self.get_customers_with_orders_query()

        variables = {"limit": limit, "ordersFirst": orders_limit}
        if cursor:
            variables["cursor"] = cursor

        return self.execute_graphql(query, variables, "getCustomersWithOrders")

    def get_all_product_data(self, limit: int = 50, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute getAllProductData query and return data

        Args:
            limit: Number of products to retrieve
            cursor: Cursor for pagination

        Returns:
            Query result data
        """
        query = self.get_all_product_data_query()

        variables = {"limit": limit}
        if cursor:
            variables["cursor"] = cursor

        return self.execute_graphql(query, variables, "getAllProductData")

    def get_product_images_data(self, product_id: str, limit: int = 50) -> Dict[str, Any]:
        """
        Execute getProductImagesById query and return data

        Args:
            product_id: Shopify product ID
            limit: Number of images to retrieve

        Returns:
            Query result data
        """
        query = self.get_product_images_query()

        variables = {"productId": product_id, "limit": limit}

        return self.execute_graphql(query, variables, "getProductImagesById")

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

        self._cache[cache_key] = {"data": data, "timestamp": time.time()}

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
        self._metrics["avg_response_time"] = (current_avg * (total_requests - 1) + execution_time) / total_requests

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
                "cache_misses": 0,
            }

    def clear_cache(self) -> None:
        """Clear the cache"""
        if self._cache:
            self._cache.clear()
            logger.info("Cache cleared")

    def paginate_customers_with_orders(self, batch_size: int = 100) -> List[Dict[str, Any]]:
        """
        Paginate through all customers with orders data

        Args:
            batch_size: Number of customers per page

        Returns:
            List of all customer data with orders
        """
        query = self.get_customers_with_orders_query()
        return self.get_paginated_data(query=query, data_path=["data", "customers"], page_size=batch_size)

    def paginate_all_product_data(self, batch_size: int = 50) -> List[Dict[str, Any]]:
        """
        Paginate through all product data

        Args:
            batch_size: Number of products per page

        Returns:
            List of all product data
        """
        query = self.get_all_product_data_query()
        return self.get_paginated_data(query=query, data_path=["data", "products"], page_size=batch_size)

    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information"""
        if not self.enable_caching or not self._cache:
            return {"caching_disabled": True}

        return {
            "cache_size": len(self._cache),
            "cache_ttl": self.cache_ttl,
            "oldest_entry_age": (
                min(time.time() - item["timestamp"] for item in self._cache.values()) if self._cache else 0
            ),
        }

    def paginate_customers_with_orders(
        self, batch_size: int = 50, max_pages: Optional[int] = None, orders_limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Paginate through all customers with orders

        Args:
            batch_size: Number of customers to fetch per request
            max_pages: Maximum number of pages to fetch
            orders_limit: Number of orders to retrieve per customer

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
                result = self.get_customers_with_orders_data(limit=batch_size, cursor=cursor, orders_limit=orders_limit)

                customers = result.get("data", {}).get("customers", {})
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
                raise AirflowException(f"Customer pagination failed at page {page_count}: {str(e)}")

        logger.info(f"Successfully fetched {len(all_customers)} customers across {page_count} pages")
        return all_customers

    def paginate_all_product_data(self, batch_size: int = 50, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Paginate through all products with comprehensive data

        Args:
            batch_size: Number of products to fetch per request
            max_pages: Maximum number of pages to fetch

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
                result = self.get_all_product_data(limit=batch_size, cursor=cursor)

                products = result.get("data", {}).get("products", {})
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
                raise AirflowException(f"Product pagination failed at page {page_count}: {str(e)}")

        logger.info(f"Successfully fetched {len(all_products)} products across {page_count} pages")
        return all_products

    def get_incremental_updates(
        self, data_type: str, updated_since: datetime, batch_size: int = 50, max_pages: Optional[int] = None
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
                batch_size=batch_size, max_pages=max_pages, orders_limit=50
            )

            # Filter for items updated since the given time
            filtered_customers = []
            for customer in all_customers:
                try:
                    updated_at = datetime.fromisoformat(customer.get("updatedAt", "").replace("Z", "+00:00"))
                    if updated_at >= updated_since:
                        filtered_customers.append(customer)
                except (ValueError, TypeError):
                    # Include items if we can't parse the date
                    filtered_customers.append(customer)

            logger.info(f"Filtered {len(filtered_customers)} customers updated since {updated_since}")
            return filtered_customers

        elif data_type == "products":
            all_products = self.paginate_all_product_data(batch_size=batch_size, max_pages=max_pages)

            # Filter for items updated since the given time
            filtered_products = []
            for product in all_products:
                try:
                    updated_at = datetime.fromisoformat(product.get("updatedAt", "").replace("Z", "+00:00"))
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
