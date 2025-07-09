"""
PXY6 Airflow Package

A comprehensive package for Shopify data integration with Apache Airflow.
Provides operators, hooks, and utilities for syncing Shopify data to PostgreSQL.
"""

__version__ = "1.0.0"
__author__ = "PXY6 Team"
__email__ = "team@pxy6.com"

# Import key components for easier access
from .operators.shopify_operator import ShopifyToPostgresOperator
from .hooks.shopify_hook import ShopifyHook
from .utils.database import (
    get_postgres_hook, execute_query, execute_insert,
    upsert_customer, upsert_product, upsert_order,
    upsert_product_variant, upsert_product_image
)
from .utils.shopify_client import ShopifyGraphQLClient
from .utils.config import AirflowConfig

__all__ = [
    "ShopifyToPostgresOperator",
    "ShopifyHook",
    "get_postgres_hook",
    "execute_query",
    "execute_insert",
    "upsert_customer",
    "upsert_product",
    "upsert_order",
    "upsert_product_variant",
    "upsert_product_image",
    "ShopifyGraphQLClient",
    "AirflowConfig",
]