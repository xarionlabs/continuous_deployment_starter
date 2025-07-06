"""
Shopify Common Utilities for Airflow DAGs

This module provides common utilities for Shopify data integration DAGs,
including session management, database connections, and data loading functions.
"""

import os
import logging
from contextlib import contextmanager
from typing import Optional, List, Tuple, Any

import shopify
from airflow.models import Variable
from airflow.providers.postgres.hooks.postgres import PostgresHook

logger = logging.getLogger(__name__)

# Database connection ID for the application database
APP_DB_CONN_ID = Variable.get("app_db_conn_id", default_var="postgres_default")

@contextmanager
def get_shopify_session():
    """
    Context manager for Shopify API session.
    
    Handles authentication and session cleanup. Reads configuration from
    environment variables first, then falls back to Airflow Variables.
    
    Yields:
        shopify module: The shopify API module with active session
        
    Raises:
        ValueError: If required Shopify credentials are not configured
    """
    # Get configuration from environment variables (preferred) or Airflow Variables
    store_domain = os.getenv("SHOPIFY_STORE_DOMAIN") or Variable.get("shopify_store_domain", default_var=None)
    api_key = os.getenv("SHOPIFY_API_KEY") or Variable.get("shopify_api_key", default_var=None)
    api_password = os.getenv("SHOPIFY_API_PASSWORD") or Variable.get("shopify_api_password", default_var=None)
    api_version = os.getenv("SHOPIFY_API_VERSION") or Variable.get("shopify_api_version", default_var="2024-01")
    
    # Validate required credentials
    if not all([store_domain, api_key, api_password]):
        raise ValueError(
            "Shopify API credentials (store_domain, api_key, api_password) are not fully configured. "
            "Set them as environment variables or Airflow Variables."
        )
    
    # Build the API URL
    site_url = f"https://{api_key}:{api_password}@{store_domain}/admin/api/{api_version}"
    
    try:
        # Initialize Shopify session
        shopify.ShopifyResource.set_site(site_url)
        shopify.ShopifyResource.set_user_agent("AirflowDAGs/1.0")
        
        # Test the connection
        shopify.Shop.current()
        logger.info(f"Successfully connected to Shopify store: {store_domain}")
        
        yield shopify
        
    except Exception as e:
        logger.error(f"Failed to connect to Shopify: {e}")
        raise
    finally:
        # Always clear the session
        shopify.ShopifyResource.clear_session()


def get_app_db_hook() -> PostgresHook:
    """
    Get a PostgreSQL hook for the application database.
    
    Returns:
        PostgresHook: Hook instance for database operations
    """
    conn_id = Variable.get("app_db_conn_id", default_var="postgres_default")
    return PostgresHook(postgres_conn_id=conn_id)


def execute_query_on_app_db(sql: str, params: Optional[Tuple] = None) -> Any:
    """
    Execute a SQL query on the application database.
    
    Args:
        sql: SQL query string
        params: Optional query parameters
        
    Returns:
        Query result
    """
    hook = get_app_db_hook()
    if params:
        return hook.run(sql, parameters=params)
    else:
        return hook.run(sql)


def bulk_insert_to_app_db(table_name: str, records: List[Tuple], columns: List[str]) -> None:
    """
    Bulk insert records into the application database.
    
    Args:
        table_name: Name of the target table
        records: List of record tuples to insert
        columns: List of column names corresponding to record tuple values
    """
    if not records:
        logger.info(f"No records to insert into {table_name}")
        return
    
    hook = get_app_db_hook()
    hook.insert_rows(
        table=table_name,
        rows=records,
        target_fields=columns
    )
    logger.info(f"Successfully inserted {len(records)} records into {table_name}")