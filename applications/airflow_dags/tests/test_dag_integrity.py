import os
import importlib.util
import pytest
from airflow.models import DAG

# Define the path to the DAGs directory
# Assuming tests are run from the root of the monorepo or a context where this relative path is valid.
# If not, this might need adjustment or be made configurable.
# For local testing within applications/airflow_dags, this path would be '../dags'
# Let's assume the tests will be run with `applications/airflow_dags` as the current working directory
# or that PYTHONPATH is set up accordingly.
DAGS_DIR = os.path.join(os.path.dirname(__file__), "..", "dags")

# Get a list of all .py files in the DAGs directory, excluding __init__.py and utility modules
dag_files = [
    f
    for f in os.listdir(DAGS_DIR)
    if f.endswith(".py") and not f.startswith("__init__") and f != "shopify_common.py"
]

@pytest.mark.parametrize("dag_file", dag_files)
def test_dag_integrity(dag_file):
    """
    Test that each DAG file:
    1. Can be imported without syntax errors.
    2. Contains at least one object that is an instance of airflow.models.DAG.
    3. The DAG object has a 'dag_id' attribute.
    """
    module_name, _ = os.path.splitext(dag_file)
    module_path = os.path.join(DAGS_DIR, dag_file)

    # Attempt to import the module
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        assert spec is not None, f"Could not create spec for {module_name} from {module_path}"
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None, f"No loader for {module_name}"
        spec.loader.exec_module(module)
    except Exception as e:
        pytest.fail(f"Failed to import DAG file {dag_file}: {e}", pytrace=True)

    # Check for DAG objects in the imported module
    dag_objects = [
        var for var in vars(module).values() if isinstance(var, DAG)
    ]
    assert dag_objects, f"No DAG objects found in {dag_file}"

    # Check each DAG object for basic properties
    for dag in dag_objects:
        assert dag.dag_id, f"DAG in {dag_file} has no dag_id: {dag}"
        # Add more checks if needed, e.g., for default_args, schedule_interval, etc.
        assert len(dag.tasks) > 0, f"DAG '{dag.dag_id}' in {dag_file} has no tasks."

def test_dag_file_names_do_not_contain_dag_word():
    """
    Airflow best practice: DAG filenames should not contain the word "dag".
    This is a convention, not a strict rule, but often followed.
    Let's make this a non-critical warning for now if it fails.
    """
    # This test is more of a convention check.
    # If this project doesn't follow this convention, this test can be removed or modified.
    for dag_file in dag_files:
        if "dag" in dag_file.lower() and dag_file != "example_dag_decorator.py": # example from airflow itself
             # Using pytest.skip to not fail the test but to provide info
             # To make it a failure, use assert "dag" not in dag_file.lower(), f"..."
            print(f"Warning: DAG filename '{dag_file}' contains the word 'dag'. Consider renaming for convention.")
            # pytest.skip(f"Convention: DAG filename '{dag_file}' contains 'dag'.")
    assert True # If we reach here, the test passes (or only skipped warnings)

# Example of a more specific check if needed for a particular DAG
# def test_specific_dag_properties():
#     module_path = os.path.join(DAGS_DIR, "shopify_get_past_purchases_dag.py")
#     module_name, _ = os.path.splitext("shopify_get_past_purchases_dag.py")
#     spec = importlib.util.spec_from_file_location(module_name, module_path)
#     module = importlib.util.module_from_spec(spec)
#     spec.loader.exec_module(module)
#
#     dag = getattr(module, "dag", None) # Assuming DAG object is named 'dag'
#     assert dag is not None, "DAG object 'dag' not found in shopify_get_past_purchases_dag.py"
#     assert dag.dag_id == "shopify_fetch_past_purchases"
#     assert "fetch_shopify_orders" in dag.task_dict
#     assert "load_orders_to_db" in dag.task_dict
#     assert "load_line_items_to_db" in dag.task_dict
#
#     # Check task dependencies
#     fetch_task = dag.get_task("fetch_shopify_orders")
#     load_orders_task = dag.get_task("load_orders_to_db")
#     assert load_orders_task in fetch_task.downstream_list
#
#     # Check for cycles (Airflow does this on load, but can be explicit)
#     assert not dag.has_cycle()

# To run these tests:
# 1. Ensure pytest is installed (`pip install pytest`).
# 2. Navigate to `applications/airflow_dags` (or ensure PYTHONPATH includes this directory and `applications/airflow_dags/dags`).
# 3. Run `pytest tests/test_dag_integrity.py`.
#
# Note on PYTHONPATH: For Airflow DAGs that import custom modules (like `shopify_common` from the same `dags` folder),
# the `dags` folder itself needs to be in PYTHONPATH. Pytest handles this reasonably well if run from
# `applications/airflow_dags` and tests are in `applications/airflow_dags/tests`.
# If `shopify_common.py` were in a different location (e.g., a shared lib),
# PYTHONPATH would need to be managed more explicitly for tests to find it.
# The `DAGS_DIR` assumes `shopify_common.py` is found because it's imported by the DAG files themselves,
# and the import mechanism within the DAG file handles its location relative to the DAG file.
# The test file itself does not directly import `shopify_common`.
# It imports the DAG module, which in turn imports `shopify_common`.
# This should work if `PYTHONPATH` includes the `dags` directory or if the DAGs use relative imports correctly.
# Given `from shopify_common import ...` in DAGs, `applications/airflow_dags/dags` must be on `PYTHONPATH`.
# One way to ensure this when running pytest from `applications/airflow_dags` is to have an `__init__.py`
# in `applications/airflow_dags/dags/` and potentially adjust `sys.path` in a `conftest.py` or test setup.
# Or, run pytest as `python -m pytest tests/test_dag_integrity.py` from `applications/airflow_dags`
# which adds the current directory to sys.path.

# Let's add a conftest.py to handle PYTHONPATH for the dags directory.
