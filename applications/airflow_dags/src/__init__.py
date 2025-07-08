"""
PXY6 Airflow Package

A comprehensive package for Shopify data integration with Apache Airflow.
Provides operators, hooks, and utilities for syncing Shopify data to PostgreSQL.
"""

__version__ = "1.0.0"
__author__ = "PXY6 Team"
__email__ = "team@pxy6.com"

# Import key components for easier access
from .operators.shopify_operator import (
    ShopifyToPostgresOperator,
    ShopifyDataValidationOperator,
    ShopifyIncrementalSyncOperator,
)
from .hooks.shopify_hook import ShopifyHook
from .utils.database import DatabaseManager
from .utils.shopify_client import ShopifyClient
from .utils.config import Config

__all__ = [
    "ShopifyToPostgresOperator",
    "ShopifyDataValidationOperator",
    "ShopifyIncrementalSyncOperator",
    "ShopifyHook",
    "DatabaseManager",
    "ShopifyClient",
    "Config",
]