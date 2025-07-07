import pytest
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime, timedelta

# Import the DAG module to test its tasks' callables
# conftest.py ensures 'dags' directory (where shopify_common and the DAG file are) is in sys.path
from dags import shopify_get_past_purchases_dag as dag_module
from dags import shopify_common # To mock its functions

# Mock Airflow's Variable and XCom utilities if tasks use them directly
# For XComs, tasks usually receive `ti` (TaskInstance) and call ti.xcom_push/pull.
# We'll mock the `ti` object passed to the callables.

# Mock the shopify_common global variables if they are accessed directly by DAG
# For example, table names if not configured via Airflow Variables for tests
MOCKED_ORDER_COLUMNS = [
    "id", "shop_id", "customer_id", "email", "total_price", "subtotal_price",
    "total_tax", "total_discounts", "currency", "financial_status",
    "fulfillment_status", "processed_at", "created_at", "updated_at",
    "landing_site", "referring_site", "source_name", "tags"
]
MOCKED_LINE_ITEM_COLUMNS = [
    "id", "order_id", "shop_id", "product_id", "variant_id", "title", "quantity",
    "sku", "vendor", "price", "total_discount", "taxable", "fulfillment_status"
]

@pytest.fixture(autouse=True)
def mock_common_dag_dependencies(mocker):
    """Mocks dependencies from shopify_common used by the DAG tasks."""
    mocker.patch("dags.shopify_get_past_purchases_dag.get_shopify_session")
    mocker.patch("dags.shopify_get_past_purchases_dag.get_app_db_hook")
    mocker.patch("dags.shopify_get_past_purchases_dag.Variable") # Mock Airflow Variable
    # Ensure column lists are defined, as DAG might import them
    mocker.patch.object(dag_module, 'ORDER_COLUMNS', MOCKED_ORDER_COLUMNS)
    mocker.patch.object(dag_module, 'LINE_ITEM_COLUMNS', MOCKED_LINE_ITEM_COLUMNS)
    mocker.patch.object(dag_module, 'ORDERS_TABLE_NAME', "TestShopifyOrder")
    mocker.patch.object(dag_module, 'ORDER_LINE_ITEMS_TABLE_NAME', "TestShopifyOrderLineItem")
    # Mock pandas if its methods are critical and complex, otherwise allow real usage
    # For to_datetime, it's simple enough to let it run or provide a simple mock if needed.
    # mocker.patch("dags.shopify_get_past_purchases_dag.pd")


@pytest.fixture
def mock_task_instance():
    """Creates a mock TaskInstance (ti) object."""
    ti = MagicMock()
    ti.xcom_push = MagicMock()
    ti.xcom_pull = MagicMock()
    ti.get_dagrun = MagicMock() # For get_last_successful_run_timestamp
    return ti

@pytest.fixture
def mock_dag_run():
    """Mocks a DagRun object."""
    dr = MagicMock()
    dr.get_previous_dagrun.return_value = None # Default: no previous successful run
    return dr

# --- Tests for get_last_successful_run_timestamp ---
def test_get_last_successful_run_timestamp_no_previous_run(mock_task_instance, mock_dag_run, mocker):
    mock_task_instance.get_dagrun.return_value = mock_dag_run
    mocker.patch.object(dag_module, "INITIAL_LOOKBACK_DAYS", 30) # Ensure it's defined

    # Mock datetime.utcnow() to control its return value
    fixed_now = datetime(2023, 1, 31, 12, 0, 0)
    mocker.patch("dags.shopify_get_past_purchases_dag.datetime",utcnow=MagicMock(return_value=fixed_now))

    expected_ts = fixed_now - timedelta(days=30)
    actual_ts = dag_module.get_last_successful_run_timestamp(ti=mock_task_instance)

    assert actual_ts == expected_ts

def test_get_last_successful_run_timestamp_with_previous_run(mock_task_instance, mock_dag_run):
    prev_success_run = MagicMock()
    prev_success_run.execution_date = datetime(2023, 1, 15, 10, 0, 0)
    mock_dag_run.get_previous_dagrun.return_value = prev_success_run
    mock_task_instance.get_dagrun.return_value = mock_dag_run

    expected_ts = prev_success_run.execution_date - timedelta(minutes=5) # 5 min overlap
    actual_ts = dag_module.get_last_successful_run_timestamp(ti=mock_task_instance)

    assert actual_ts == expected_ts

# --- Tests for fetch_shopify_orders_task ---
@patch("dags.shopify_get_past_purchases_dag.get_shopify_session")
@patch("dags.shopify_get_past_purchases_dag.get_last_successful_run_timestamp") # Mock this helper too
def test_fetch_shopify_orders_task_no_orders(mock_get_last_run_ts, mock_get_session, mock_task_instance, mocker):
    start_time = datetime(2023, 1, 1)
    mock_get_last_run_ts.return_value = start_time

    mock_shopify_api = MagicMock()
    mock_get_session.return_value.__enter__.return_value = mock_shopify_api

    mock_shop_details = MagicMock()
    mock_shop_details.id = 123
    mock_shopify_api.Shop.current.return_value = mock_shop_details

    mock_shopify_api.Order.find.return_value = [] # No orders found

    # Mock datetime.utcnow for consistent "processed_at_max" if not provided in conf
    fixed_now_utc = datetime(2023, 1, 2, 0, 0, 0) # Ensure this is after start_time
    mocker.patch('dags.shopify_get_past_purchases_dag.datetime', MagicMock(utcnow=MagicMock(return_value=fixed_now_utc)))


    dag_module.fetch_shopify_orders_task(ti=mock_task_instance, dag_run=MagicMock(conf={}))

    mock_shopify_api.Order.find.assert_called_once_with(
        limit=dag_module.ORDERS_PER_PAGE_LIMIT,
        updated_at_min=start_time.isoformat(),
        status='any',
        order='updated_at asc'
    )
    mock_task_instance.xcom_push.assert_any_call(key="orders_data", value=[])
    mock_task_instance.xcom_push.assert_any_call(key="line_items_data", value=[])

@patch("dags.shopify_get_past_purchases_dag.get_shopify_session")
@patch("dags.shopify_get_past_purchases_dag.get_last_successful_run_timestamp")
def test_fetch_shopify_orders_task_with_data(mock_get_last_run_ts, mock_get_session, mock_task_instance, mocker):
    start_time = datetime(2023, 1, 1)
    mock_get_last_run_ts.return_value = start_time

    mock_shopify_api = MagicMock()
    mock_get_session.return_value.__enter__.return_value = mock_shopify_api

    mock_shop_details = MagicMock()
    mock_shop_details.id = 12345
    mock_shopify_api.Shop.current.return_value = mock_shop_details

    # Mock order data
    mock_order1 = MagicMock()
    mock_order1.id = 1
    mock_order1.customer = MagicMock(id=101) if hasattr(mock_order1, 'customer') else None # Handle if customer is not always present
    # Fill in other required fields for ORDER_COLUMNS for mock_order1
    for col in MOCKED_ORDER_COLUMNS:
        if not hasattr(mock_order1, col): setattr(mock_order1, col, f"val_{col}_1")
    mock_order1.processed_at = "2023-01-01T10:00:00Z" # Ensure compatible with pd.to_datetime
    mock_order1.created_at = "2023-01-01T09:00:00Z"
    mock_order1.updated_at = "2023-01-01T11:00:00Z"
    mock_order1.total_price = "100.00"


    mock_li1 = MagicMock()
    mock_li1.id = 10
    # Fill in other required fields for LINE_ITEM_COLUMNS for mock_li1
    for col in MOCKED_LINE_ITEM_COLUMNS:
         if not hasattr(mock_li1, col): setattr(mock_li1, col, f"val_li_{col}_1")
    mock_li1.price = "50.00"
    mock_li1.total_discount = "5.00"

    mock_order1.line_items = [mock_li1]

    # Simulate pagination: first page has order1, next page is empty
    page1_mock = MagicMock()
    page1_mock.__iter__.return_value = iter([mock_order1]) # Make it iterable
    page1_mock.has_next_page.return_value = False # Single page for simplicity here
    # If testing multiple pages:
    # page1_mock.has_next_page.return_value = True
    # page1_mock.next_page.return_value = page2_mock (where page2_mock.has_next_page.return_value = False)

    mock_shopify_api.Order.find.return_value = page1_mock

    # Mock pandas to_datetime as it's used for conversion
    mock_pd_to_datetime = mocker.patch("dags.shopify_get_past_purchases_dag.pd.to_datetime")
    mock_pd_to_datetime.side_effect = lambda dt: datetime.fromisoformat(dt.replace('Z', '+00:00')) if isinstance(dt, str) else dt


    dag_module.fetch_shopify_orders_task(ti=mock_task_instance, dag_run=MagicMock(conf={}))

    # Verify XComs (structure depends on how data is processed into tuples)
    pushed_orders = mock_task_instance.xcom_push.call_args_list[0][1]['value'] # Assuming orders_data is first
    pushed_line_items = mock_task_instance.xcom_push.call_args_list[1][1]['value']

    assert len(pushed_orders) == 1
    assert pushed_orders[0][MOCKED_ORDER_COLUMNS.index("id")] == 1 # Check ID

    assert len(pushed_line_items) == 1
    assert pushed_line_items[0][MOCKED_LINE_ITEM_COLUMNS.index("id")] == 10 # Check ID
    assert pushed_line_items[0][MOCKED_LINE_ITEM_COLUMNS.index("order_id")] == 1 # Check FK

# --- Tests for load_orders_to_db_task ---
@patch("dags.shopify_get_past_purchases_dag.get_app_db_hook")
def test_load_orders_to_db_task_with_data(mock_get_hook, mock_task_instance):
    mock_db_hook_instance = MagicMock()
    mock_get_hook.return_value = mock_db_hook_instance
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db_hook_instance.get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Sample data as if pulled from XCom
    sample_orders_data = [(1, 12345, 101, 'test@example.com', 100.0, 90.0, 5.0, 5.0, 'USD', 'paid',
                           'fulfilled', '2023-01-01T10:00:00', '2023-01-01T09:00:00', '2023-01-01T11:00:00',
                           None, None, 'web', 'tag1')]
                           # Ensure tuple matches MOCKED_ORDER_COLUMNS
    mock_task_instance.xcom_pull.return_value = sample_orders_data

    dag_module.load_orders_to_db_task(ti=mock_task_instance)

    mock_db_hook_instance.get_conn.assert_called_once()
    mock_conn.cursor.assert_called_once()
    mock_cursor.executemany.assert_called_once()
    # Check the SQL query (first arg to executemany)
    actual_sql = mock_cursor.executemany.call_args[0][0]
    assert "INSERT INTO TestShopifyOrder" in actual_sql
    assert "ON CONFLICT (id) DO UPDATE" in actual_sql
    # Check the data passed (second arg to executemany)
    assert mock_cursor.executemany.call_args[0][1] == sample_orders_data
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

@patch("dags.shopify_get_past_purchases_dag.get_app_db_hook")
def test_load_orders_to_db_task_no_data(mock_get_hook, mock_task_instance):
    mock_task_instance.xcom_pull.return_value = [] # No data
    dag_module.load_orders_to_db_task(ti=mock_task_instance)
    mock_get_hook.return_value.get_conn.assert_not_called()


# --- Tests for load_line_items_to_db_task (similar structure to load_orders) ---
@patch("dags.shopify_get_past_purchases_dag.get_app_db_hook")
def test_load_line_items_to_db_task_with_data(mock_get_hook, mock_task_instance):
    mock_db_hook_instance = MagicMock()
    mock_get_hook.return_value = mock_db_hook_instance
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db_hook_instance.get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    sample_li_data = [(10, 1, 12345, 201, 301, 'Item 1', 1, 'SKU001', 'Vendor A',
                       50.0, 5.0, True, 'fulfilled')]
                       # Ensure tuple matches MOCKED_LINE_ITEM_COLUMNS
    mock_task_instance.xcom_pull.return_value = sample_li_data

    dag_module.load_line_items_to_db_task(ti=mock_task_instance)

    mock_db_hook_instance.get_conn.assert_called_once()
    actual_sql = mock_cursor.executemany.call_args[0][0]
    assert "INSERT INTO TestShopifyOrderLineItem" in actual_sql
    assert "ON CONFLICT (id) DO UPDATE" in actual_sql
    assert mock_cursor.executemany.call_args[0][1] == sample_li_data
    mock_conn.commit.assert_called_once()

# Skipping AirflowSkipException test for brevity, but it could be added for fetch_shopify_orders_task
# if processed_at_min >= processed_at_max
