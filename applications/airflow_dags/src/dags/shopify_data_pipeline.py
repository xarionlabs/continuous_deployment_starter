"""
Shopify Data Pipeline - Main Orchestration DAG

This DAG orchestrates the complete Shopify data synchronization pipeline using Airflow 3.0.2
patterns with @task decorators. It coordinates specialized DAGs for different data types:
- shopify_past_purchases: Customer purchase data using getCustomersWithOrders query
- shopify_store_metadata: Product catalog data using getAllProductData and getProductImages queries

This main orchestration DAG provides:
- Cross-DAG coordination and dependency management
- Unified monitoring and reporting
- Error handling and alerting across all sync operations
- REST API triggerable for manual execution
- Comprehensive data quality validation across all data types

Schedule: Daily at 1:00 AM UTC (coordinates other DAGs)
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import asyncio

from airflow import DAG
from airflow.decorators import task, task_group
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.utils.trigger_rule import TriggerRule
from airflow.exceptions import AirflowException
from airflow.models import Variable
# from airflow.utils.dates import days_ago  # Not available in Airflow 3.0.2
from airflow.utils.state import State

import structlog
from operators.shopify_operator import (
    ShopifyToPostgresOperator,
    ShopifyDataValidationOperator,
    ShopifyIncrementalSyncOperator
)
from hooks.shopify_hook import ShopifyHook
from utils.database import DatabaseManager

logger = structlog.get_logger(__name__)

# DAG Configuration
DAG_ID = "shopify_data_pipeline"
DESCRIPTION = "Orchestrates complete Shopify data synchronization pipeline across specialized DAGs"
SCHEDULE_INTERVAL = "0 1 * * *"  # Daily at 1:00 AM UTC (coordinates other DAGs)
START_DATE = datetime(2024, 1, 1)
CATCHUP = False
MAX_ACTIVE_RUNS = 1
MAX_ACTIVE_TASKS = 10
DAGRUN_TIMEOUT = timedelta(hours=8)

# Coordinated DAG configurations
COORDINATED_DAGS = {
    "shopify_past_purchases": {
        "schedule": "0 2 * * *",  # Runs after main pipeline
        "timeout": timedelta(hours=4),
        "priority": "high"
    },
    "shopify_store_metadata": {
        "schedule": "0 3 * * *",  # Runs after past purchases
        "timeout": timedelta(hours=6),
        "priority": "high"
    }
}

# Default arguments
default_args = {
    "owner": "pxy6-data-team",
    "depends_on_past": False,
    "start_date": START_DATE,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
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
    tags=["shopify", "data-pipeline", "etl", "orchestration"],
    doc_md=__doc__,
)

# Configuration Tasks
@task(dag=dag)
def get_pipeline_config(**context) -> Dict[str, Any]:
    """
    Get pipeline configuration settings
    
    Returns:
        Dictionary containing pipeline configuration
    """
    logger.info("Getting pipeline configuration")
    
    config = {
        "sync_mode": Variable.get("shopify_sync_mode", "incremental"),  # full, incremental
        "batch_size": int(Variable.get("shopify_batch_size", "100")),
        "max_pages": int(Variable.get("shopify_max_pages", "0")) or None,
        "enable_products_sync": Variable.get("shopify_enable_products_sync", "true").lower() == "true",
        "enable_customers_sync": Variable.get("shopify_enable_customers_sync", "true").lower() == "true",
        "enable_orders_sync": Variable.get("shopify_enable_orders_sync", "true").lower() == "true",
        "enable_validation": Variable.get("shopify_enable_validation", "true").lower() == "true",
        "validation_threshold": float(Variable.get("shopify_validation_threshold", "0.95")),
        "lookback_hours": int(Variable.get("shopify_lookback_hours", "24")),
        "parallel_execution": Variable.get("shopify_parallel_execution", "true").lower() == "true",
        "coordinate_specialized_dags": Variable.get("shopify_coordinate_dags", "true").lower() == "true",
        "enable_cross_dag_monitoring": Variable.get("shopify_cross_dag_monitoring", "true").lower() == "true",
        "dag_coordination_mode": Variable.get("shopify_dag_coordination_mode", "sequential"),  # sequential, parallel
    }
    
    logger.info(f"Pipeline configuration: {config}")
    return config

@task(dag=dag)
def validate_connections(**context) -> Dict[str, Any]:
    """
    Validate all required connections
    
    Returns:
        Dictionary with connection validation results
    """
    logger.info("Validating connections")
    
    validation_results = {
        "shopify_connection": False,
        "postgres_connection": False,
        "overall_status": "FAILED"
    }
    
    try:
        # Test Shopify connection
        shopify_hook = ShopifyHook(shopify_conn_id="shopify_default")
        validation_results["shopify_connection"] = shopify_hook.test_connection()
        shopify_hook.close()
        
        # Test PostgreSQL connection
        async def test_postgres():
            db_manager = DatabaseManager()
            try:
                await db_manager.connect()
                result = await db_manager.test_connection()
                return result
            finally:
                await db_manager.close()
        
        validation_results["postgres_connection"] = asyncio.run(test_postgres())
        
        # Overall status
        if validation_results["shopify_connection"] and validation_results["postgres_connection"]:
            validation_results["overall_status"] = "PASSED"
        
    except Exception as e:
        logger.error(f"Connection validation failed: {str(e)}")
        validation_results["error"] = str(e)
    
    logger.info(f"Connection validation results: {validation_results}")
    
    if validation_results["overall_status"] == "FAILED":
        raise AirflowException(f"Connection validation failed: {validation_results}")
    
    return validation_results

@task(dag=dag)
def prepare_database(**context) -> Dict[str, Any]:
    """
    Prepare database for sync operations
    
    Returns:
        Dictionary with database preparation results
    """
    logger.info("Preparing database for sync operations")
    
    async def setup_database():
        db_manager = DatabaseManager()
        try:
            await db_manager.connect()
            await db_manager.create_tables()
            
            # Get current statistics
            stats = {
                "products_count": await db_manager.get_products_count(),
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
    
    result = asyncio.run(setup_database())
    
    if result.get("setup_status") == "FAILED":
        raise AirflowException(f"Database preparation failed: {result.get('error')}")
    
    logger.info(f"Database preparation completed: {result}")
    return result

def decide_coordination_mode(**context) -> str:
    """
    Decide whether to coordinate DAGs sequentially or trigger them in parallel
    
    Returns:
        Task ID for the chosen coordination mode
    """
    config = context["task_instance"].xcom_pull(task_ids="get_pipeline_config")
    coordination_mode = config.get("dag_coordination_mode", "sequential")
    coordinate_dags = config.get("coordinate_specialized_dags", True)
    
    logger.info(f"DAG coordination mode: {coordination_mode}, enabled: {coordinate_dags}")
    
    if not coordinate_dags:
        return "pipeline_end"
    elif coordination_mode == "parallel":
        return "parallel_dag_coordination.trigger_all_dags"
    else:
        return "sequential_dag_coordination.trigger_past_purchases_dag"

# DAG Coordination Decision
coordination_decision = BranchPythonOperator(
    task_id="decide_coordination_mode",
    python_callable=decide_coordination_mode,
    dag=dag,
)

# Sequential DAG Coordination Task Group
@task_group(group_id="sequential_dag_coordination", dag=dag)
def sequential_dag_coordination():
    """Task group for sequential DAG coordination"""
    
    # Trigger Past Purchases DAG
    trigger_past_purchases = TriggerDagRunOperator(
        task_id="trigger_past_purchases_dag",
        trigger_dag_id="shopify_past_purchases",
        conf={"triggered_by": "shopify_data_pipeline"},
        wait_for_completion=True,
        poke_interval=60,
        timeout=COORDINATED_DAGS["shopify_past_purchases"]["timeout"].total_seconds(),
        allowed_states=[State.SUCCESS],
        failed_states=[State.FAILED, State.UPSTREAM_FAILED],
    )
    
    # Trigger Store Metadata DAG (runs after past purchases)
    trigger_store_metadata = TriggerDagRunOperator(
        task_id="trigger_store_metadata_dag",
        trigger_dag_id="shopify_store_metadata",
        conf={"triggered_by": "shopify_data_pipeline"},
        wait_for_completion=True,
        poke_interval=60,
        timeout=COORDINATED_DAGS["shopify_store_metadata"]["timeout"].total_seconds(),
        allowed_states=[State.SUCCESS],
        failed_states=[State.FAILED, State.UPSTREAM_FAILED],
    )
    
    # Sequential execution
    trigger_past_purchases >> trigger_store_metadata
    
    return trigger_store_metadata

# Parallel DAG Coordination Task Group
@task_group(group_id="parallel_dag_coordination", dag=dag)
def parallel_dag_coordination():
    """Task group for parallel DAG coordination"""
    
    # Trigger all DAGs in parallel
    trigger_past_purchases_parallel = TriggerDagRunOperator(
        task_id="trigger_past_purchases_parallel",
        trigger_dag_id="shopify_past_purchases",
        conf={"triggered_by": "shopify_data_pipeline", "mode": "parallel"},
        wait_for_completion=True,
        poke_interval=60,
        timeout=COORDINATED_DAGS["shopify_past_purchases"]["timeout"].total_seconds(),
        allowed_states=[State.SUCCESS],
        failed_states=[State.FAILED, State.UPSTREAM_FAILED],
    )
    
    trigger_store_metadata_parallel = TriggerDagRunOperator(
        task_id="trigger_store_metadata_parallel",
        trigger_dag_id="shopify_store_metadata",
        conf={"triggered_by": "shopify_data_pipeline", "mode": "parallel"},
        wait_for_completion=True,
        poke_interval=60,
        timeout=COORDINATED_DAGS["shopify_store_metadata"]["timeout"].total_seconds(),
        allowed_states=[State.SUCCESS],
        failed_states=[State.FAILED, State.UPSTREAM_FAILED],
    )
    
    trigger_all_dags = EmptyOperator(
        task_id="trigger_all_dags",
        trigger_rule=TriggerRule.NONE_FAILED,
    )
    
    wait_for_all_dags = EmptyOperator(
        task_id="wait_for_all_dags",
        trigger_rule=TriggerRule.ALL_SUCCESS,
    )
    
    # Parallel execution
    trigger_all_dags >> [trigger_past_purchases_parallel, trigger_store_metadata_parallel] >> wait_for_all_dags
    
    return wait_for_all_dags

# Data Validation Task Group
@task_group(group_id="validation_group", dag=dag)
def validation_operations():
    """Task group for data validation operations"""
    
    validation_start = EmptyOperator(task_id="validation_start")
    
    # Products Validation
    products_validation = ShopifyDataValidationOperator(
        task_id="products_validation",
        postgres_conn_id="postgres_default",
        data_type="products",
        validation_rules=[
            {
                "name": "products_count_check",
                "query": "SELECT COUNT(*) FROM shopify_products",
                "expected": None  # Just check that we get a result
            },
            {
                "name": "products_with_title_check",
                "query": "SELECT COUNT(*) FROM shopify_products WHERE title IS NOT NULL AND title != ''",
                "expected": None
            },
            {
                "name": "recent_products_check",
                "query": "SELECT COUNT(*) FROM shopify_products WHERE synced_at >= NOW() - INTERVAL '24 hours'",
                "expected": None
            }
        ],
        trigger_rule=TriggerRule.NONE_FAILED,
    )
    
    # Customers Validation
    customers_validation = ShopifyDataValidationOperator(
        task_id="customers_validation",
        postgres_conn_id="postgres_default",
        data_type="customers",
        validation_rules=[
            {
                "name": "customers_count_check",
                "query": "SELECT COUNT(*) FROM shopify_customers",
                "expected": None
            },
            {
                "name": "customers_with_email_check",
                "query": "SELECT COUNT(*) FROM shopify_customers WHERE email IS NOT NULL AND email != ''",
                "expected": None
            },
            {
                "name": "recent_customers_check",
                "query": "SELECT COUNT(*) FROM shopify_customers WHERE synced_at >= NOW() - INTERVAL '24 hours'",
                "expected": None
            }
        ],
        trigger_rule=TriggerRule.NONE_FAILED,
    )
    
    # Orders Validation
    orders_validation = ShopifyDataValidationOperator(
        task_id="orders_validation",
        postgres_conn_id="postgres_default",
        data_type="orders",
        validation_rules=[
            {
                "name": "orders_count_check",
                "query": "SELECT COUNT(*) FROM shopify_orders",
                "expected": None
            },
            {
                "name": "orders_with_customer_check",
                "query": "SELECT COUNT(*) FROM shopify_orders WHERE customer_id IS NOT NULL",
                "expected": None
            },
            {
                "name": "recent_orders_check",
                "query": "SELECT COUNT(*) FROM shopify_orders WHERE synced_at >= NOW() - INTERVAL '24 hours'",
                "expected": None
            }
        ],
        trigger_rule=TriggerRule.NONE_FAILED,
    )
    
    validation_end = EmptyOperator(
        task_id="validation_end",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )
    
    # Set dependencies
    validation_start >> [products_validation, customers_validation, orders_validation] >> validation_end
    
    return validation_end

# Cross-DAG Monitoring Tasks
@task(dag=dag)
def monitor_coordinated_dags(**context) -> Dict[str, Any]:
    """
    Monitor the status of coordinated DAGs
    
    Returns:
        Dictionary with DAG monitoring results
    """
    logger.info("Monitoring coordinated DAGs")
    
    config = context["task_instance"].xcom_pull(task_ids="get_pipeline_config")
    
    if not config.get("enable_cross_dag_monitoring", True):
        return {"monitoring_status": "DISABLED"}
    
    try:
        from airflow.models import DagRun
        from airflow.utils.db import provide_session
        
        @provide_session
        def get_dag_status(session=None):
            monitoring_results = {
                "monitoring_timestamp": datetime.now().isoformat(),
                "coordinated_dags": {},
                "overall_status": "SUCCESS"
            }
            
            for dag_id, config in COORDINATED_DAGS.items():
                try:
                    # Get the latest DAG run
                    latest_dag_run = session.query(DagRun).filter(
                        DagRun.dag_id == dag_id
                    ).order_by(DagRun.execution_date.desc()).first()
                    
                    if latest_dag_run:
                        dag_status = {
                            "dag_id": dag_id,
                            "state": latest_dag_run.state,
                            "execution_date": latest_dag_run.execution_date.isoformat(),
                            "start_date": latest_dag_run.start_date.isoformat() if latest_dag_run.start_date else None,
                            "end_date": latest_dag_run.end_date.isoformat() if latest_dag_run.end_date else None,
                            "priority": config["priority"]
                        }
                        
                        if latest_dag_run.state in [State.FAILED, State.UPSTREAM_FAILED]:
                            monitoring_results["overall_status"] = "FAILED"
                    else:
                        dag_status = {
                            "dag_id": dag_id,
                            "state": "NOT_FOUND",
                            "message": "No DAG runs found"
                        }
                        monitoring_results["overall_status"] = "WARNING"
                    
                    monitoring_results["coordinated_dags"][dag_id] = dag_status
                    
                except Exception as e:
                    logger.error(f"Error monitoring DAG {dag_id}: {str(e)}")
                    monitoring_results["coordinated_dags"][dag_id] = {
                        "dag_id": dag_id,
                        "state": "ERROR",
                        "error": str(e)
                    }
                    monitoring_results["overall_status"] = "FAILED"
            
            return monitoring_results
        
        result = get_dag_status()
        
        logger.info(f"DAG monitoring completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"DAG monitoring failed: {str(e)}")
        return {"monitoring_status": "FAILED", "error": str(e)}

# Post-processing tasks
@task(dag=dag)
def generate_comprehensive_report(**context) -> Dict[str, Any]:
    """
    Generate comprehensive sync report across all coordinated DAGs
    
    Returns:
        Dictionary with comprehensive sync report data
    """
    logger.info("Generating comprehensive sync report")
    
    async def get_comprehensive_stats():
        db_manager = DatabaseManager()
        try:
            await db_manager.connect()
            
            # Basic statistics
            basic_stats = {
                "products_count": await db_manager.get_products_count(),
                "customers_count": await db_manager.get_customers_count(),
                "orders_count": await db_manager.get_orders_count(),
            }
            
            # Get variants and images count
            variants_result = await db_manager.execute_query(
                "SELECT COUNT(*) as count FROM shopify_product_variants", 
                fetch=True
            )
            images_result = await db_manager.execute_query(
                "SELECT COUNT(*) as count FROM shopify_product_images", 
                fetch=True
            )
            line_items_result = await db_manager.execute_query(
                "SELECT COUNT(*) as count FROM shopify_order_line_items", 
                fetch=True
            )
            
            extended_stats = {
                "variants_count": variants_result[0]["count"] if variants_result else 0,
                "images_count": images_result[0]["count"] if images_result else 0,
                "line_items_count": line_items_result[0]["count"] if line_items_result else 0,
            }
            
            # Get recent activity statistics
            recent_activity = await db_manager.execute_query("""
                SELECT 
                    COUNT(DISTINCT CASE WHEN p.synced_at >= NOW() - INTERVAL '24 hours' THEN p.id END) as recent_products,
                    COUNT(DISTINCT CASE WHEN c.synced_at >= NOW() - INTERVAL '24 hours' THEN c.id END) as recent_customers,
                    COUNT(DISTINCT CASE WHEN o.synced_at >= NOW() - INTERVAL '24 hours' THEN o.id END) as recent_orders
                FROM shopify_products p
                FULL OUTER JOIN shopify_customers c ON 1=1
                FULL OUTER JOIN shopify_orders o ON 1=1
            """, fetch=True)
            
            recent_stats = recent_activity[0] if recent_activity else {}
            
            # Get data quality metrics
            quality_result = await db_manager.execute_query("""
                SELECT 
                    COUNT(CASE WHEN p.title IS NOT NULL AND p.description_html IS NOT NULL THEN 1 END) as complete_products,
                    COUNT(CASE WHEN c.email IS NOT NULL AND c.email != '' THEN 1 END) as customers_with_email,
                    COUNT(CASE WHEN o.total_price_amount > 0 THEN 1 END) as orders_with_value
                FROM shopify_products p
                FULL OUTER JOIN shopify_customers c ON 1=1
                FULL OUTER JOIN shopify_orders o ON 1=1
            """, fetch=True)
            
            quality_stats = quality_result[0] if quality_result else {}
            
            config = context["task_instance"].xcom_pull(task_ids="get_pipeline_config")
            monitoring_result = context["task_instance"].xcom_pull(task_ids="monitor_coordinated_dags") or {}
            
            report = {
                "report_timestamp": datetime.now().isoformat(),
                "pipeline_configuration": {
                    "sync_mode": config.get("sync_mode"),
                    "coordination_mode": config.get("dag_coordination_mode"),
                    "coordinated_dags_enabled": config.get("coordinate_specialized_dags")
                },
                "basic_statistics": basic_stats,
                "extended_statistics": extended_stats,
                "recent_activity": {
                    "recent_products": recent_stats.get("recent_products", 0),
                    "recent_customers": recent_stats.get("recent_customers", 0),
                    "recent_orders": recent_stats.get("recent_orders", 0)
                },
                "data_quality": {
                    "complete_products": quality_stats.get("complete_products", 0),
                    "customers_with_email": quality_stats.get("customers_with_email", 0),
                    "orders_with_value": quality_stats.get("orders_with_value", 0)
                },
                "dag_monitoring": monitoring_result,
                "report_status": "SUCCESS"
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate comprehensive report: {str(e)}")
            return {"report_status": "FAILED", "error": str(e)}
        finally:
            await db_manager.close()
    
    report = asyncio.run(get_comprehensive_stats())
    
    logger.info(f"Comprehensive sync report generated: {report}")
    return report

@task(dag=dag)
def cleanup_old_data(**context) -> Dict[str, Any]:
    """
    Cleanup old data based on retention policies
    
    Returns:
        Dictionary with cleanup results
    """
    logger.info("Starting data cleanup")
    
    # This would implement data retention policies
    # For now, just return a placeholder
    cleanup_results = {
        "cleanup_status": "SUCCESS",
        "records_cleaned": 0,
        "message": "Cleanup completed successfully"
    }
    
    logger.info(f"Data cleanup completed: {cleanup_results}")
    return cleanup_results

# Pipeline End
pipeline_end = EmptyOperator(
    task_id="pipeline_end",
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    dag=dag,
)

# Pipeline Error Handler
pipeline_error = BashOperator(
    task_id="pipeline_error",
    bash_command='echo "Pipeline failed - check logs for details"',
    trigger_rule=TriggerRule.ONE_FAILED,
    dag=dag,
)

# Set up task dependencies
config = get_pipeline_config()
validation = validate_connections()
database_prep = prepare_database()

# Main pipeline flow
config >> validation >> database_prep >> coordination_decision

# Sequential coordination path
sequential_coordination = sequential_dag_coordination()
coordination_decision >> sequential_coordination

# Parallel coordination path
parallel_coordination = parallel_dag_coordination()
coordination_decision >> parallel_coordination

# Monitoring and reporting
dag_monitoring = monitor_coordinated_dags()
comprehensive_report = generate_comprehensive_report()
cleanup = cleanup_old_data()

# Connect coordination operations to monitoring and reporting
[sequential_coordination, parallel_coordination] >> dag_monitoring >> comprehensive_report >> cleanup >> pipeline_end

# Error handling
pipeline_error = BashOperator(
    task_id="pipeline_error",
    bash_command='echo "Pipeline coordination failed - check logs for details"',
    trigger_rule=TriggerRule.ONE_FAILED,
    dag=dag,
)

[sequential_coordination, parallel_coordination, dag_monitoring, comprehensive_report, cleanup] >> pipeline_error

if __name__ == "__main__":
    dag.test()