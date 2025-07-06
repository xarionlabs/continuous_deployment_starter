from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow.models import Variable
from airflow.exceptions import AirflowSkipException

import logging
# Assuming shopify_common.py is in the same directory or PYTHONPATH is set up
from shopify_common import get_shopify_session, bulk_insert_to_app_db, APP_DB_CONN_ID, get_app_db_hook

logger = logging.getLogger(__name__)

# --- DAG Configuration ---
DAG_ID = "shopify_fetch_past_purchases"
DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime.now() - timedelta(days=1), # Default start date
}
SCHEDULE_INTERVAL = None # Manually triggered or via API
CATCHUP = False
TAGS = ["shopify", "data_fetch", "purchases"]

# --- DAG-specific Variables ---
# How far back to look for orders if no last_run_timestamp is available
# Can be overridden by Airflow Variable "shopify_orders_initial_lookback_days"
INITIAL_LOOKBACK_DAYS = int(Variable.get("shopify_orders_initial_lookback_days", default_var=30))
ORDERS_PER_PAGE_LIMIT = 250 # Max allowed by Shopify for Order resource

# --- Database Table Configuration ---
# This should match your Prisma schema or database table structure
ORDERS_TABLE_NAME = Variable.get("shopify_orders_table_name", default_var="ShopifyOrder")
ORDER_LINE_ITEMS_TABLE_NAME = Variable.get("shopify_order_line_items_table_name", default_var="ShopifyOrderLineItem")
# Define columns carefully, matching your DB schema. Ensure datatypes are compatible.
# Example columns - customize these extensively!
ORDER_COLUMNS = [
    "id", "shop_id", "customer_id", "email", "total_price", "subtotal_price",
    "total_tax", "total_discounts", "currency", "financial_status",
    "fulfillment_status", "processed_at", "created_at", "updated_at",
    "landing_site", "referring_site", "source_name", "tags"
    # Add any other fields you need from the Shopify Order object
]
LINE_ITEM_COLUMNS = [
    "id", "order_id", "shop_id", "product_id", "variant_id", "title", "quantity",
    "sku", "vendor", "price", "total_discount", "taxable", "fulfillment_status"
    # Add any other fields you need from the LineItem object
]


def get_last_successful_run_timestamp(**kwargs):
    """
    Retrieves the last successful run timestamp for this DAG to determine the data fetch window.
    If not found, returns a timestamp based on INITIAL_LOOKBACK_DAYS.
    This uses Airflow's internal metadata DB, not the application DB.
    """
    ti = kwargs['ti']
    dag_run = ti.get_dagrun()
    prev_success_run = dag_run.get_previous_dagrun(state='success')

    if prev_success_run:
        last_run_ts = prev_success_run.execution_date
        logger.info(f"Last successful run was at: {last_run_ts}")
        # Add a small overlap to avoid missing records due to timing issues
        return last_run_ts - timedelta(minutes=5)
    else:
        logger.info(f"No previous successful run found. Using initial lookback of {INITIAL_LOOKBACK_DAYS} days.")
        return datetime.utcnow() - timedelta(days=INITIAL_LOOKBACK_DAYS)

def fetch_shopify_orders_task(**kwargs):
    """
    Fetches orders from Shopify since the last successful run or initial lookback period.
    """
    ti = kwargs['ti']
    # Get the 'since' timestamp from XComs (pushed by get_last_successful_run_timestamp_task)
    # or from the DAG run conf if triggered with specific dates
    dag_run_conf = kwargs.get('dag_run', {}).conf or {}
    start_date_str = dag_run_conf.get('start_date')
    end_date_str = dag_run_conf.get('end_date') # Exclusive

    if start_date_str:
        processed_at_min = datetime.fromisoformat(start_date_str)
        logger.info(f"Using provided start_date: {processed_at_min.isoformat()}")
    else:
        processed_at_min = get_last_successful_run_timestamp(**kwargs) # Use internal logic
        logger.info(f"Calculated processed_at_min: {processed_at_min.isoformat()}")

    if end_date_str:
        processed_at_max = datetime.fromisoformat(end_date_str)
        logger.info(f"Using provided end_date: {processed_at_max.isoformat()}")
    else:
        processed_at_max = datetime.utcnow() # Fetch up to now if no end_date
        logger.info(f"Defaulting end_date to current UTC time: {processed_at_max.isoformat()}")

    if processed_at_min >= processed_at_max:
        logger.info(f"Start date {processed_at_min} is not before end date {processed_at_max}. Skipping.")
        raise AirflowSkipException("Start date is not before end date.")

    all_orders_data = []
    all_line_items_data = []
    page_count = 1

    with get_shopify_session() as shopify_api:
        shop_details = shopify_api.Shop.current() # Get shop_id
        shop_id = shop_details.id
        logger.info(f"Fetching orders for shop ID: {shop_id} processed between {processed_at_min.isoformat()} and {processed_at_max.isoformat()}")

        # Shopify API uses 'processed_at' for when an order was authorized/charged.
        # 'created_at' is when the order object was created (could be a draft).
        # 'updated_at' is the last modification.
        # For "past purchases" `processed_at` or `created_at` with financial_status 'paid' might be suitable.
        # Let's use `updated_at_min` to catch changes, and filter by financial status if needed.
        # Shopify filters: created_at_min, created_at_max, updated_at_min, updated_at_max, processed_at_min, processed_at_max
        # status='any' to get all orders regardless of open/closed/cancelled. Can be filtered later.

        # Using updated_at_min to catch any order changes since last run.
        # If an order is created and paid after processed_at_min, it's caught.
        # If an old order is updated (e.g., refund, fulfillment), it's also caught.
        # This means we might re-fetch and re-process some orders, so the load task needs to handle upserts.
        orders_page = shopify_api.Order.find(
            limit=ORDERS_PER_PAGE_LIMIT,
            updated_at_min=processed_at_min.isoformat(), # Catches new and updated orders
            # processed_at_max=processed_at_max.isoformat(), # Careful: if an order is processed later, it might be missed
            status='any', # Get all orders and filter/handle status downstream
            order='updated_at asc' # Process in order of update
        )

        while orders_page:
            logger.info(f"Processing page {page_count} of orders...")
            for order in orders_page:
                # Additional filter: ensure order.updated_at is within the window if using updated_at_min broadly
                # Shopify's updated_at_min should handle this, but good for sanity.
                # Also, if an order was updated but its processed_at is outside a strict processed_at window,
                # you might want to skip it depending on requirements.
                # For this example, we take any order updated in the window.

                order_data = {col: getattr(order, col, None) for col in ORDER_COLUMNS if hasattr(order, col)}
                # Ensure all defined columns are present, even if None
                for col in ORDER_COLUMNS:
                    if col not in order_data:
                        order_data[col] = None

                order_data['id'] = order.id # Primary key
                order_data['shop_id'] = shop_id
                order_data['customer_id'] = order.customer.id if order.customer else None

                # Handle datetimes - convert to ISO format string or specific DB format
                for dt_field in ["processed_at", "created_at", "updated_at"]:
                    if order_data.get(dt_field):
                        # Assuming DB expects ISO format strings for datetime fields
                        order_data[dt_field] = pd.to_datetime(order_data[dt_field]).isoformat()


                # Flatten complex fields or extract specific parts
                # Example: order_data['customer_email'] = order.customer.email if order.customer else None
                # Ensure data types match DB schema (e.g., prices as numeric)
                for price_field in ["total_price", "subtotal_price", "total_tax", "total_discounts"]:
                    if order_data.get(price_field):
                        order_data[price_field] = float(order_data[price_field])


                all_orders_data.append(tuple(order_data.get(col) for col in ORDER_COLUMNS))

                for li in order.line_items:
                    line_item_data = {col: getattr(li, col, None) for col in LINE_ITEM_COLUMNS if hasattr(li, col)}
                    for col in LINE_ITEM_COLUMNS:
                        if col not in line_item_data:
                            line_item_data[col] = None

                    line_item_data['id'] = li.id # Primary key
                    line_item_data['order_id'] = order.id # Foreign key
                    line_item_data['shop_id'] = shop_id

                    if line_item_data.get('price'):
                         line_item_data['price'] = float(line_item_data['price'])
                    if line_item_data.get('total_discount'):
                         line_item_data['total_discount'] = float(line_item_data['total_discount'])

                    all_line_items_data.append(tuple(line_item_data.get(col) for col in LINE_ITEM_COLUMNS))

            if orders_page.has_next_page():
                orders_page = orders_page.next_page()
                page_count += 1
            else:
                break

    logger.info(f"Fetched {len(all_orders_data)} orders and {len(all_line_items_data)} line items.")

    # Push to XComs for the next task
    # Note: XComs have size limits. For very large datasets, consider staging to S3/GCS.
    ti.xcom_push(key="orders_data", value=all_orders_data)
    ti.xcom_push(key="line_items_data", value=all_line_items_data)

    if not all_orders_data:
        logger.info("No new or updated orders found in the given timeframe.")
        # raise AirflowSkipException("No new or updated orders to process.") # Option: skip downstream if no data

def load_orders_to_db_task(**kwargs):
    """
    Loads fetched order data into the application's PostgreSQL database.
    This task should handle upserts (insert new, update existing).
    """
    ti = kwargs['ti']
    orders_data = ti.xcom_pull(task_ids="fetch_shopify_orders", key="orders_data")

    if not orders_data:
        logger.info("No order data to load. Skipping DB operation.")
        return

    logger.info(f"Received {len(orders_data)} orders to load into table '{ORDERS_TABLE_NAME}'.")

    # For simplicity, this example uses bulk_insert_to_app_db.
    # In a real scenario, you'd need an UPSERT mechanism.
    # PostgreSQL's ON CONFLICT DO UPDATE is common.
    # This might involve:
    # 1. Loading data to a staging table.
    # 2. Performing a MERGE or INSERT...ON CONFLICT from staging to the final table.
    # Or, constructing dynamic SQL for ON CONFLICT if PostgresHook doesn't support it directly for insert_rows.

    # Example of direct insert (will fail on primary key conflict if not handled)
    # For a true upsert, you would need more sophisticated SQL or a helper function.
    # The `shopify_common.bulk_insert_to_app_db` uses `insert_rows` which typically doesn't handle conflicts.
    # You might need to write custom SQL with ON CONFLICT.

    # TEMPORARY: Simple insert. Replace with robust upsert logic.
    # Option: Delete records within the fetched ID range first, then insert. (Risky if process fails mid-way)
    # Option: Use a custom hook method or raw SQL for ON CONFLICT.

    # For now, let's assume we are only inserting new records or the table is cleared/managed elsewhere.
    # A proper solution requires an "upsert" strategy.
    # Example: If order_id is the primary key for ORDERS_TABLE_NAME
    # SQL for upsert:
    # INSERT INTO ShopifyOrder (id, shop_id, ...) VALUES (%s, %s, ...)
    # ON CONFLICT (id) DO UPDATE SET shop_id = EXCLUDED.shop_id, ...;

    # Using the simple bulk_insert for now. This will fail if an order ID already exists
    # and there's a primary key constraint.
    # TODO: Implement a proper upsert strategy.

    # Get a DB hook
    db_hook = get_app_db_hook()
    conn = None
    try:
        conn = db_hook.get_conn()
        cursor = conn.cursor()

        # Prepare for UPSERT
        # Assuming 'id' is the primary key for ORDERS_TABLE_NAME
        # And ORDER_COLUMNS lists all columns in the correct order for orders_data tuples
        cols_str = ", ".join(ORDER_COLUMNS)
        val_placeholders = ", ".join(["%s"] * len(ORDER_COLUMNS))

        # Construct the SET part of the ON CONFLICT statement
        update_cols = [f"{col} = EXCLUDED.{col}" for col in ORDER_COLUMNS if col != "id"]
        update_set_str = ", ".join(update_cols)

        upsert_sql = f"""
        INSERT INTO {ORDERS_TABLE_NAME} ({cols_str})
        VALUES ({val_placeholders})
        ON CONFLICT (id) DO UPDATE
        SET {update_set_str};
        """

        logger.info(f"Executing UPSERT for {len(orders_data)} orders into {ORDERS_TABLE_NAME}...")
        # db_hook.run() can execute SQL, but for many records, psycopg2's execute_batch or executemany is better.
        # Using executemany for efficiency with UPSERT
        cursor.executemany(upsert_sql, orders_data)
        conn.commit()
        logger.info(f"Successfully upserted {len(orders_data)} orders.")

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error loading orders to DB: {e}")
        raise
    finally:
        if conn:
            cursor.close()
            conn.close()


def load_line_items_to_db_task(**kwargs):
    """
    Loads fetched order line item data into the application's PostgreSQL database.
    Handles upserts for line items.
    """
    ti = kwargs['ti']
    line_items_data = ti.xcom_pull(task_ids="fetch_shopify_orders", key="line_items_data")

    if not line_items_data:
        logger.info("No line item data to load. Skipping DB operation.")
        return

    logger.info(f"Received {len(line_items_data)} line items to load into table '{ORDER_LINE_ITEMS_TABLE_NAME}'.")

    # Similar to orders, implement robust UPSERT logic.
    # Assuming 'id' is the primary key for ORDER_LINE_ITEMS_TABLE_NAME
    # And 'order_id' is a foreign key to ORDERS_TABLE_NAME

    db_hook = get_app_db_hook()
    conn = None
    try:
        conn = db_hook.get_conn()
        cursor = conn.cursor()

        cols_str = ", ".join(LINE_ITEM_COLUMNS)
        val_placeholders = ", ".join(["%s"] * len(LINE_ITEM_COLUMNS))
        update_cols = [f"{col} = EXCLUDED.{col}" for col in LINE_ITEM_COLUMNS if col != "id"]
        update_set_str = ", ".join(update_cols)

        upsert_sql = f"""
        INSERT INTO {ORDER_LINE_ITEMS_TABLE_NAME} ({cols_str})
        VALUES ({val_placeholders})
        ON CONFLICT (id) DO UPDATE
        SET {update_set_str};
        """

        logger.info(f"Executing UPSERT for {len(line_items_data)} line items into {ORDER_LINE_ITEMS_TABLE_NAME}...")
        cursor.executemany(upsert_sql, line_items_data)
        conn.commit()
        logger.info(f"Successfully upserted {len(line_items_data)} line items.")

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error loading line items to DB: {e}")
        raise
    finally:
        if conn:
            cursor.close()
            conn.close()


# --- DAG Definition ---
with DAG(
    dag_id=DAG_ID,
    default_args=DEFAULT_ARGS,
    schedule=SCHEDULE_INTERVAL,
    catchup=CATCHUP,
    tags=TAGS,
    doc_md=__doc__ # Adds this file's docstring to the Airflow UI
) as dag:

    # Task to determine the data fetch window (e.g., since last successful run)
    # This is implicitly handled by fetch_shopify_orders_task now
    # get_run_parameters_task = PythonOperator(
    #     task_id="get_run_parameters",
    #     python_callable=get_last_successful_run_timestamp,
    # )

    fetch_orders_python_task = PythonOperator(
        task_id="fetch_shopify_orders",
        python_callable=fetch_shopify_orders_task,
        # op_kwargs can be used to pass static params if needed
    )

    load_orders_python_task = PythonOperator(
        task_id="load_orders_to_db",
        python_callable=load_orders_to_db_task,
    )

    load_line_items_python_task = PythonOperator(
        task_id="load_line_items_to_db",
        python_callable=load_line_items_to_db_task,
    )

    # Define task dependencies
    # get_run_parameters_task >> fetch_orders_python_task
    fetch_orders_python_task >> [load_orders_python_task, load_line_items_python_task]

# Import pandas for date conversion if not already available
try:
    import pandas as pd
except ImportError:
    logger.warning("Pandas library is not installed. Datetime conversion in fetch_shopify_orders_task might need adjustment.")
    # Create a dummy pd.to_datetime if pandas is not available, or handle conversion differently
    class pd: # Minimal mock
        @staticmethod
        def to_datetime(dt_str):
            if isinstance(dt_str, datetime):
                return dt_str
            # Basic ISO format parsing, add more robust parsing if needed without pandas
            try:
                return datetime.fromisoformat(str(dt_str).replace('Z', '+00:00'))
            except:
                 # Attempt to parse with common Shopify format if fromisoformat fails
                try:
                    return datetime.strptime(str(dt_str), '%Y-%m-%dT%H:%M:%S%z')
                except:
                    logger.error(f"Failed to parse datetime string: {dt_str}")
                    return None
