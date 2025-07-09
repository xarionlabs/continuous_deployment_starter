"""
Utility modules for Airflow DAGs.

This package contains utility functions and classes for:
- Shopify API interactions
- Database connections and operations
- Data processing and transformation
- Logging and monitoring
- Configuration management
"""

from .database import (
    get_postgres_hook, execute_query, execute_insert, 
    upsert_customer, upsert_product, upsert_order,
    upsert_product_variant, upsert_product_image
)

__all__ = [
    'get_postgres_hook',
    'execute_query',
    'execute_insert',
    'upsert_customer',
    'upsert_product',
    'upsert_order',
    'upsert_product_variant',
    'upsert_product_image',
]