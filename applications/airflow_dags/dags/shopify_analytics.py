"""
Shopify Analytics DAG

Simple Airflow DAG for calculating basic Shopify analytics and metrics
from synchronized data. Runs after the main sync completes.

Schedule: Daily at 4:00 AM UTC (2 hours after sync)
"""

from datetime import datetime, timedelta
from airflow.decorators import dag, task
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor
import asyncio
import structlog

from pxy6.utils.database import DatabaseManager

logger = structlog.get_logger(__name__)

# Default arguments for all tasks
default_args = {
    "owner": "pxy6-data-team",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

@dag(
    dag_id="shopify_analytics",
    default_args=default_args,
    description="Calculate basic Shopify analytics and metrics",
    schedule=None,  # Triggered manually or by external task sensor
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["shopify", "analytics", "metrics"],
    doc_md=__doc__,
)
def shopify_analytics_dag():
    
    # Wait for sync DAG to complete
    wait_for_sync = ExternalTaskSensor(
        task_id="wait_for_sync",
        external_dag_id="shopify_sync",
        external_task_id=None,  # Wait for entire DAG
        timeout=3600,  # 1 hour timeout
        poke_interval=300,  # Check every 5 minutes
    )
    
    @task
    def calculate_customer_metrics(**context) -> dict:
        """Calculate basic customer metrics"""
        logger.info("Calculating customer metrics")
        
        # Get DAG run configuration (may be passed from shopify_sync)
        dag_run_conf = context['dag_run'].conf or {}
        
        async def _calculate_metrics():
            db_manager = DatabaseManager()
            
            try:
                await db_manager.connect()
                
                # Basic customer counts
                total_customers = await db_manager.get_customers_count()
                
                # Customers with orders
                customers_with_orders = await db_manager.execute_query(
                    "SELECT COUNT(*) as count FROM shopify_customers WHERE number_of_orders > 0",
                    fetch=True
                )
                customers_with_orders_count = customers_with_orders[0]["count"] if customers_with_orders else 0
                
                # New customers this month
                new_customers_month = await db_manager.execute_query(
                    "SELECT COUNT(*) as count FROM shopify_customers WHERE created_at >= date_trunc('month', CURRENT_DATE)",
                    fetch=True
                )
                new_customers_month_count = new_customers_month[0]["count"] if new_customers_month else 0
                
                metrics = {
                    "total_customers": total_customers,
                    "customers_with_orders": customers_with_orders_count,
                    "new_customers_this_month": new_customers_month_count,
                    "customer_conversion_rate": round(customers_with_orders_count / total_customers * 100, 2) if total_customers > 0 else 0
                }
                
                return metrics
                
            finally:
                await db_manager.close()
        
        result = asyncio.run(_calculate_metrics())
        logger.info(f"Customer metrics: {result}")
        return result
    
    @task
    def calculate_order_metrics(**context) -> dict:
        """Calculate basic order metrics"""
        logger.info("Calculating order metrics")
        
        # Get DAG run configuration (may be passed from shopify_sync)
        dag_run_conf = context['dag_run'].conf or {}
        
        async def _calculate_metrics():
            db_manager = DatabaseManager()
            
            try:
                await db_manager.connect()
                
                # Basic order counts
                total_orders = await db_manager.get_orders_count()
                
                # Revenue metrics
                revenue_query = await db_manager.execute_query("""
                    SELECT 
                        SUM(total_price_amount) as total_revenue,
                        AVG(total_price_amount) as avg_order_value,
                        COUNT(*) as orders_with_revenue
                    FROM shopify_orders 
                    WHERE total_price_amount > 0
                """, fetch=True)
                
                revenue_data = revenue_query[0] if revenue_query else {}
                
                # Orders this week
                orders_week = await db_manager.execute_query(
                    "SELECT COUNT(*) as count FROM shopify_orders WHERE created_at >= date_trunc('week', CURRENT_DATE)",
                    fetch=True
                )
                orders_week_count = orders_week[0]["count"] if orders_week else 0
                
                metrics = {
                    "total_orders": total_orders,
                    "total_revenue": float(revenue_data.get("total_revenue", 0) or 0),
                    "average_order_value": float(revenue_data.get("avg_order_value", 0) or 0),
                    "orders_this_week": orders_week_count
                }
                
                return metrics
                
            finally:
                await db_manager.close()
        
        result = asyncio.run(_calculate_metrics())
        logger.info(f"Order metrics: {result}")
        return result
    
    @task
    def calculate_product_metrics(**context) -> dict:
        """Calculate basic product metrics"""
        logger.info("Calculating product metrics")
        
        # Get DAG run configuration (may be passed from shopify_sync)
        dag_run_conf = context['dag_run'].conf or {}
        
        async def _calculate_metrics():
            db_manager = DatabaseManager()
            
            try:
                await db_manager.connect()
                
                # Basic product counts
                total_products = await db_manager.get_products_count()
                
                # Active products
                active_products = await db_manager.execute_query(
                    "SELECT COUNT(*) as count FROM shopify_products WHERE status = 'ACTIVE'",
                    fetch=True
                )
                active_products_count = active_products[0]["count"] if active_products else 0
                
                # Products with variants
                products_with_variants = await db_manager.execute_query("""
                    SELECT COUNT(DISTINCT product_id) as count 
                    FROM shopify_product_variants
                """, fetch=True)
                products_with_variants_count = products_with_variants[0]["count"] if products_with_variants else 0
                
                # Total variants
                total_variants = await db_manager.execute_query(
                    "SELECT COUNT(*) as count FROM shopify_product_variants",
                    fetch=True
                )
                total_variants_count = total_variants[0]["count"] if total_variants else 0
                
                metrics = {
                    "total_products": total_products,
                    "active_products": active_products_count,
                    "products_with_variants": products_with_variants_count,
                    "total_variants": total_variants_count
                }
                
                return metrics
                
            finally:
                await db_manager.close()
        
        result = asyncio.run(_calculate_metrics())
        logger.info(f"Product metrics: {result}")
        return result
    
    @task
    def generate_analytics_report(customer_metrics: dict, order_metrics: dict, product_metrics: dict) -> dict:
        """Generate consolidated analytics report"""
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "customer_metrics": customer_metrics,
            "order_metrics": order_metrics,
            "product_metrics": product_metrics,
            "status": "completed"
        }
        
        logger.info(f"Analytics report generated: {report}")
        return report
    
    # Define task dependencies
    customer_metrics = calculate_customer_metrics()
    order_metrics = calculate_order_metrics()
    product_metrics = calculate_product_metrics()
    report = generate_analytics_report(customer_metrics, order_metrics, product_metrics)
    
    # Task flow
    wait_for_sync >> [customer_metrics, order_metrics, product_metrics] >> report

# Instantiate the DAG
shopify_analytics_dag()