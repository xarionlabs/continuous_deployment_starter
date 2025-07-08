"""
Shopify Data Sync DAG

Simple Airflow DAG for synchronizing Shopify data (customers, orders, products) 
to the PXY6 database. Follows Airflow best practices with clear, linear task flow.

Schedule: Daily at 2:00 AM UTC
"""

from datetime import datetime, timedelta
from airflow.decorators import dag, task
import asyncio
import structlog

from pxy6.utils.shopify_graphql import ShopifyGraphQLClient
from pxy6.utils.database import DatabaseManager

logger = structlog.get_logger(__name__)

# Default arguments for all tasks
default_args = {
    "owner": "pxy6-data-team",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

@dag(
    dag_id="shopify_sync",
    default_args=default_args,
    description="Sync Shopify customers, orders, and products to database",
    schedule=None,  # Triggered manually via app.pxy6.com API
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["shopify", "etl", "sync"],
    doc_md=__doc__,
)
def shopify_sync_dag():
    
    @task
    def sync_customers() -> dict:
        """Extract and load customer data from Shopify"""
        logger.info("Starting customer sync")
        
        async def _sync_customers():
            # Initialize clients
            graphql_client = ShopifyGraphQLClient()
            db_manager = DatabaseManager()
            
            try:
                await db_manager.connect()
                await db_manager.create_tables()
                
                # Extract customers
                customers_data = []
                cursor = None
                
                while True:
                    result = graphql_client.get_customers_with_orders(limit=100, cursor=cursor)
                    customers = result.get("customers", {})
                    edges = customers.get("edges", [])
                    
                    if not edges:
                        break
                    
                    customers_data.extend([edge["node"] for edge in edges])
                    
                    # Check pagination
                    page_info = customers.get("pageInfo", {})
                    if not page_info.get("hasNextPage", False):
                        break
                    cursor = page_info.get("endCursor")
                
                # Load customers to database
                for customer in customers_data:
                    await db_manager.upsert_customer(customer)
                
                return {"customers_synced": len(customers_data)}
                
            finally:
                await db_manager.close()
        
        result = asyncio.run(_sync_customers())
        logger.info(f"Customer sync completed: {result}")
        return result
    
    @task
    def sync_orders() -> dict:
        """Extract and load order data from Shopify"""
        logger.info("Starting order sync")
        
        async def _sync_orders():
            # Initialize clients
            graphql_client = ShopifyGraphQLClient()
            db_manager = DatabaseManager()
            
            try:
                await db_manager.connect()
                
                # Extract orders from last 7 days for incremental sync
                lookback_time = datetime.now() - timedelta(days=7)
                orders_data = []
                cursor = None
                
                while True:
                    result = graphql_client.get_orders(limit=100, cursor=cursor)
                    orders = result.get("orders", {})
                    edges = orders.get("edges", [])
                    
                    if not edges:
                        break
                    
                    # Filter recent orders
                    for edge in edges:
                        order = edge["node"]
                        order_date = datetime.fromisoformat(
                            order.get("createdAt", "").replace("Z", "+00:00")
                        )
                        if order_date >= lookback_time:
                            orders_data.append(order)
                    
                    # Check pagination
                    page_info = orders.get("pageInfo", {})
                    if not page_info.get("hasNextPage", False):
                        break
                    cursor = page_info.get("endCursor")
                
                # Load orders to database
                orders_count = 0
                for order in orders_data:
                    await db_manager.upsert_order(order)
                    orders_count += 1
                
                return {"orders_synced": orders_count}
                
            finally:
                await db_manager.close()
        
        result = asyncio.run(_sync_orders())
        logger.info(f"Order sync completed: {result}")
        return result
    
    @task
    def sync_products() -> dict:
        """Extract and load product data from Shopify"""
        logger.info("Starting product sync")
        
        async def _sync_products():
            # Initialize clients
            graphql_client = ShopifyGraphQLClient()
            db_manager = DatabaseManager()
            
            try:
                await db_manager.connect()
                
                # Extract products
                products_data = []
                cursor = None
                
                while True:
                    result = graphql_client.get_all_product_data(limit=50, cursor=cursor)
                    products = result.get("products", {})
                    edges = products.get("edges", [])
                    
                    if not edges:
                        break
                    
                    products_data.extend([edge["node"] for edge in edges])
                    
                    # Check pagination
                    page_info = products.get("pageInfo", {})
                    if not page_info.get("hasNextPage", False):
                        break
                    cursor = page_info.get("endCursor")
                
                # Load products to database
                products_count = 0
                for product in products_data:
                    await db_manager.upsert_product(product)
                    products_count += 1
                    
                    # Sync product variants
                    variants = product.get("variants", {}).get("edges", [])
                    for variant_edge in variants:
                        variant = variant_edge["node"]
                        variant["product_id"] = product["id"]
                        await db_manager.upsert_product_variant(variant)
                    
                    # Sync product images
                    images = product.get("images", {}).get("edges", [])
                    for image_edge in images:
                        image = image_edge["node"]
                        image["product_id"] = product["id"]
                        await db_manager.upsert_product_image(image)
                
                return {"products_synced": products_count}
                
            finally:
                await db_manager.close()
        
        result = asyncio.run(_sync_products())
        logger.info(f"Product sync completed: {result}")
        return result
    
    @task
    def generate_sync_summary(customer_result: dict, order_result: dict, product_result: dict) -> dict:
        """Generate summary of sync operation"""
        summary = {
            "sync_timestamp": datetime.now().isoformat(),
            "customers_synced": customer_result.get("customers_synced", 0),
            "orders_synced": order_result.get("orders_synced", 0), 
            "products_synced": product_result.get("products_synced", 0),
            "status": "completed"
        }
        
        logger.info(f"Sync summary: {summary}")
        return summary
    
    # Define task dependencies
    customers = sync_customers()
    orders = sync_orders()
    products = sync_products()
    summary = generate_sync_summary(customers, orders, products)
    
    # Linear dependency chain
    [customers, orders, products] >> summary

# Instantiate the DAG
shopify_sync_dag()