import pytest
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime, timedelta

# Import the DAG module to test its tasks' callables
from dags import shopify_get_store_metadata_dag as metadata_dag_module
from dags import shopify_common

# Mocked column lists (ensure these match the DAG's definitions for consistency in tests)
MOCKED_PRODUCT_COLUMNS = [
    "id", "shop_id", "title", "body_html", "vendor", "product_type", "handle",
    "created_at", "updated_at", "published_at", "status", "tags"
]
MOCKED_VARIANT_COLUMNS = [
    "id", "product_id", "shop_id", "title", "price", "sku", "position", "inventory_policy",
    "inventory_quantity", "inventory_item_id", "old_inventory_quantity", "requires_shipping",
    "taxable", "barcode", "grams", "weight", "weight_unit", "created_at", "updated_at"
]
MOCKED_IMAGE_COLUMNS = [
    "id", "product_id", "shop_id", "position", "created_at", "updated_at", "alt", "width", "height", "src"
]
MOCKED_COLLECTION_COLUMNS = [
    "id", "shop_id", "handle", "title", "updated_at", "body_html", "published_at",
    "sort_order", "template_suffix", "published_scope"
]

@pytest.fixture(autouse=True)
def mock_common_metadata_dag_dependencies(mocker):
    """Mocks dependencies from shopify_common and Airflow Variables for metadata DAG tasks."""
    mocker.patch.object(metadata_dag_module, "get_shopify_session")
    mocker.patch.object(metadata_dag_module, "get_app_db_hook")
    mock_variable_get = mocker.patch.object(metadata_dag_module, "Variable")

    # Default mock for Variable.get
    def var_get_side_effect(key, default_var=None):
        if key.endswith("_full_sync"): return "false" # Default to incremental
        # Add other variable mocks if the DAG uses more
        return default_var if default_var is not None else f"mock_var_{key}"
    mock_variable_get.get.side_effect = var_get_side_effect

    # Patch column lists and table names to ensure consistency
    mocker.patch.object(metadata_dag_module, 'PRODUCT_COLUMNS', MOCKED_PRODUCT_COLUMNS)
    mocker.patch.object(metadata_dag_module, 'VARIANT_COLUMNS', MOCKED_VARIANT_COLUMNS)
    mocker.patch.object(metadata_dag_module, 'IMAGE_COLUMNS', MOCKED_IMAGE_COLUMNS)
    mocker.patch.object(metadata_dag_module, 'COLLECTION_COLUMNS', MOCKED_COLLECTION_COLUMNS)

    mocker.patch.object(metadata_dag_module, 'PRODUCTS_TABLE_NAME', "TestShopifyProduct")
    mocker.patch.object(metadata_dag_module, 'PRODUCT_VARIANTS_TABLE_NAME', "TestShopifyProductVariant")
    mocker.patch.object(metadata_dag_module, 'PRODUCT_IMAGES_TABLE_NAME', "TestShopifyProductImage")
    mocker.patch.object(metadata_dag_module, 'COLLECTIONS_TABLE_NAME', "TestShopifyCollection")
    mocker.patch.object(metadata_dag_module, 'SMART_COLLECTIONS_TABLE_NAME', "TestShopifySmartCollection")

    # Mock pandas to_datetime
    mock_pd_to_datetime = mocker.patch("dags.shopify_get_store_metadata_dag.pd.to_datetime")
    mock_pd_to_datetime.side_effect = lambda dt: datetime.fromisoformat(dt.replace('Z', '+00:00')) if isinstance(dt, str) else dt


@pytest.fixture
def mock_task_instance():
    ti = MagicMock()
    ti.get_dagrun = MagicMock()
    return ti

@pytest.fixture
def mock_dag_run():
    dr = MagicMock()
    dr.get_previous_dagrun.return_value = None
    return dr

# --- Tests for get_last_update_timestamp_for_resource ---
def test_get_last_update_timestamp_full_sync(mock_task_instance, mocker):
    mock_variable_get = mocker.patch.object(metadata_dag_module.Variable, 'get')
    mock_variable_get.return_value = "true" # Force full sync

    ts = metadata_dag_module.get_last_update_timestamp_for_resource("products", ti=mock_task_instance)
    assert ts is None
    mock_variable_get.assert_called_once_with("shopify_products_full_sync", default_var="false")

def test_get_last_update_timestamp_no_previous_run(mock_task_instance, mock_dag_run, mocker):
    mock_variable_get = mocker.patch.object(metadata_dag_module.Variable, 'get')
    mock_variable_get.return_value = "false" # Incremental
    mock_task_instance.get_dagrun.return_value = mock_dag_run # mock_dag_run has no prev successful run by default

    ts = metadata_dag_module.get_last_update_timestamp_for_resource("products", ti=mock_task_instance)
    assert ts is None # Should be None for initial full sync if no previous run

def test_get_last_update_timestamp_with_previous_run(mock_task_instance, mock_dag_run, mocker):
    mock_variable_get = mocker.patch.object(metadata_dag_module.Variable, 'get')
    mock_variable_get.return_value = "false" # Incremental

    prev_success_run = MagicMock()
    prev_success_run.execution_date = datetime(2023, 1, 10, 0, 0, 0)
    mock_dag_run.get_previous_dagrun.return_value = prev_success_run
    mock_task_instance.get_dagrun.return_value = mock_dag_run

    expected_ts = prev_success_run.execution_date - timedelta(minutes=10) # 10 min overlap
    actual_ts = metadata_dag_module.get_last_update_timestamp_for_resource("products", ti=mock_task_instance)
    assert actual_ts == expected_ts

# --- Tests for fetch_and_load_products_task ---
@patch.object(metadata_dag_module, "get_last_update_timestamp_for_resource")
@patch.object(metadata_dag_module, "get_shopify_session")
@patch.object(metadata_dag_module, "_upsert_data_to_db") # Mock the internal upsert helper
def test_fetch_and_load_products_task_flow(
    mock_upsert_db, mock_get_session, mock_get_last_ts, mock_task_instance
):
    mock_get_last_ts.return_value = None # Simulate full sync for simplicity

    mock_shopify_api = MagicMock()
    mock_get_session.return_value.__enter__.return_value = mock_shopify_api

    mock_shop_details = MagicMock()
    mock_shop_details.id = 987
    mock_shopify_api.Shop.current.return_value = mock_shop_details

    # Mock Product Data
    mock_product1 = MagicMock()
    mock_product1.id = 1001
    for col in MOCKED_PRODUCT_COLUMNS: setattr(mock_product1, col, f"prod1_{col}") # Basic values
    mock_product1.created_at = "2023-01-01T00:00:00Z"
    mock_product1.updated_at = "2023-01-01T00:00:00Z"
    mock_product1.published_at = "2023-01-01T00:00:00Z"


    mock_variant1 = MagicMock()
    mock_variant1.id = 2001
    for col in MOCKED_VARIANT_COLUMNS: setattr(mock_variant1, col, f"var1_{col}")
    mock_variant1.price = "10.00"
    mock_variant1.inventory_quantity = "5" # Shopify API might return as string
    mock_variant1.old_inventory_quantity = "0"
    mock_variant1.grams = "100"
    mock_variant1.created_at = "2023-01-01T00:00:00Z"
    mock_variant1.updated_at = "2023-01-01T00:00:00Z"


    mock_image1 = MagicMock()
    mock_image1.id = 3001
    for col in MOCKED_IMAGE_COLUMNS: setattr(mock_image1, col, f"img1_{col}")
    mock_image1.created_at = "2023-01-01T00:00:00Z"
    mock_image1.updated_at = "2023-01-01T00:00:00Z"


    mock_product1.variants = [mock_variant1]
    mock_product1.images = [mock_image1]

    page1_mock = MagicMock()
    page1_mock.__iter__.return_value = iter([mock_product1])
    page1_mock.has_next_page.return_value = False
    mock_shopify_api.Product.find.return_value = page1_mock

    metadata_dag_module.fetch_and_load_products_task(ti=mock_task_instance)

    mock_shopify_api.Product.find.assert_called_once_with(limit=metadata_dag_module.ITEMS_PER_PAGE_LIMIT)

    # Check calls to _upsert_data_to_db
    # Products
    mock_upsert_db.assert_any_call(ANY, "TestShopifyProduct", MOCKED_PRODUCT_COLUMNS)
    products_call_args = [c for c in mock_upsert_db.call_args_list if c[0][1] == "TestShopifyProduct"][0]
    assert len(products_call_args[0][0]) == 1 # One product
    assert products_call_args[0][0][0][MOCKED_PRODUCT_COLUMNS.index("id")] == 1001

    # Variants
    mock_upsert_db.assert_any_call(ANY, "TestShopifyProductVariant", MOCKED_VARIANT_COLUMNS)
    variants_call_args = [c for c in mock_upsert_db.call_args_list if c[0][1] == "TestShopifyProductVariant"][0]
    assert len(variants_call_args[0][0]) == 1
    assert variants_call_args[0][0][MOCKED_VARIANT_COLUMNS.index("id")] == 2001
    assert variants_call_args[0][0][MOCKED_VARIANT_COLUMNS.index("product_id")] == 1001
    assert variants_call_args[0][0][MOCKED_VARIANT_COLUMNS.index("inventory_quantity")] == 5 # Check type conversion

    # Images
    mock_upsert_db.assert_any_call(ANY, "TestShopifyProductImage", MOCKED_IMAGE_COLUMNS)
    images_call_args = [c for c in mock_upsert_db.call_args_list if c[0][1] == "TestShopifyProductImage"][0]
    assert len(images_call_args[0][0]) == 1
    assert images_call_args[0][0][MOCKED_IMAGE_COLUMNS.index("id")] == 3001
    assert images_call_args[0][0][MOCKED_IMAGE_COLUMNS.index("product_id")] == 1001


# --- Tests for fetch_and_load_collections_task ---
@patch.object(metadata_dag_module, "get_last_update_timestamp_for_resource")
@patch.object(metadata_dag_module, "get_shopify_session")
@patch.object(metadata_dag_module, "_fetch_all_pages") # Mock the page fetcher directly
@patch.object(metadata_dag_module, "_upsert_data_to_db")
def test_fetch_and_load_collections_task_custom_collection(
    mock_upsert_db, mock_fetch_pages, mock_get_session, mock_get_last_ts, mock_task_instance
):
    mock_get_last_ts.return_value = None # Full sync

    mock_shopify_api = MagicMock() # Not directly used if _fetch_all_pages is mocked, but get_shopify_session needs it
    mock_get_session.return_value.__enter__.return_value = mock_shopify_api
    mock_shop_details = MagicMock(id=987)
    mock_shopify_api.Shop.current.return_value = mock_shop_details


    # Sample data that _fetch_all_pages would return
    sample_collections_data = [
        (7001, 987, "col-handle-1", "Collection 1", "2023-01-01T00:00:00Z", "html", "2023-01-01T00:00:00Z", "alpha", None, "web")
    ]
    mock_fetch_pages.return_value = sample_collections_data

    metadata_dag_module.fetch_and_load_collections_task("CustomCollection", ti=mock_task_instance)

    # Verify _fetch_all_pages was called correctly for CustomCollection
    mock_fetch_pages.assert_called_once_with(
        mock_shopify_api.CustomCollection, # Expected Shopify resource class
        987, # shop_id
        "TestShopifyCollection", # table_name
        MOCKED_COLLECTION_COLUMNS, # columns_def
        updated_at_min=None # Since mock_get_last_ts returned None
    )

    # Verify _upsert_data_to_db was called with the data from _fetch_all_pages
    mock_upsert_db.assert_called_once_with(sample_collections_data, "TestShopifyCollection", MOCKED_COLLECTION_COLUMNS)


# --- Test for _upsert_data_to_db (internal helper, but good to have direct tests) ---
@patch("dags.shopify_get_store_metadata_dag.get_app_db_hook") # Patch where it's defined
def test_internal_upsert_data_to_db_with_data(mock_get_hook_global):
    # This tests the _upsert_data_to_db function in the metadata_dag_module
    mock_db_hook_instance = MagicMock()
    mock_get_hook_global.return_value = mock_db_hook_instance
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db_hook_instance.get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    sample_data = [(1, "data1"), (2, "data2")]
    table_name = "TestTable"
    columns = ["id", "value"]

    metadata_dag_module._upsert_data_to_db(sample_data, table_name, columns)

    mock_db_hook_instance.get_conn.assert_called_once()
    mock_conn.cursor.assert_called_once()
    mock_cursor.executemany.assert_called_once()

    actual_sql = mock_cursor.executemany.call_args[0][0]
    assert f"INSERT INTO {table_name}" in actual_sql
    assert "ON CONFLICT (id) DO UPDATE SET" in actual_sql
    assert "value = EXCLUDED.value" in actual_sql # Check one of the set clauses

    assert mock_cursor.executemany.call_args[0][1] == sample_data
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

@patch("dags.shopify_get_store_metadata_dag.get_app_db_hook")
def test_internal_upsert_data_to_db_no_data(mock_get_hook_global):
    metadata_dag_module._upsert_data_to_db([], "TestTable", ["id"])
    mock_get_hook_global.return_value.get_conn.assert_not_called()
