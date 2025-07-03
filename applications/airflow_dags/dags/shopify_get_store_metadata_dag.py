from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from airflow.models import Variable
from airflow.exceptions import AirflowSkipException

import logging
from datetime import datetime, timedelta
from shopify_common import get_shopify_session, bulk_insert_to_app_db, APP_DB_CONN_ID, get_app_db_hook

logger = logging.getLogger(__name__)

# --- DAG Configuration ---
DAG_ID = "shopify_fetch_store_metadata"
DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}
SCHEDULE_INTERVAL = "@daily" # Or as frequently as you need to update metadata
CATCHUP = False # Set to True if you want to backfill runs
TAGS = ["shopify", "data_fetch", "metadata", "products", "collections"]

# --- Database Table Configuration ---
# These should match your Prisma schema or database table structure
PRODUCTS_TABLE_NAME = Variable.get("shopify_products_table_name", default_var="ShopifyProduct")
PRODUCT_VARIANTS_TABLE_NAME = Variable.get("shopify_product_variants_table_name", default_var="ShopifyProductVariant")
PRODUCT_IMAGES_TABLE_NAME = Variable.get("shopify_product_images_table_name", default_var="ShopifyProductImage")
COLLECTIONS_TABLE_NAME = Variable.get("shopify_collections_table_name", default_var="ShopifyCollection") # For Custom Collections
SMART_COLLECTIONS_TABLE_NAME = Variable.get("shopify_smart_collections_table_name", default_var="ShopifySmartCollection")

# Define columns carefully, matching your DB schema.
PRODUCT_COLUMNS = [
    "id", "shop_id", "title", "body_html", "vendor", "product_type", "handle",
    "created_at", "updated_at", "published_at", "status", "tags"
]
VARIANT_COLUMNS = [
    "id", "product_id", "shop_id", "title", "price", "sku", "position", "inventory_policy",
    "inventory_quantity", "inventory_item_id", "old_inventory_quantity", "requires_shipping",
    "taxable", "barcode", "grams", "weight", "weight_unit", "created_at", "updated_at"
]
IMAGE_COLUMNS = [
    "id", "product_id", "shop_id", "position", "created_at", "updated_at", "alt", "width", "height", "src"
]
COLLECTION_COLUMNS = [ # For both CustomCollection and SmartCollection, common fields
    "id", "shop_id", "handle", "title", "updated_at", "body_html", "published_at",
    "sort_order", "template_suffix", "published_scope"
]
# Add specific fields for SmartCollection if needed, e.g., rules.

ITEMS_PER_PAGE_LIMIT = 250 # Max for most Shopify resources

def get_last_update_timestamp_for_resource(resource_name, **kwargs):
    """
    Placeholder function to get the last updated_at timestamp for a given resource type from the DB.
    This helps fetch only new or updated items.
    For a full refresh, this can return None or a very old date.
    """
    # In a real scenario, query your app DB: SELECT MAX(updated_at) FROM your_table
    # For this example, we'll assume we always want to fetch data since the last DAG run if it was successful,
    # or do a full sync if configured or if it's the first run.
    # If Variable shopify_metadata_full_sync is 'true', then do a full sync.
    full_sync = Variable.get(f"shopify_{resource_name}_full_sync", default_var="false").lower() == "true"
    if full_sync:
        logger.info(f"Performing a full sync for {resource_name} as per configuration.")
        return None # No min_date, fetch all

    ti = kwargs['ti']
    dag_run = ti.get_dagrun()
    prev_success_run = dag_run.get_previous_dagrun(state='success')

    if prev_success_run:
        last_run_ts = prev_success_run.execution_date
        logger.info(f"Last successful run for metadata was at: {last_run_ts}. Fetching {resource_name} updated since then.")
        return last_run_ts - timedelta(minutes=10) # Overlap by 10 mins
    else:
        logger.info(f"No previous successful run found for metadata. Performing initial full sync for {resource_name}.")
        return None # No min_date, fetch all initially


def _fetch_all_pages(shopify_resource_class, shop_id, table_name, columns_def, **kwargs):
    """
    Generic function to fetch all items for a given Shopify resource.
    Handles pagination and prepares data for DB insertion.
    `kwargs` can include `updated_at_min` or other filters.
    """
    all_items_data = []
    page_count = 1

    updated_at_min_iso = None
    if kwargs.get("updated_at_min"):
        updated_at_min_iso = pd.to_datetime(kwargs["updated_at_min"]).isoformat()
        logger.info(f"Fetching {shopify_resource_class.__name__} with updated_at_min: {updated_at_min_iso}")
        items_page = shopify_resource_class.find(limit=ITEMS_PER_PAGE_LIMIT, updated_at_min=updated_at_min_iso)
    else:
        logger.info(f"Fetching all {shopify_resource_class.__name__} (no updated_at_min filter).")
        items_page = shopify_resource_class.find(limit=ITEMS_PER_PAGE_LIMIT)

    while items_page:
        logger.info(f"Processing page {page_count} of {shopify_resource_class.__name__}...")
        for item in items_page:
            item_data = {col: getattr(item, col, None) for col in columns_def if hasattr(item, col)}
            for col in columns_def: # Ensure all columns are present
                 if col not in item_data: item_data[col] = None

            item_data['id'] = item.id # Primary key
            item_data['shop_id'] = shop_id

            # Handle datetimes - convert to ISO format string or specific DB format
            for dt_field in ["created_at", "updated_at", "published_at"]:
                if item_data.get(dt_field) and item_data[dt_field] is not None:
                    item_data[dt_field] = pd.to_datetime(item_data[dt_field]).isoformat()

            # Specific handling for product variants (nested under product) is done in its own task.
            # Specific handling for product images (nested under product) is done in its own task.

            all_items_data.append(tuple(item_data.get(col) for col in columns_def))

        if items_page.has_next_page():
            items_page = items_page.next_page()
            page_count += 1
        else:
            break

    logger.info(f"Fetched {len(all_items_data)} total {shopify_resource_class.__name__}.")
    return all_items_data

def _upsert_data_to_db(data, table_name, columns_def, **kwargs):
    """Generic function to upsert data into the database."""
    if not data:
        logger.info(f"No data to load for {table_name}. Skipping DB operation.")
        return

    logger.info(f"Received {len(data)} items to load into table '{table_name}'.")

    db_hook = get_app_db_hook()
    conn = None
    try:
        conn = db_hook.get_conn()
        cursor = conn.cursor()

        cols_str = ", ".join(columns_def)
        val_placeholders = ", ".join(["%s"] * len(columns_def))
        update_cols = [f"{col} = EXCLUDED.{col}" for col in columns_def if col != "id"] # Assuming 'id' is PK
        update_set_str = ", ".join(update_cols)

        # Handle cases where there might be other unique constraints or PK is not 'id'
        # This assumes 'id' is the primary key for all metadata tables.
        pk_column = "id"
        if table_name == PRODUCT_VARIANTS_TABLE_NAME and "inventory_item_id" in columns_def:
             # Variants might be uniquely identified by 'id' or 'inventory_item_id' in some contexts
             # but Shopify 'id' for variant is globally unique.
             pass


        upsert_sql = f"""
        INSERT INTO {table_name} ({cols_str})
        VALUES ({val_placeholders})
        ON CONFLICT ({pk_column}) DO UPDATE
        SET {update_set_str};
        """

        logger.info(f"Executing UPSERT for {len(data)} items into {table_name}...")
        cursor.executemany(upsert_sql, data)
        conn.commit()
        logger.info(f"Successfully upserted {len(data)} items into {table_name}.")

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error loading data to table {table_name}: {e}")
        raise
    finally:
        if conn:
            cursor.close()
            conn.close()


def fetch_and_load_products_task(**kwargs):
    ti = kwargs['ti']
    updated_at_min = get_last_update_timestamp_for_resource("products", **kwargs)

    all_products_data = []
    all_variants_data = []
    all_images_data = []

    with get_shopify_session() as shopify_api:
        shop_details = shopify_api.Shop.current()
        shop_id = shop_details.id

        fetch_args = {'limit': ITEMS_PER_PAGE_LIMIT}
        if updated_at_min:
            fetch_args['updated_at_min'] = pd.to_datetime(updated_at_min).isoformat()
            logger.info(f"Fetching products with updated_at_min: {fetch_args['updated_at_min']}")
        else:
            logger.info("Fetching all products (no updated_at_min filter).")

        products_page = shopify_api.Product.find(**fetch_args)
        page_count = 1

        while products_page:
            logger.info(f"Processing page {page_count} of products...")
            for product in products_page:
                prod_data = {col: getattr(product, col, None) for col in PRODUCT_COLUMNS if hasattr(product, col)}
                for col in PRODUCT_COLUMNS:
                    if col not in prod_data: prod_data[col] = None
                prod_data['id'] = product.id
                prod_data['shop_id'] = shop_id
                for dt_field in ["created_at", "updated_at", "published_at"]:
                    if prod_data.get(dt_field):
                        prod_data[dt_field] = pd.to_datetime(prod_data[dt_field]).isoformat()
                all_products_data.append(tuple(prod_data.get(col) for col in PRODUCT_COLUMNS))

                # Fetch variants for this product
                for variant in product.variants:
                    var_data = {col: getattr(variant, col, None) for col in VARIANT_COLUMNS if hasattr(variant,col)}
                    for col in VARIANT_COLUMNS:
                        if col not in var_data: var_data[col] = None
                    var_data['id'] = variant.id
                    var_data['product_id'] = product.id
                    var_data['shop_id'] = shop_id
                    for dt_field in ["created_at", "updated_at"]:
                         if var_data.get(dt_field):
                            var_data[dt_field] = pd.to_datetime(var_data[dt_field]).isoformat()
                    if var_data.get('price'): var_data['price'] = float(var_data['price'])
                    # inventory_quantity is often a string from API, ensure it's int
                    if var_data.get('inventory_quantity') is not None:
                        var_data['inventory_quantity'] = int(var_data['inventory_quantity'])
                    if var_data.get('old_inventory_quantity') is not None:
                        var_data['old_inventory_quantity'] = int(var_data['old_inventory_quantity'])
                    if var_data.get('grams') is not None:
                        var_data['grams'] = int(var_data['grams'])


                    all_variants_data.append(tuple(var_data.get(col) for col in VARIANT_COLUMNS))

                # Fetch images for this product
                for image in product.images:
                    img_data = {col: getattr(image, col, None) for col in IMAGE_COLUMNS if hasattr(image,col)}
                    for col in IMAGE_COLUMNS:
                        if col not in img_data: img_data[col] = None
                    img_data['id'] = image.id
                    img_data['product_id'] = product.id
                    img_data['shop_id'] = shop_id
                    for dt_field in ["created_at", "updated_at"]:
                         if img_data.get(dt_field):
                            img_data[dt_field] = pd.to_datetime(img_data[dt_field]).isoformat()
                    all_images_data.append(tuple(img_data.get(col) for col in IMAGE_COLUMNS))

            if products_page.has_next_page():
                products_page = products_page.next_page()
                page_count += 1
            else:
                break

    logger.info(f"Fetched {len(all_products_data)} products, {len(all_variants_data)} variants, {len(all_images_data)} images.")

    if not all_products_data and updated_at_min: # If incremental and no new products
        logger.info("No new or updated products found.")
        # Option: skip downstream tasks if no data.
        # However, variants or images of existing products might have changed even if product itself didn't.
        # So, we proceed to attempt upserting variants and images.
        # If all_products_data is empty on a full sync, then it's truly empty.

    _upsert_data_to_db(all_products_data, PRODUCTS_TABLE_NAME, PRODUCT_COLUMNS)
    _upsert_data_to_db(all_variants_data, PRODUCT_VARIANTS_TABLE_NAME, VARIANT_COLUMNS)
    _upsert_data_to_db(all_images_data, PRODUCT_IMAGES_TABLE_NAME, IMAGE_COLUMNS)


def fetch_and_load_collections_task(collection_type, **kwargs):
    """Fetches and loads either CustomCollections or SmartCollections."""
    ti = kwargs['ti']
    resource_name = "custom_collections" if collection_type == "CustomCollection" else "smart_collections"
    table_name = COLLECTIONS_TABLE_NAME if collection_type == "CustomCollection" else SMART_COLLECTIONS_TABLE_NAME

    updated_at_min = get_last_update_timestamp_for_resource(resource_name, **kwargs)

    with get_shopify_session() as shopify_api:
        shop_details = shopify_api.Shop.current()
        shop_id = shop_details.id

        shopify_class = shopify_api.CustomCollection if collection_type == "CustomCollection" else shopify_api.SmartCollection

        fetch_kwargs = {}
        if updated_at_min:
            fetch_kwargs['updated_at_min'] = pd.to_datetime(updated_at_min).isoformat()

        collections_data = _fetch_all_pages(shopify_class, shop_id, table_name, COLLECTION_COLUMNS, **fetch_kwargs)

    if not collections_data and updated_at_min:
        logger.info(f"No new or updated {collection_type} found.")
        # raise AirflowSkipException(f"No new or updated {collection_type} to process.")

    _upsert_data_to_db(collections_data, table_name, COLLECTION_COLUMNS)


# --- DAG Definition ---
with DAG(
    dag_id=DAG_ID,
    default_args=DEFAULT_ARGS,
    schedule_interval=SCHEDULE_INTERVAL,
    start_date=days_ago(1), # Adjust as needed, esp. if catchup=True
    catchup=CATCHUP,
    tags=TAGS,
    doc_md=f"""
    ### Shopify Store Metadata Fetch DAG
    This DAG fetches store metadata like products, variants, images, custom collections, and smart collections from Shopify.
    - It uses `updated_at_min` to fetch incrementally where possible, based on the last successful DAG run.
    - A full sync can be triggered by setting Airflow Variable `shopify_<resource_type>_full_sync` to `true`.
    - Data is upserted into corresponding tables in the application database ({APP_DB_CONN_ID}).
    **Tables Populated:**
    - `{PRODUCTS_TABLE_NAME}`
    - `{PRODUCT_VARIANTS_TABLE_NAME}`
    - `{PRODUCT_IMAGES_TABLE_NAME}`
    - `{COLLECTIONS_TABLE_NAME}` (Custom Collections)
    - `{SMART_COLLECTIONS_TABLE_NAME}` (Smart Collections)
    """
) as dag:

    fetch_load_products = PythonOperator(
        task_id="fetch_and_load_products_variants_images",
        python_callable=fetch_and_load_products_task,
    )

    fetch_load_custom_collections = PythonOperator(
        task_id="fetch_and_load_custom_collections",
        python_callable=fetch_and_load_collections_task,
        op_kwargs={"collection_type": "CustomCollection"},
    )

    fetch_load_smart_collections = PythonOperator(
        task_id="fetch_and_load_smart_collections",
        python_callable=fetch_and_load_collections_task,
        op_kwargs={"collection_type": "SmartCollection"},
    )

    # Define task dependencies - these can run in parallel if desired
    # For simplicity, running them sequentially here, but parallel is often better.
    # If parallel, ensure your DB connection pool and Shopify API limits can handle it.
    fetch_load_products >> fetch_load_custom_collections >> fetch_load_smart_collections

# Import pandas for date conversion if not already available
try:
    import pandas as pd
except ImportError:
    logger.warning("Pandas library is not installed. Datetime conversion in DAG might need adjustment.")
    class pd: # Minimal mock
        @staticmethod
        def to_datetime(dt_str):
            if isinstance(dt_str, datetime): return dt_str
            try: return datetime.fromisoformat(str(dt_str).replace('Z', '+00:00'))
            except:
                try: return datetime.strptime(str(dt_str), '%Y-%m-%dT%H:%M:%S%z')
                except:
                    logger.error(f"Failed to parse datetime string: {dt_str}")
                    return None
