"""
Shopify Analytics DAG

Simple Airflow DAG for calculating basic Shopify analytics and metrics
from synchronized data. Runs after the main sync completes.

Schedule: Daily at 4:00 AM UTC (2 hours after sync)
"""

from datetime import datetime, timedelta
from airflow.decorators import dag, task
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor
import structlog

from pxy6.utils.database import execute_query

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
        
        # Basic customer counts
        total_customers = execute_query("SELECT COUNT(*) as count FROM customers")
        total_customers_count = total_customers[0]["count"] if total_customers else 0
        
        # Customers with orders
        customers_with_orders = execute_query(
            "SELECT COUNT(*) as count FROM customers WHERE number_of_orders > 0"
        )
        customers_with_orders_count = customers_with_orders[0]["count"] if customers_with_orders else 0
        
        # New customers this month
        new_customers_month = execute_query(
            "SELECT COUNT(*) as count FROM customers WHERE created_at >= date_trunc('month', CURRENT_DATE)"
        )
        new_customers_month_count = new_customers_month[0]["count"] if new_customers_month else 0
        
        metrics = {
            "total_customers": total_customers_count,
            "customers_with_orders": customers_with_orders_count,
            "new_customers_this_month": new_customers_month_count,
            "customer_conversion_rate": round(customers_with_orders_count / total_customers_count * 100, 2) if total_customers_count > 0 else 0
        }
        
        logger.info(f"Customer metrics: {metrics}")
        return metrics
    
    @task
    def calculate_order_metrics(**context) -> dict:
        """Calculate basic order metrics"""
        logger.info("Calculating order metrics")
        
        # Get DAG run configuration (may be passed from shopify_sync)
        dag_run_conf = context['dag_run'].conf or {}
        
        # Basic order counts
        total_orders = execute_query("SELECT COUNT(*) as count FROM orders")
        total_orders_count = total_orders[0]["count"] if total_orders else 0
        
        # Revenue metrics
        revenue_query = execute_query("""
            SELECT 
                SUM(total_price_amount) as total_revenue,
                AVG(total_price_amount) as avg_order_value,
                COUNT(*) as orders_with_revenue
            FROM orders 
            WHERE total_price_amount > 0
        """)
        
        revenue_data = revenue_query[0] if revenue_query else {}
        
        # Orders this week
        orders_week = execute_query(
            "SELECT COUNT(*) as count FROM orders WHERE created_at >= date_trunc('week', CURRENT_DATE)"
        )
        orders_week_count = orders_week[0]["count"] if orders_week else 0
        
        metrics = {
            "total_orders": total_orders_count,
            "total_revenue": float(revenue_data.get("total_revenue", 0) or 0),
            "average_order_value": float(revenue_data.get("avg_order_value", 0) or 0),
            "orders_this_week": orders_week_count
        }
        
        logger.info(f"Order metrics: {metrics}")
        return metrics
    
    @task
    def calculate_product_metrics(**context) -> dict:
        """Calculate basic product metrics"""
        logger.info("Calculating product metrics")
        
        # Get DAG run configuration (may be passed from shopify_sync)
        dag_run_conf = context['dag_run'].conf or {}
        
        # Basic product counts
        total_products = execute_query("SELECT COUNT(*) as count FROM products")
        total_products_count = total_products[0]["count"] if total_products else 0
        
        # Active products
        active_products = execute_query(
            "SELECT COUNT(*) as count FROM products WHERE status = 'ACTIVE'"
        )
        active_products_count = active_products[0]["count"] if active_products else 0
        
        # Products with variants
        products_with_variants = execute_query("""
            SELECT COUNT(DISTINCT product_id) as count 
            FROM product_variants
        """)
        products_with_variants_count = products_with_variants[0]["count"] if products_with_variants else 0
        
        # Total variants
        total_variants = execute_query(
            "SELECT COUNT(*) as count FROM product_variants"
        )
        total_variants_count = total_variants[0]["count"] if total_variants else 0
        
        metrics = {
            "total_products": total_products_count,
            "active_products": active_products_count,
            "products_with_variants": products_with_variants_count,
            "total_variants": total_variants_count
        }
        
        logger.info(f"Product metrics: {metrics}")
        return metrics
    
    @task
    def generate_analytics_report(customer_metrics: dict, order_metrics: dict, product_metrics: dict) -> dict:
        """Generate consolidated analytics report"""
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "customer_metrics": customer_metrics,
            "order_metrics": order_metrics,
            "product_metrics": product_metrics,
            "summary": {
                "total_customers": customer_metrics["total_customers"],
                "total_orders": order_metrics["total_orders"],
                "total_products": product_metrics["total_products"],
                "total_revenue": order_metrics["total_revenue"],
                "avg_order_value": order_metrics["average_order_value"],
                "customer_conversion_rate": customer_metrics["customer_conversion_rate"]
            }
        }
        
        logger.info(f"Analytics report generated: {report}")
        return report
    
    # Define task dependencies
    customer_metrics = calculate_customer_metrics()
    order_metrics = calculate_order_metrics()
    product_metrics = calculate_product_metrics()
    report = generate_analytics_report(customer_metrics, order_metrics, product_metrics)
    
    # Set up dependency chain
    wait_for_sync >> [customer_metrics, order_metrics, product_metrics] >> report

# Instantiate the DAG
shopify_analytics_dag()