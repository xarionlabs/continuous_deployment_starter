"""
Shopify Data Sync DAG

Simple Airflow DAG for synchronizing Shopify data (customers, orders, products) 
to the PXY6 database. Follows Airflow best practices with clear, linear task flow.

Schedule: Daily at 2:00 AM UTC
"""

from datetime import datetime, timedelta
from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
import structlog

from pxy6.hooks.shopify_hook import ShopifyHook
from pxy6.utils.database import (
    upsert_customer,
    upsert_product,
    upsert_order,
    upsert_product_variant,
    upsert_product_image,
    upsert_sync_log,
    upsert_sync_state,
)

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
        dag_run_conf = context["dag_run"].conf or {}
        shop_domain = dag_run_conf.get("shop_domain")
        
        if not shop_domain:
            raise AirflowException("Shop domain is required for sync operations")

        # Initialize hook with DAG configuration
        hook = ShopifyHook()
        hook.setup_with_dag_config(dag_run_conf)

        # Test connection first
        if not hook.test_connection():
            hook.close()
            raise AirflowException(f"Failed to connect to Shopify shop: {shop_domain}")

        try:
            # Extract customers using the hook
            customers_data = hook.paginate_customers_with_orders(batch_size=100)

            # Load customers to database
            for customer in customers_data:
                try:
                    upsert_customer(customer, shop_domain)
                except Exception as e:
                    logger.error(f"Failed to upsert customer {customer.get('id', 'unknown')}: {str(e)}")
                    hook.close()
                    raise AirflowException(f"Database error while upserting customer: {str(e)}")

            logger.info(
                f"Successfully synced {len(customers_data)} customers for shop: {dag_run_conf.get('shop_domain')}"
            )
            result = {"customers_synced": len(customers_data)}

        except AirflowException:
            # Re-raise Airflow exceptions to properly fail the task
            raise
        except Exception as e:
            logger.error(f"Unexpected error during customer sync: {str(e)}")
            hook.close()
            raise AirflowException(f"Customer sync failed: {str(e)}")
        finally:
            hook.close()

        logger.info(f"Customer sync completed: {result}")
        return result

    @task
    def sync_orders(**context) -> dict:
        """Extract and load order data from Shopify"""
        logger.info("Starting order sync")

        # Get DAG run configuration
        dag_run_conf = context["dag_run"].conf or {}
        shop_domain = dag_run_conf.get("shop_domain")
        
        if not shop_domain:
            raise AirflowException("Shop domain is required for sync operations")

        # Initialize hook with DAG configuration
        hook = ShopifyHook()
        hook.setup_with_dag_config(dag_run_conf)

        # Test connection first
        if not hook.test_connection():
            hook.close()
            raise AirflowException(f"Failed to connect to Shopify shop: {shop_domain}")

        try:
            # For now, get all customers with orders (which includes order data)
            # This will be more efficient than a separate orders query for most shops
            customers_with_orders = hook.paginate_customers_with_orders(batch_size=100)

            # Extract order data from customers
            orders_data = []
            for customer in customers_with_orders:
                customer_orders = customer.get("orders", {}).get("edges", [])
                for order_edge in customer_orders:
                    order = order_edge["node"]
                    # Include all orders (no time limitation)
                    orders_data.append(order)

            # Load orders to database
            orders_count = 0
            for order in orders_data:
                try:
                    upsert_order(order, shop_domain)
                    orders_count += 1
                except Exception as e:
                    logger.error(f"Failed to upsert order {order.get('id', 'unknown')}: {str(e)}")
                    hook.close()
                    raise AirflowException(f"Database error while upserting order: {str(e)}")

            logger.info(f"Successfully synced {orders_count} orders for shop: {dag_run_conf.get('shop_domain')}")
            result = {"orders_synced": orders_count}

        except AirflowException:
            # Re-raise Airflow exceptions to properly fail the task
            raise
        except Exception as e:
            logger.error(f"Unexpected error during order sync: {str(e)}")
            hook.close()
            raise AirflowException(f"Order sync failed: {str(e)}")
        finally:
            hook.close()

        logger.info(f"Order sync completed: {result}")
        return result

    @task
    def sync_products(**context) -> dict:
        """Extract and load product data from Shopify"""
        logger.info("Starting product sync")

        # Get DAG run configuration
        dag_run_conf = context["dag_run"].conf or {}
        shop_domain = dag_run_conf.get("shop_domain")
        
        if not shop_domain:
            raise AirflowException("Shop domain is required for sync operations")

        # Initialize hook with DAG configuration
        hook = ShopifyHook()
        hook.setup_with_dag_config(dag_run_conf)

        # Test connection first
        if not hook.test_connection():
            hook.close()
            raise AirflowException(f"Failed to connect to Shopify shop: {shop_domain}")

        try:
            # Extract products using the hook
            products_data = hook.paginate_all_product_data(batch_size=50)

            # Load products to database
            products_count = 0
            for product in products_data:
                try:
                    upsert_product(product, shop_domain)
                    products_count += 1

                    # Sync product variants
                    variants = product.get("variants", {}).get("edges", [])
                    for variant_edge in variants:
                        variant = variant_edge["node"]
                        variant["product_id"] = product["id"]
                        try:
                            upsert_product_variant(variant, shop_domain)
                        except Exception as e:
                            logger.error(f"Failed to upsert product variant {variant.get('id', 'unknown')}: {str(e)}")
                            hook.close()
                            raise AirflowException(f"Database error while upserting product variant: {str(e)}")

                    # Sync product images from media field
                    media_items = product.get("media", {}).get("edges", [])
                    for media_edge in media_items:
                        media = media_edge["node"]
                        # Only process MediaImage items
                        if media.get("mediaContentType") == "IMAGE" and media.get("image"):
                            image_data = {
                                "id": media.get("id"),
                                "product_id": product["id"],
                                "src": media.get("image", {}).get("url"),
                                "altText": media.get("alt"),
                                "width": media.get("image", {}).get("width"),
                                "height": media.get("image", {}).get("height"),
                                "position": None,  # Media doesn't have position in this query
                                "legacyResourceId": None,
                                "createdAt": None,  # Media doesn't have created/updated in this query
                                "updatedAt": None,
                            }
                            try:
                                upsert_product_image(image_data, shop_domain)
                            except Exception as e:
                                logger.error(
                                    f"Failed to upsert product image {image_data.get('id', 'unknown')}: {str(e)}"
                                )
                                hook.close()
                                raise AirflowException(f"Database error while upserting product image: {str(e)}")

                except Exception as e:
                    logger.error(f"Failed to upsert product {product.get('id', 'unknown')}: {str(e)}")
                    hook.close()
                    raise AirflowException(f"Database error while upserting product: {str(e)}")

            logger.info(f"Successfully synced {products_count} products for shop: {dag_run_conf.get('shop_domain')}")
            result = {"products_synced": products_count}

        except AirflowException:
            # Re-raise Airflow exceptions to properly fail the task
            raise
        except Exception as e:
            logger.error(f"Unexpected error during product sync: {str(e)}")
            hook.close()
            raise AirflowException(f"Product sync failed: {str(e)}")
        finally:
            hook.close()

        logger.info(f"Product sync completed: {result}")
        return result

    @task
    def generate_sync_summary(customer_result: dict, order_result: dict, product_result: dict, **context) -> dict:
        """Generate summary of sync operation and update sync tracking tables"""
        try:
            # Get DAG run configuration
            dag_run_conf = context["dag_run"].conf or {}
            shop_domain = dag_run_conf.get("shop_domain")
            
            if not shop_domain:
                raise AirflowException("Shop domain is required for sync tracking")

            summary = {
                "sync_timestamp": datetime.now().isoformat(),
                "customers_synced": customer_result.get("customers_synced", 0),
                "orders_synced": order_result.get("orders_synced", 0),
                "products_synced": product_result.get("products_synced", 0),
                "status": "completed",
                "shop": shop_domain,
            }

            # Record sync states for each entity type
            sync_time = datetime.now()

            # Update sync states
            upsert_sync_state("customers", shop_domain, sync_time)
            upsert_sync_state("orders", shop_domain, sync_time)
            upsert_sync_state("products", shop_domain, sync_time)

            # Record overall sync log
            total_records = summary["customers_synced"] + summary["orders_synced"] + summary["products_synced"]
            upsert_sync_log(
                entity_type="all",
                operation="full_sync",
                status="completed",
                shop=shop_domain,
                records_processed=total_records,
                records_created=total_records,  # Assuming upserts create new records
                records_updated=0,
            )

            logger.info(f"Sync summary: {summary}")
            return summary

        except Exception as e:
            logger.error(f"Failed to generate sync summary: {str(e)}")
            # Record failed sync log
            dag_run_conf = context.get("dag_run", {}).conf or {}
            shop_domain = dag_run_conf.get("shop_domain", "unknown")
            upsert_sync_log(entity_type="all", operation="full_sync", status="failed", shop=shop_domain, error_message=str(e))
            raise AirflowException(f"Failed to generate sync summary: {str(e)}")

    # Define task dependencies
    customers = sync_customers()
    orders = sync_orders()
    products = sync_products()
    summary = generate_sync_summary(customers, orders, products)

    # Linear dependency chain
    [customers, orders, products] >> summary


# Instantiate the DAG
shopify_sync_dag()
