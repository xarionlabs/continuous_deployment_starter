"""
Utility modules for Airflow DAGs.

This package contains utility functions and classes for:
- Shopify API interactions
- Database connections and operations
- Data processing and transformation
- Logging and monitoring
- Configuration management
"""

from .shopify_client import ShopifyGraphQLClient
from .shopify_graphql import ShopifyGraphQLClient as ShopifyGraphQLClientV2
from .database import (
    get_postgres_hook, execute_query, execute_insert, 
    upsert_customer, upsert_product, upsert_order,
    upsert_product_variant, upsert_product_image
)
from .config import get_config, get_shopify_config

__all__ = [
    'ShopifyGraphQLClient',
    'ShopifyGraphQLClientV2',
    'get_postgres_hook',
    'execute_query',
    'execute_insert',
    'upsert_customer',
    'upsert_product',
    'upsert_order',
    'upsert_product_variant',
    'upsert_product_image',
    'get_config',
    'get_shopify_config',
]