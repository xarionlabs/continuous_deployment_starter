"""
Shopify Past Purchases DAG - Customer Purchase Data Synchronization

This DAG handles comprehensive synchronization of customer purchase data from Shopify
using the getCustomersWithOrders GraphQL query. It extracts customer information along
with their complete order history, including line items, customer journey data, and
purchase analytics.

Features:
- Uses Airflow 3.0.2 @task decorators for modern workflow patterns
- Connects to pxy6 database using pxy6_airflow user
- Comprehensive error handling and retry logic
- Incremental and full sync modes
- Data quality validation and monitoring
- REST API triggerable for manual execution
- Comprehensive logging and status tracking

Schedule: Daily at 2:00 AM UTC
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import asyncio
import json

from airflow import DAG
from airflow.decorators import task, task_group
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator
from airflow.utils.trigger_rule import TriggerRule
from airflow.exceptions import AirflowException
from airflow.models import Variable
from airflow.sensors.time_delta import TimeDeltaSensor

import structlog
from pxy6.hooks.shopify_hook import ShopifyHook
from pxy6.utils.database import DatabaseManager
from pxy6.utils.shopify_graphql import ShopifyGraphQLClient

logger = structlog.get_logger(__name__)

# DAG Configuration
DAG_ID = "shopify_past_purchases"
DESCRIPTION = "Synchronize customer purchase data from Shopify using getCustomersWithOrders query"
SCHEDULE_INTERVAL = "0 2 * * *"  # Daily at 2:00 AM UTC
START_DATE = datetime(2024, 1, 1)
CATCHUP = False
MAX_ACTIVE_RUNS = 1
MAX_ACTIVE_TASKS = 5
DAGRUN_TIMEOUT = timedelta(hours=4)

# Default arguments with comprehensive error handling
default_args = {
    "owner": "pxy6-data-team",
    "depends_on_past": False,
    "start_date": START_DATE,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "execution_timeout": timedelta(hours=2),
}

# Create DAG
dag = DAG(
    DAG_ID,
    default_args=default_args,
    description=DESCRIPTION,
    schedule=SCHEDULE_INTERVAL,
    catchup=CATCHUP,
    max_active_runs=MAX_ACTIVE_RUNS,
    max_active_tasks=MAX_ACTIVE_TASKS,
    dagrun_timeout=DAGRUN_TIMEOUT,
    tags=["shopify", "customers", "purchases", "etl", "incremental"],
    doc_md=__doc__,
)

# Configuration Tasks
@task(dag=dag)
def get_sync_config(**context) -> Dict[str, Any]:
    """
    Get synchronization configuration for past purchases
    
    Returns:
        Dictionary containing sync configuration
    """
    logger.info("Getting past purchases sync configuration")
    
    config = {
        "sync_mode": Variable.get("shopify_past_purchases_sync_mode", "incremental"),
        "batch_size": int(Variable.get("shopify_past_purchases_batch_size", "50")),
        "max_pages": int(Variable.get("shopify_past_purchases_max_pages", "0")) or None,
        "lookback_hours": int(Variable.get("shopify_past_purchases_lookback_hours", "24")),
        "include_orders": Variable.get("shopify_past_purchases_include_orders", "true").lower() == "true",
        "include_line_items": Variable.get("shopify_past_purchases_include_line_items", "true").lower() == "true",
        "include_customer_journey": Variable.get("shopify_past_purchases_include_journey", "true").lower() == "true",
        "validation_enabled": Variable.get("shopify_past_purchases_validation", "true").lower() == "true",
        "data_quality_threshold": float(Variable.get("shopify_past_purchases_quality_threshold", "0.95")),
        "parallel_processing": Variable.get("shopify_past_purchases_parallel", "true").lower() == "true",
    }
    
    logger.info(f"Past purchases sync configuration: {config}")
    return config

@task(dag=dag)
def validate_connections(**context) -> Dict[str, Any]:
    """
    Validate Shopify and database connections
    
    Returns:
        Dictionary with connection validation results
    """
    logger.info("Validating connections for past purchases sync")
    
    validation_results = {
        "shopify_connection": False,
        "postgres_connection": False,
        "shopify_access_permissions": False,
        "overall_status": "FAILED"
    }
    
    try:
        # Test Shopify connection
        shopify_hook = ShopifyHook(shopify_conn_id="shopify_default")
        validation_results["shopify_connection"] = shopify_hook.test_connection()
        
        # Test Shopify GraphQL client with better error handling
        try:
            graphql_client = ShopifyGraphQLClient()
            shop_info = graphql_client.get_shop_info()
            validation_results["shopify_access_permissions"] = bool(shop_info.get("shop", {}).get("id"))
            logger.info(f"Shopify shop access verified: {shop_info.get('shop', {}).get('name', 'Unknown')}")
        except Exception as shop_error:
            logger.error(f"Shopify shop access validation failed: {str(shop_error)}")
            validation_results["shopify_access_permissions"] = False
            validation_results["shopify_error"] = str(shop_error)
        
        shopify_hook.close()
        
        # Test PostgreSQL connection
        async def test_postgres():
            db_manager = DatabaseManager()
            try:
                await db_manager.connect()
                result = await db_manager.test_connection()
                # Additional validation - check if we can query Shopify tables
                try:
                    await db_manager.execute_query("SELECT 1 FROM information_schema.tables WHERE table_name = 'shopify_customers' LIMIT 1", fetch=True)
                    logger.info("Database connection and table access verified")
                except Exception as table_error:
                    logger.warning(f"Shopify tables may not exist yet: {str(table_error)}")
                return result
            except Exception as db_error:
                logger.error(f"Database connection failed: {str(db_error)}")
                return False
            finally:
                await db_manager.close()
        
        validation_results["postgres_connection"] = asyncio.run(test_postgres())
        
        # Overall status
        if all([
            validation_results["shopify_connection"],
            validation_results["postgres_connection"],
            validation_results["shopify_access_permissions"]
        ]):
            validation_results["overall_status"] = "PASSED"
        
    except Exception as e:
        logger.error(f"Connection validation failed: {str(e)}")
        validation_results["error"] = str(e)
    
    logger.info(f"Connection validation results: {validation_results}")
    
    if validation_results["overall_status"] == "FAILED":
        raise AirflowException(f"Connection validation failed: {validation_results}")
    
    return validation_results

@task(dag=dag)
def prepare_database_tables(**context) -> Dict[str, Any]:
    """
    Prepare database tables for customer and order data
    
    Returns:
        Dictionary with database preparation results
    """
    logger.info("Preparing database tables for past purchases")
    
    async def setup_tables():
        db_manager = DatabaseManager()
        try:
            await db_manager.connect()
            
            # Create base tables
            await db_manager.create_tables()
            
            # Create additional tables for enhanced customer journey tracking
            await db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS shopify_customer_journey_moments (
                    id SERIAL PRIMARY KEY,
                    customer_id VARCHAR(255) REFERENCES shopify_customers(id),
                    order_id VARCHAR(255) REFERENCES shopify_orders(id),
                    moment_type VARCHAR(50),
                    occurred_at TIMESTAMP WITH TIME ZONE,
                    source VARCHAR(255),
                    medium VARCHAR(255),
                    campaign VARCHAR(255),
                    content VARCHAR(255),
                    term VARCHAR(255),
                    landing_page TEXT,
                    referrer TEXT,
                    raw_data JSONB,
                    synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create index for performance
            await db_manager.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_shopify_customer_journey_customer_id 
                ON shopify_customer_journey_moments(customer_id);
            """)
            
            await db_manager.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_shopify_customer_journey_occurred_at 
                ON shopify_customer_journey_moments(occurred_at);
            """)
            
            # Create customer analytics summary table
            await db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS shopify_customer_analytics (
                    customer_id VARCHAR(255) PRIMARY KEY REFERENCES shopify_customers(id),
                    total_orders INTEGER DEFAULT 0,
                    total_spent_amount DECIMAL(10, 2) DEFAULT 0,
                    total_spent_currency VARCHAR(10),
                    average_order_value DECIMAL(10, 2) DEFAULT 0,
                    first_order_date TIMESTAMP WITH TIME ZONE,
                    last_order_date TIMESTAMP WITH TIME ZONE,
                    days_since_last_order INTEGER,
                    customer_lifetime_days INTEGER,
                    total_line_items INTEGER DEFAULT 0,
                    unique_products_purchased INTEGER DEFAULT 0,
                    preferred_product_types TEXT[],
                    preferred_vendors TEXT[],
                    marketing_attribution JSONB,
                    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Get current statistics
            stats = {
                "customers_count": await db_manager.get_customers_count(),
                "orders_count": await db_manager.get_orders_count(),
                "setup_status": "SUCCESS"
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Database setup failed: {str(e)}")
            return {"setup_status": "FAILED", "error": str(e)}
        finally:
            await db_manager.close()
    
    result = asyncio.run(setup_tables())
    
    if result.get("setup_status") == "FAILED":
        raise AirflowException(f"Database preparation failed: {result.get('error')}")
    
    logger.info(f"Database preparation completed: {result}")
    return result

def decide_sync_mode(**context) -> str:
    """
    Decide whether to run full or incremental sync
    
    Returns:
        Task ID for the chosen sync mode
    """
    config = context["task_instance"].xcom_pull(task_ids="get_sync_config")
    sync_mode = config.get("sync_mode", "incremental")
    
    logger.info(f"Past purchases sync mode decision: {sync_mode}")
    
    if sync_mode == "full":
        return "full_sync_group.extract_all_customers"
    else:
        return "incremental_sync_group.extract_recent_customers"

# Sync Mode Decision
sync_mode_decision = BranchPythonOperator(
    task_id="decide_sync_mode",
    python_callable=decide_sync_mode,
    dag=dag,
)

# Full Sync Task Group
@task_group(group_id="full_sync_group", dag=dag)
def full_sync_operations():
    """Task group for full synchronization of customer purchase data"""
    
    @task
    def extract_all_customers(**context) -> Dict[str, Any]:
        """Extract all customers with their complete order history"""
        logger.info("Starting full extraction of customers with orders")
        
        config = context["task_instance"].xcom_pull(task_ids="get_sync_config")
        batch_size = config.get("batch_size", 50)
        max_pages = config.get("max_pages")
        
        try:
            graphql_client = ShopifyGraphQLClient()
            
            customers_data = []
            cursor = None
            page_count = 0
            
            while True:
                page_count += 1
                logger.info(f"Extracting page {page_count} of customers")
                
                # Get customers with orders using the GraphQL client
                result = graphql_client.get_customers_with_orders(
                    limit=batch_size,
                    cursor=cursor
                )
                
                customers = result.get("customers", {})
                edges = customers.get("edges", [])
                
                if not edges:
                    logger.info("No more customers to extract")
                    break
                
                # Process customer data
                for edge in edges:
                    customer_node = edge["node"]
                    customers_data.append(customer_node)
                
                logger.info(f"Extracted {len(edges)} customers on page {page_count}")
                
                # Check pagination
                page_info = customers.get("pageInfo", {})
                if not page_info.get("hasNextPage", False):
                    break
                
                cursor = page_info.get("endCursor")
                
                # Check max pages limit
                if max_pages and page_count >= max_pages:
                    logger.info(f"Reached max pages limit: {max_pages}")
                    break
            
            extraction_result = {
                "total_customers": len(customers_data),
                "pages_processed": page_count,
                "extraction_status": "SUCCESS"
            }
            
            logger.info(f"Full customer extraction completed: {extraction_result}")
            
            # Store data for processing
            context["task_instance"].xcom_push(
                key="customers_data",
                value=customers_data
            )
            
            return extraction_result
            
        except Exception as e:
            logger.error(f"Full customer extraction failed: {str(e)}")
            raise AirflowException(f"Full customer extraction failed: {str(e)}")
    
    @task
    def process_customer_data(**context) -> Dict[str, Any]:
        """Process and load customer data into database"""
        logger.info("Processing customer data for full sync")
        
        customers_data = context["task_instance"].xcom_pull(
            task_ids="full_sync_group.extract_all_customers",
            key="customers_data"
        )
        
        if not customers_data:
            raise AirflowException("No customer data available for processing")
        
        async def process_data():
            db_manager = DatabaseManager()
            try:
                await db_manager.connect()
                
                processed_customers = 0
                processed_orders = 0
                processed_line_items = 0
                error_count = 0
                
                for customer_data in customers_data:
                    try:
                        # Process customer
                        await db_manager.upsert_customer(customer_data)
                        processed_customers += 1
                        
                        # Process customer orders
                        orders = customer_data.get("orders", {}).get("edges", [])
                        for order_edge in orders:
                            order_data = order_edge["node"]
                            
                            # Add customer reference to order
                            order_data["customer_id"] = customer_data["id"]
                            
                            # Process order
                            await upsert_order(db_manager, order_data)
                            processed_orders += 1
                            
                            # Process line items
                            line_items = order_data.get("lineItems", {}).get("edges", [])
                            for line_item_edge in line_items:
                                line_item_data = line_item_edge["node"]
                                line_item_data["order_id"] = order_data["id"]
                                
                                await upsert_line_item(db_manager, line_item_data)
                                processed_line_items += 1
                            
                            # Process customer journey data
                            journey_data = order_data.get("customerJourneySummary")
                            if journey_data:
                                await upsert_customer_journey(
                                    db_manager, 
                                    customer_data["id"], 
                                    order_data["id"], 
                                    journey_data
                                )
                    
                    except Exception as e:
                        logger.error(f"Error processing customer {customer_data.get('id', 'unknown')}: {str(e)}")
                        error_count += 1
                
                # Update customer analytics
                await calculate_customer_analytics(db_manager)
                
                result = {
                    "processed_customers": processed_customers,
                    "processed_orders": processed_orders,
                    "processed_line_items": processed_line_items,
                    "error_count": error_count,
                    "processing_status": "SUCCESS"
                }
                
                return result
                
            finally:
                await db_manager.close()
        
        result = asyncio.run(process_data())
        
        logger.info(f"Customer data processing completed: {result}")
        return result
    
    # Task dependencies
    extract_task = extract_all_customers()
    process_task = process_customer_data()
    
    extract_task >> process_task
    
    return process_task

# Incremental Sync Task Group
@task_group(group_id="incremental_sync_group", dag=dag)
def incremental_sync_operations():
    """Task group for incremental synchronization of customer purchase data"""
    
    @task
    def extract_recent_customers(**context) -> Dict[str, Any]:
        """Extract customers with recent activity"""
        logger.info("Starting incremental extraction of customers with recent orders")
        
        config = context["task_instance"].xcom_pull(task_ids="get_sync_config")
        batch_size = config.get("batch_size", 50)
        lookback_hours = config.get("lookback_hours", 24)
        
        try:
            # Calculate lookback time
            lookback_time = datetime.now() - timedelta(hours=lookback_hours)
            
            graphql_client = ShopifyGraphQLClient()
            
            customers_data = []
            cursor = None
            page_count = 0
            
            while True:
                page_count += 1
                logger.info(f"Extracting page {page_count} of recent customers")
                
                # Get customers with orders
                result = graphql_client.get_customers_with_orders(
                    limit=batch_size,
                    cursor=cursor
                )
                
                customers = result.get("customers", {})
                edges = customers.get("edges", [])
                
                if not edges:
                    break
                
                # Filter customers with recent activity
                recent_customers = []
                for edge in edges:
                    customer_node = edge["node"]
                    
                    # Check if customer has recent orders
                    customer_updated = datetime.fromisoformat(
                        customer_node.get("updatedAt", "").replace("Z", "+00:00")
                    )
                    
                    if customer_updated >= lookback_time:
                        recent_customers.append(customer_node)
                
                customers_data.extend(recent_customers)
                
                # Check pagination
                page_info = customers.get("pageInfo", {})
                if not page_info.get("hasNextPage", False):
                    break
                
                cursor = page_info.get("endCursor")
            
            extraction_result = {
                "total_customers": len(customers_data),
                "pages_processed": page_count,
                "lookback_hours": lookback_hours,
                "extraction_status": "SUCCESS"
            }
            
            logger.info(f"Incremental customer extraction completed: {extraction_result}")
            
            # Store data for processing
            context["task_instance"].xcom_push(
                key="recent_customers_data",
                value=customers_data
            )
            
            return extraction_result
            
        except Exception as e:
            logger.error(f"Incremental customer extraction failed: {str(e)}")
            raise AirflowException(f"Incremental customer extraction failed: {str(e)}")
    
    @task
    def process_recent_customer_data(**context) -> Dict[str, Any]:
        """Process and load recent customer data"""
        logger.info("Processing recent customer data for incremental sync")
        
        customers_data = context["task_instance"].xcom_pull(
            task_ids="incremental_sync_group.extract_recent_customers",
            key="recent_customers_data"
        )
        
        if not customers_data:
            logger.info("No recent customer data to process")
            return {"processed_customers": 0, "processing_status": "SUCCESS"}
        
        async def process_data():
            db_manager = DatabaseManager()
            try:
                await db_manager.connect()
                
                processed_customers = 0
                processed_orders = 0
                error_count = 0
                
                for customer_data in customers_data:
                    try:
                        # Process customer
                        await db_manager.upsert_customer(customer_data)
                        processed_customers += 1
                        
                        # Process recent orders
                        orders = customer_data.get("orders", {}).get("edges", [])
                        for order_edge in orders:
                            order_data = order_edge["node"]
                            order_data["customer_id"] = customer_data["id"]
                            
                            await upsert_order(db_manager, order_data)
                            processed_orders += 1
                            
                            # Process line items
                            line_items = order_data.get("lineItems", {}).get("edges", [])
                            for line_item_edge in line_items:
                                line_item_data = line_item_edge["node"]
                                line_item_data["order_id"] = order_data["id"]
                                
                                await upsert_line_item(db_manager, line_item_data)
                    
                    except Exception as e:
                        logger.error(f"Error processing customer {customer_data.get('id', 'unknown')}: {str(e)}")
                        error_count += 1
                
                # Update analytics for processed customers
                await calculate_customer_analytics(db_manager, customer_ids=[c["id"] for c in customers_data])
                
                result = {
                    "processed_customers": processed_customers,
                    "processed_orders": processed_orders,
                    "error_count": error_count,
                    "processing_status": "SUCCESS"
                }
                
                return result
                
            finally:
                await db_manager.close()
        
        result = asyncio.run(process_data())
        
        logger.info(f"Recent customer data processing completed: {result}")
        return result
    
    # Task dependencies
    extract_task = extract_recent_customers()
    process_task = process_recent_customer_data()
    
    extract_task >> process_task
    
    return process_task

# Helper functions for data processing
async def upsert_order(db_manager: DatabaseManager, order_data: Dict[str, Any]) -> None:
    """Upsert order data into the database"""
    query = """
        INSERT INTO shopify_orders (
            id, name, email, customer_id, created_at, updated_at, processed_at,
            closed_at, cancelled, cancelled_at, cancel_reason, total_price_amount,
            total_price_currency_code, subtotal_price_amount, subtotal_price_currency_code,
            total_tax_amount, total_tax_currency_code, total_shipping_price_amount,
            total_shipping_price_currency_code, financial_status, fulfillment_status,
            tags, note, customer_journey_summary, raw_data, synced_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            email = EXCLUDED.email,
            customer_id = EXCLUDED.customer_id,
            updated_at = EXCLUDED.updated_at,
            processed_at = EXCLUDED.processed_at,
            closed_at = EXCLUDED.closed_at,
            cancelled = EXCLUDED.cancelled,
            cancelled_at = EXCLUDED.cancelled_at,
            cancel_reason = EXCLUDED.cancel_reason,
            total_price_amount = EXCLUDED.total_price_amount,
            total_price_currency_code = EXCLUDED.total_price_currency_code,
            subtotal_price_amount = EXCLUDED.subtotal_price_amount,
            subtotal_price_currency_code = EXCLUDED.subtotal_price_currency_code,
            total_tax_amount = EXCLUDED.total_tax_amount,
            total_tax_currency_code = EXCLUDED.total_tax_currency_code,
            total_shipping_price_amount = EXCLUDED.total_shipping_price_amount,
            total_shipping_price_currency_code = EXCLUDED.total_shipping_price_currency_code,
            financial_status = EXCLUDED.financial_status,
            fulfillment_status = EXCLUDED.fulfillment_status,
            tags = EXCLUDED.tags,
            note = EXCLUDED.note,
            customer_journey_summary = EXCLUDED.customer_journey_summary,
            raw_data = EXCLUDED.raw_data,
            synced_at = EXCLUDED.synced_at
    """
    
    # Extract pricing information
    total_price = order_data.get("totalPriceV2", {})
    subtotal_price = order_data.get("subtotalPriceV2", {})
    total_tax = order_data.get("totalTaxV2", {})
    total_shipping = order_data.get("totalShippingPriceV2", {})
    
    params = (
        order_data["id"],
        order_data.get("name"),
        order_data.get("email"),
        order_data.get("customer_id"),
        datetime.fromisoformat(order_data["createdAt"].replace("Z", "+00:00")) if order_data.get("createdAt") else None,
        datetime.fromisoformat(order_data["updatedAt"].replace("Z", "+00:00")) if order_data.get("updatedAt") else None,
        datetime.fromisoformat(order_data["processedAt"].replace("Z", "+00:00")) if order_data.get("processedAt") else None,
        datetime.fromisoformat(order_data["closedAt"].replace("Z", "+00:00")) if order_data.get("closedAt") else None,
        order_data.get("cancelled", False),
        datetime.fromisoformat(order_data["cancelledAt"].replace("Z", "+00:00")) if order_data.get("cancelledAt") else None,
        order_data.get("cancelReason"),
        float(total_price.get("amount", 0)) if total_price.get("amount") else None,
        total_price.get("currencyCode"),
        float(subtotal_price.get("amount", 0)) if subtotal_price.get("amount") else None,
        subtotal_price.get("currencyCode"),
        float(total_tax.get("amount", 0)) if total_tax.get("amount") else None,
        total_tax.get("currencyCode"),
        float(total_shipping.get("amount", 0)) if total_shipping.get("amount") else None,
        total_shipping.get("currencyCode"),
        order_data.get("financialStatus"),
        order_data.get("fulfillmentStatus"),
        order_data.get("tags", []),
        order_data.get("note"),
        json.dumps(order_data.get("customerJourneySummary", {})),
        json.dumps(order_data),
        datetime.now()
    )
    
    await db_manager.execute_query(query, params)

async def upsert_line_item(db_manager: DatabaseManager, line_item_data: Dict[str, Any]) -> None:
    """Upsert line item data into the database"""
    query = """
        INSERT INTO shopify_order_line_items (
            id, order_id, name, quantity, original_total_amount, original_total_currency_code,
            variant_id, variant_title, variant_price, variant_sku, product_id, product_title,
            product_handle, product_type, product_vendor, raw_data, synced_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            quantity = EXCLUDED.quantity,
            original_total_amount = EXCLUDED.original_total_amount,
            original_total_currency_code = EXCLUDED.original_total_currency_code,
            variant_id = EXCLUDED.variant_id,
            variant_title = EXCLUDED.variant_title,
            variant_price = EXCLUDED.variant_price,
            variant_sku = EXCLUDED.variant_sku,
            product_id = EXCLUDED.product_id,
            product_title = EXCLUDED.product_title,
            product_handle = EXCLUDED.product_handle,
            product_type = EXCLUDED.product_type,
            product_vendor = EXCLUDED.product_vendor,
            raw_data = EXCLUDED.raw_data,
            synced_at = EXCLUDED.synced_at
    """
    
    # Extract variant and product information
    variant = line_item_data.get("variant", {})
    product = variant.get("product", {})
    original_total = line_item_data.get("originalTotalSet", {}).get("shopMoney", {})
    
    params = (
        line_item_data["id"],
        line_item_data.get("order_id"),
        line_item_data.get("name"),
        line_item_data.get("quantity"),
        float(original_total.get("amount", 0)) if original_total.get("amount") else None,
        original_total.get("currencyCode"),
        variant.get("id"),
        variant.get("title"),
        float(variant.get("price", 0)) if variant.get("price") else None,
        variant.get("sku"),
        product.get("id"),
        product.get("title"),
        product.get("handle"),
        product.get("productType"),
        product.get("vendor"),
        json.dumps(line_item_data),
        datetime.now()
    )
    
    await db_manager.execute_query(query, params)

async def upsert_customer_journey(
    db_manager: DatabaseManager, 
    customer_id: str, 
    order_id: str, 
    journey_data: Dict[str, Any]
) -> None:
    """Upsert customer journey data into the database"""
    if not journey_data:
        return
    
    # Process first visit
    first_visit = journey_data.get("firstVisit", {})
    if first_visit:
        await upsert_journey_moment(
            db_manager, customer_id, order_id, "first_visit", first_visit
        )
    
    # Process last visit
    last_visit = journey_data.get("lastVisit", {})
    if last_visit:
        await upsert_journey_moment(
            db_manager, customer_id, order_id, "last_visit", last_visit
        )

async def upsert_journey_moment(
    db_manager: DatabaseManager,
    customer_id: str,
    order_id: str,
    moment_type: str,
    moment_data: Dict[str, Any]
) -> None:
    """Upsert individual customer journey moment"""
    query = """
        INSERT INTO shopify_customer_journey_moments (
            customer_id, order_id, moment_type, occurred_at, source, medium, campaign,
            content, term, landing_page, referrer, raw_data, synced_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (customer_id, order_id, moment_type) DO UPDATE SET
            occurred_at = EXCLUDED.occurred_at,
            source = EXCLUDED.source,
            medium = EXCLUDED.medium,
            campaign = EXCLUDED.campaign,
            content = EXCLUDED.content,
            term = EXCLUDED.term,
            landing_page = EXCLUDED.landing_page,
            referrer = EXCLUDED.referrer,
            raw_data = EXCLUDED.raw_data,
            synced_at = EXCLUDED.synced_at
    """
    
    # Extract UTM parameters
    utm_params = moment_data.get("utmParameters", {})
    
    # For this example, we'll use the current time since occurred_at isn't directly available
    occurred_at = datetime.now()
    
    params = (
        customer_id,
        order_id,
        moment_type,
        occurred_at,
        moment_data.get("source"),
        utm_params.get("medium"),
        utm_params.get("campaign"),
        utm_params.get("content"),
        utm_params.get("term"),
        moment_data.get("landingPage"),
        moment_data.get("referrer"),
        json.dumps(moment_data),
        datetime.now()
    )
    
    await db_manager.execute_query(query, params)

async def calculate_customer_analytics(
    db_manager: DatabaseManager, 
    customer_ids: Optional[List[str]] = None
) -> None:
    """Calculate and update customer analytics"""
    if customer_ids:
        # Update analytics for specific customers
        customer_filter = f"WHERE c.id = ANY($1)"
        params = [customer_ids]
    else:
        # Update analytics for all customers
        customer_filter = ""
        params = []
    
    query = f"""
        INSERT INTO shopify_customer_analytics (
            customer_id, total_orders, total_spent_amount, total_spent_currency,
            average_order_value, first_order_date, last_order_date, days_since_last_order,
            customer_lifetime_days, total_line_items, unique_products_purchased,
            calculated_at, synced_at
        )
        SELECT 
            c.id,
            COUNT(DISTINCT o.id) as total_orders,
            SUM(o.total_price_amount) as total_spent_amount,
            c.total_spent_currency_code,
            AVG(o.total_price_amount) as average_order_value,
            MIN(o.created_at) as first_order_date,
            MAX(o.created_at) as last_order_date,
            EXTRACT(DAYS FROM NOW() - MAX(o.created_at)) as days_since_last_order,
            EXTRACT(DAYS FROM NOW() - c.created_at) as customer_lifetime_days,
            COUNT(li.id) as total_line_items,
            COUNT(DISTINCT li.product_id) as unique_products_purchased,
            NOW() as calculated_at,
            NOW() as synced_at
        FROM shopify_customers c
        LEFT JOIN shopify_orders o ON c.id = o.customer_id
        LEFT JOIN shopify_order_line_items li ON o.id = li.order_id
        {customer_filter}
        GROUP BY c.id, c.total_spent_currency_code, c.created_at
        ON CONFLICT (customer_id) DO UPDATE SET
            total_orders = EXCLUDED.total_orders,
            total_spent_amount = EXCLUDED.total_spent_amount,
            average_order_value = EXCLUDED.average_order_value,
            first_order_date = EXCLUDED.first_order_date,
            last_order_date = EXCLUDED.last_order_date,
            days_since_last_order = EXCLUDED.days_since_last_order,
            customer_lifetime_days = EXCLUDED.customer_lifetime_days,
            total_line_items = EXCLUDED.total_line_items,
            unique_products_purchased = EXCLUDED.unique_products_purchased,
            calculated_at = EXCLUDED.calculated_at,
            synced_at = EXCLUDED.synced_at
    """
    
    await db_manager.execute_query(query, params)

# Data Validation Task
@task(dag=dag)
def validate_past_purchases_data(**context) -> Dict[str, Any]:
    """
    Validate past purchases data quality
    
    Returns:
        Dictionary with validation results
    """
    logger.info("Starting past purchases data validation")
    
    async def validate_data():
        db_manager = DatabaseManager()
        try:
            await db_manager.connect()
            
            validation_results = {
                "total_customers": 0,
                "total_orders": 0,
                "total_line_items": 0,
                "validation_checks": [],
                "passed_checks": 0,
                "failed_checks": 0,
                "overall_status": "PASSED"
            }
            
            # Get counts
            validation_results["total_customers"] = await db_manager.get_customers_count()
            validation_results["total_orders"] = await db_manager.get_orders_count()
            
            # Get line items count
            line_items_result = await db_manager.execute_query(
                "SELECT COUNT(*) as count FROM shopify_order_line_items", 
                fetch=True
            )
            validation_results["total_line_items"] = line_items_result[0]["count"] if line_items_result else 0
            
            # Validation checks
            checks = [
                {
                    "name": "customers_with_orders",
                    "query": "SELECT COUNT(*) FROM shopify_customers WHERE id IN (SELECT DISTINCT customer_id FROM shopify_orders)",
                    "description": "Customers with at least one order"
                },
                {
                    "name": "orders_with_line_items",
                    "query": "SELECT COUNT(*) FROM shopify_orders WHERE id IN (SELECT DISTINCT order_id FROM shopify_order_line_items)",
                    "description": "Orders with line items"
                },
                {
                    "name": "recent_sync_customers",
                    "query": "SELECT COUNT(*) FROM shopify_customers WHERE synced_at >= NOW() - INTERVAL '24 hours'",
                    "description": "Recently synced customers"
                },
                {
                    "name": "recent_sync_orders",
                    "query": "SELECT COUNT(*) FROM shopify_orders WHERE synced_at >= NOW() - INTERVAL '24 hours'",
                    "description": "Recently synced orders"
                },
                {
                    "name": "customers_with_email",
                    "query": "SELECT COUNT(*) FROM shopify_customers WHERE email IS NOT NULL AND email != ''",
                    "description": "Customers with email addresses"
                },
                {
                    "name": "orders_with_total_price",
                    "query": "SELECT COUNT(*) FROM shopify_orders WHERE total_price_amount > 0",
                    "description": "Orders with positive total price"
                }
            ]
            
            for check in checks:
                try:
                    result = await db_manager.execute_query(check["query"], fetch=True)
                    count = result[0]["count"] if result else 0
                    
                    check_result = {
                        "name": check["name"],
                        "description": check["description"],
                        "count": count,
                        "status": "PASSED" if count > 0 else "FAILED"
                    }
                    
                    validation_results["validation_checks"].append(check_result)
                    
                    if check_result["status"] == "PASSED":
                        validation_results["passed_checks"] += 1
                    else:
                        validation_results["failed_checks"] += 1
                        validation_results["overall_status"] = "FAILED"
                        
                except Exception as e:
                    check_result = {
                        "name": check["name"],
                        "description": check["description"],
                        "error": str(e),
                        "status": "FAILED"
                    }
                    validation_results["validation_checks"].append(check_result)
                    validation_results["failed_checks"] += 1
                    validation_results["overall_status"] = "FAILED"
            
            return validation_results
            
        finally:
            await db_manager.close()
    
    result = asyncio.run(validate_data())
    
    logger.info(f"Past purchases data validation completed: {result}")
    return result

# Reporting Task
@task(dag=dag)
def generate_sync_report(**context) -> Dict[str, Any]:
    """
    Generate comprehensive sync report
    
    Returns:
        Dictionary with sync report data
    """
    logger.info("Generating past purchases sync report")
    
    async def generate_report():
        db_manager = DatabaseManager()
        try:
            await db_manager.connect()
            
            # Get basic statistics
            customers_count = await db_manager.get_customers_count()
            orders_count = await db_manager.get_orders_count()
            
            # Get line items count
            line_items_result = await db_manager.execute_query(
                "SELECT COUNT(*) as count FROM shopify_order_line_items", 
                fetch=True
            )
            line_items_count = line_items_result[0]["count"] if line_items_result else 0
            
            # Get customer analytics summary
            analytics_result = await db_manager.execute_query("""
                SELECT 
                    COUNT(*) as customers_with_analytics,
                    AVG(total_orders) as avg_orders_per_customer,
                    AVG(total_spent_amount) as avg_customer_value,
                    AVG(average_order_value) as avg_order_value
                FROM shopify_customer_analytics
            """, fetch=True)
            
            analytics_summary = analytics_result[0] if analytics_result else {}
            
            # Get recent activity
            recent_activity = await db_manager.execute_query("""
                SELECT 
                    COUNT(DISTINCT customer_id) as recent_customers,
                    COUNT(*) as recent_orders
                FROM shopify_orders 
                WHERE created_at >= NOW() - INTERVAL '7 days'
            """, fetch=True)
            
            recent_stats = recent_activity[0] if recent_activity else {}
            
            report = {
                "sync_timestamp": datetime.now().isoformat(),
                "basic_stats": {
                    "total_customers": customers_count,
                    "total_orders": orders_count,
                    "total_line_items": line_items_count
                },
                "customer_analytics": {
                    "customers_with_analytics": analytics_summary.get("customers_with_analytics", 0),
                    "avg_orders_per_customer": float(analytics_summary.get("avg_orders_per_customer", 0) or 0),
                    "avg_customer_value": float(analytics_summary.get("avg_customer_value", 0) or 0),
                    "avg_order_value": float(analytics_summary.get("avg_order_value", 0) or 0)
                },
                "recent_activity": {
                    "recent_customers": recent_stats.get("recent_customers", 0),
                    "recent_orders": recent_stats.get("recent_orders", 0)
                },
                "report_status": "SUCCESS"
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate sync report: {str(e)}")
            return {"report_status": "FAILED", "error": str(e)}
        finally:
            await db_manager.close()
    
    report = asyncio.run(generate_report())
    
    logger.info(f"Past purchases sync report generated: {report}")
    return report

# Pipeline End
pipeline_end = EmptyOperator(
    task_id="pipeline_end",
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    dag=dag,
)

# Set up task dependencies
config = get_sync_config()
validation = validate_connections()
database_prep = prepare_database_tables()

# Main pipeline flow
config >> validation >> database_prep >> sync_mode_decision

# Full sync path
full_sync_group = full_sync_operations()
sync_mode_decision >> full_sync_group

# Incremental sync path
incremental_sync_group = incremental_sync_operations()
sync_mode_decision >> incremental_sync_group

# Validation and reporting
data_validation = validate_past_purchases_data()
sync_report = generate_sync_report()

# Connect sync operations to validation and reporting
[full_sync_group, incremental_sync_group] >> data_validation >> sync_report >> pipeline_end

if __name__ == "__main__":
    dag.test()