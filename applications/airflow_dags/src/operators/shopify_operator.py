"""
Custom Shopify Operators for Airflow 3.0.2

This module provides simple, synchronous operators for Shopify data operations.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from airflow.models import BaseOperator
from airflow.utils.context import Context
from airflow.exceptions import AirflowException

import structlog
import json

from pxy6.hooks.shopify_hook import ShopifyHook
from pxy6.utils.database import upsert_customer, upsert_product, upsert_order, execute_query

logger = structlog.get_logger(__name__)


class ShopifyToPostgresOperator(BaseOperator):
    """
    Operator to extract data from Shopify and load it into PostgreSQL
    
    This operator handles the complete ETL process for Shopify data,
    including extraction, transformation, and loading into the database.
    """
    
    template_fields = ["start_date", "end_date", "batch_size", "max_pages"]
    
    def __init__(
        self,
        shopify_conn_id: str = "shopify_default",
        postgres_conn_id: str = "postgres_default",
        data_type: str = "products",  # products, customers, orders
        batch_size: int = 100,
        max_pages: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        incremental: bool = True,
        upsert: bool = True,
        **kwargs
    ):
        """
        Initialize ShopifyToPostgresOperator
        
        Args:
            shopify_conn_id: Airflow connection ID for Shopify
            postgres_conn_id: Airflow connection ID for PostgreSQL
            data_type: Type of data to extract (products, customers, orders)
            batch_size: Number of records to process in each batch
            max_pages: Maximum number of pages to fetch
            start_date: Start date for incremental sync
            end_date: End date for incremental sync
            incremental: Whether to perform incremental sync
            upsert: Whether to upsert records or insert only
        """
        super().__init__(**kwargs)
        self.shopify_conn_id = shopify_conn_id
        self.postgres_conn_id = postgres_conn_id
        self.data_type = data_type
        self.batch_size = batch_size
        self.max_pages = max_pages
        self.start_date = start_date
        self.end_date = end_date
        self.incremental = incremental
        self.upsert = upsert
        
        # Validate data type
        if data_type not in ["products", "customers", "orders"]:
            raise AirflowException(f"Invalid data_type: {data_type}")
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """
        Execute the operator
        
        Args:
            context: Airflow context
            
        Returns:
            Dictionary with execution results
        """
        logger.info(f"Starting Shopify to Postgres sync for {self.data_type}")
        
        # Get shop domain from DAG run configuration
        dag_run_conf = context.get("dag_run", {}).conf or {}
        shop_domain = dag_run_conf.get("shop_domain")
        
        if not shop_domain:
            raise AirflowException("Shop domain is required for sync operations")
        
        # Initialize hooks
        shopify_hook = ShopifyHook(shopify_conn_id=self.shopify_conn_id)
        
        # Test connections
        if not shopify_hook.test_connection():
            raise AirflowException("Failed to connect to Shopify API")
        
        try:
            # Run the sync operation
            result = self._sync_data(shopify_hook, shop_domain)
            
            logger.info(f"Sync completed successfully: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Sync failed: {str(e)}")
            raise AirflowException(f"Sync failed: {str(e)}")
        
        finally:
            shopify_hook.close()
    
    def _sync_data(self, shopify_hook: ShopifyHook, shop_domain: str) -> Dict[str, Any]:
        """
        Sync data from Shopify to PostgreSQL
        
        Args:
            shopify_hook: Shopify hook instance
            shop_domain: Shop domain for multi-tenancy
            
        Returns:
            Dictionary with sync results
        """
        # Get data from Shopify
        data = self._extract_data(shopify_hook)
        
        # Process and load data
        result = self._load_data(data, shop_domain)
        
        return result
    
    def _extract_data(self, shopify_hook: ShopifyHook) -> List[Dict[str, Any]]:
        """
        Extract data from Shopify
        
        Args:
            shopify_hook: Shopify hook instance
            
        Returns:
            List of extracted records
        """
        logger.info(f"Extracting {self.data_type} from Shopify")
        
        # Use the hook's built-in methods for data extraction
        if self.data_type == "products":
            data = shopify_hook.paginate_all_product_data(
                batch_size=self.batch_size
            )
        elif self.data_type == "customers":
            data = shopify_hook.paginate_customers_with_orders(
                batch_size=self.batch_size
            )
        elif self.data_type == "orders":
            # For orders, extract from customers with orders
            customers_data = shopify_hook.paginate_customers_with_orders(
                batch_size=self.batch_size
            )
            data = []
            for customer in customers_data:
                customer_orders = customer.get("orders", {}).get("edges", [])
                for order_edge in customer_orders:
                    data.append(order_edge["node"])
        else:
            raise AirflowException(f"Unsupported data type: {self.data_type}")
        
        logger.info(f"Extracted {len(data)} {self.data_type} records")
        return data
    
    def _load_data(self, data: List[Dict[str, Any]], shop_domain: str) -> Dict[str, Any]:
        """
        Load data into PostgreSQL
        
        Args:
            data: List of records to load
            shop_domain: Shop domain for multi-tenancy
            
        Returns:
            Dictionary with load results
        """
        logger.info(f"Loading {len(data)} {self.data_type} records into PostgreSQL")
        
        loaded_count = 0
        error_count = 0
        
        for record in data:
            try:
                if self.data_type == "products":
                    upsert_product(record, shop_domain)
                elif self.data_type == "customers":
                    upsert_customer(record, shop_domain)
                elif self.data_type == "orders":
                    upsert_order(record, shop_domain)
                
                loaded_count += 1
                
            except Exception as e:
                logger.error(f"Failed to load record {record.get('id', 'unknown')}: {str(e)}")
                error_count += 1
        
        result = {
            "data_type": self.data_type,
            "extracted_count": len(data),
            "loaded_count": loaded_count,
            "error_count": error_count,
            "success_rate": loaded_count / len(data) if data else 0
        }
        
        logger.info(f"Load completed: {result}")
        return result