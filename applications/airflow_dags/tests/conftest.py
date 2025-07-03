import sys
import os

# Add the 'dags' directory to sys.path to allow tests to import DAGs
# and for DAGs to import modules within the 'dags' directory (like shopify_common).
# This assumes tests are run from the 'applications/airflow_dags' directory or
# that the paths are adjusted accordingly if run from the monorepo root.

# Path to the 'dags' directory relative to this conftest.py file
DAGS_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "dags")
)

# Add DAGS_FOLDER to sys.path if it's not already there
if DAGS_FOLDER not in sys.path:
    sys.path.insert(0, DAGS_FOLDER)

# Optional: Add the parent of 'dags' (i.e., 'applications/airflow_dags') to sys.path
# This might be useful if DAGs or common modules need to import from other parts
# of the 'airflow_dags' application, though typically DAGs should be self-contained
# or rely on installed packages or modules within the DAGs folder itself.
# APP_AIRFLOW_DAGS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# if APP_AIRFLOW_DAGS_ROOT not in sys.path:
#     sys.path.insert(0, APP_AIRFLOW_DAGS_ROOT)

# You can also define fixtures here that can be used by any test in this directory or subdirectories.
# For example, a fixture to provide a default Airflow DAG run context:
#
# import pendulum
# from airflow.utils.state import DagRunState
# from airflow.utils.types import DagRunType
#
# @pytest.fixture
# def mock_dag_run(dag):
#     """Provides a basic mock DagRun object."""
#     return dag.create_dagrun(
#         state=DagRunState.RUNNING,
#         execution_date=pendulum.now(),
#         run_type=DagRunType.MANUAL,
#     )
#
# @pytest.fixture
# def mock_ti(dag, mock_dag_run, task_id):
#     """Provides a TaskInstance mock, requires task_id to be specified or parameterized."""
#     task = dag.get_task(task_id)
#     return mock_dag_run.get_task_instance(task.task_id)

# Note: To use fixtures like mock_dag_run or mock_ti that depend on a 'dag' object,
# the test function itself would need a 'dag' fixture that provides the specific DAG instance.
# This might involve loading the DAG within the test or a fixture.
# For DAG integrity tests, we are loading DAGs dynamically, so these might be more useful
# for task-specific unit/integration tests.
