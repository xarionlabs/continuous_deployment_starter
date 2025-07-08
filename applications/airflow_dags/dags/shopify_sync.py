"""
Shopify Data Sync DAG

Simple Airflow DAG for synchronizing Shopify data (customers, orders, products) 
to the PXY6 database. Follows Airflow best practices with clear, linear task flow.

Schedule: Daily at 2:00 AM UTC
"""

from datetime import datetime, timedelta
from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
import asyncio
import structlog

from pxy6.hooks.shopify_hook import ShopifyHook
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
    def sync_customers(**context) -> dict:
        """Extract and load customer data from Shopify"""
        logger.info("Starting customer sync")
        
        # Get DAG run configuration
        dag_run_conf = context['dag_run'].conf or {}
        
        async def _sync_customers():
            # Initialize hook with DAG configuration
            hook = ShopifyHook()
            hook.setup_with_dag_config(dag_run_conf)
            
            # Test connection first
            if not hook.test_connection():
                shop_domain = dag_run_conf.get('shop_domain', 'unknown')
                raise AirflowException(f"Failed to connect to Shopify shop: {shop_domain}")
            
            db_manager = DatabaseManager()
            
            try:
                await db_manager.connect()
                await db_manager.create_tables()
                
                # Extract customers using the hook
                customers_data = hook.paginate_customers_with_orders(batch_size=100)
                
                # Load customers to database
                for customer in customers_data:
                    await db_manager.upsert_customer(customer)
                
                logger.info(f"Successfully synced {len(customers_data)} customers for shop: {dag_run_conf.get('shop_domain')}")
                return {"customers_synced": len(customers_data)}
                
            finally:
                await db_manager.close()
                hook.close()
        
        result = asyncio.run(_sync_customers())
        logger.info(f"Customer sync completed: {result}")
        return result
    
    @task
    def sync_orders(**context) -> dict:
        """Extract and load order data from Shopify"""
        logger.info("Starting order sync")
        
        # Get DAG run configuration
        dag_run_conf = context['dag_run'].conf or {}
        
        async def _sync_orders():
            # Initialize hook with DAG configuration
            hook = ShopifyHook()
            hook.setup_with_dag_config(dag_run_conf)
            
            # Test connection first
            if not hook.test_connection():
                shop_domain = dag_run_conf.get('shop_domain', 'unknown')
                raise AirflowException(f"Failed to connect to Shopify shop: {shop_domain}")
            
            db_manager = DatabaseManager()
            
            try:
                await db_manager.connect()
                
                # For now, get all customers with orders (which includes order data)
                # This will be more efficient than a separate orders query for most shops
                customers_with_orders = hook.paginate_customers_with_orders(batch_size=100)
                
                # Extract order data from customers
                orders_data = []
                for customer in customers_with_orders:
                    customer_orders = customer.get("orders", {}).get("edges", [])
                    for order_edge in customer_orders:
                        order = order_edge["node"]
                        # Filter for recent orders (last 7 days)
                        order_date = datetime.fromisoformat(
                            order.get("createdAt", "").replace("Z", "+00:00")
                        )
                        lookback_time = datetime.now() - timedelta(days=7)
                        if order_date >= lookback_time:
                            orders_data.append(order)
                
                # Load orders to database
                orders_count = 0
                for order in orders_data:
                    await db_manager.upsert_order(order)
                    orders_count += 1
                
                logger.info(f"Successfully synced {orders_count} orders for shop: {dag_run_conf.get('shop_domain')}")
                return {"orders_synced": orders_count}
                
            finally:
                await db_manager.close()
                hook.close()
        
        result = asyncio.run(_sync_orders())
        logger.info(f"Order sync completed: {result}")
        return result
    
    @task
    def sync_products(**context) -> dict:
        """Extract and load product data from Shopify"""
        logger.info("Starting product sync")
        
        # Get DAG run configuration
        dag_run_conf = context['dag_run'].conf or {}
        
        async def _sync_products():
            # Initialize hook with DAG configuration
            hook = ShopifyHook()
            hook.setup_with_dag_config(dag_run_conf)
            
            # Test connection first
            if not hook.test_connection():
                shop_domain = dag_run_conf.get('shop_domain', 'unknown')
                raise AirflowException(f"Failed to connect to Shopify shop: {shop_domain}")
            
            db_manager = DatabaseManager()
            
            try:
                await db_manager.connect()
                
                # Extract products using the hook
                products_data = hook.paginate_all_product_data(
                    batch_size=50,
                    include_variants=True,
                    include_images=True,
                    include_metafields=True,
                    include_collections=True,
                    include_inventory=True
                )
                
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
                
                logger.info(f"Successfully synced {products_count} products for shop: {dag_run_conf.get('shop_domain')}")
                return {"products_synced": products_count}
                
            finally:
                await db_manager.close()
                hook.close()
        
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