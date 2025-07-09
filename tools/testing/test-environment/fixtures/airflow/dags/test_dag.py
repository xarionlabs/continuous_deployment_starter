from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.postgres import PostgresOperator
from airflow.hooks.postgres_hook import PostgresHook
import logging

# Default arguments for the DAG
default_args = {
    'owner': 'test-admin',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create the DAG
dag = DAG(
    'test_deployment_dag',
    default_args=default_args,
    description='Test deployment simulation DAG',
    schedule_interval=timedelta(hours=1),
    catchup=False,
    tags=['test', 'deployment'],
)

def log_deployment_start(**context):
    """Log the start of a deployment"""
    logging.info(f"Starting deployment test at {datetime.now()}")
    logging.info(f"Context: {context}")
    return "deployment_started"

def simulate_build_process(**context):
    """Simulate building applications"""
    import time
    import random
    
    # Simulate build time
    build_time = random.uniform(1, 3)
    time.sleep(build_time)
    
    logging.info(f"Build completed in {build_time:.2f} seconds")
    return f"build_completed_{build_time:.2f}s"

def simulate_test_process(**context):
    """Simulate running tests"""
    import time
    import random
    
    # Simulate test time
    test_time = random.uniform(1, 2)
    time.sleep(test_time)
    
    # Simulate occasional test failures (10% chance)
    if random.random() < 0.1:
        raise Exception("Simulated test failure")
    
    logging.info(f"Tests completed in {test_time:.2f} seconds")
    return f"tests_passed_{test_time:.2f}s"

def update_deployment_status(**context):
    """Update deployment status in database"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='test_postgres')
        
        # Insert deployment record
        sql = """
        INSERT INTO deployments (deployment_id, app_name, version, environment, status, completed_at)
        VALUES (%(deployment_id)s, %(app_name)s, %(version)s, %(environment)s, %(status)s, CURRENT_TIMESTAMP)
        ON CONFLICT (deployment_id) 
        DO UPDATE SET 
            status = EXCLUDED.status,
            completed_at = EXCLUDED.completed_at
        """
        
        postgres_hook.run(sql, parameters={
            'deployment_id': f"airflow_deploy_{context['ts_nodash']}",
            'app_name': 'test-airflow-dag',
            'version': '1.0.0',
            'environment': 'test',
            'status': 'completed'
        })
        
        logging.info("Deployment status updated successfully")
        return "status_updated"
        
    except Exception as e:
        logging.error(f"Failed to update deployment status: {e}")
        raise

# Define tasks
start_task = PythonOperator(
    task_id='log_deployment_start',
    python_callable=log_deployment_start,
    dag=dag,
)

build_task = PythonOperator(
    task_id='simulate_build',
    python_callable=simulate_build_process,
    dag=dag,
)

test_task = PythonOperator(
    task_id='simulate_tests',
    python_callable=simulate_test_process,
    dag=dag,
)

health_check_task = BashOperator(
    task_id='health_check',
    bash_command='curl -f http://test-app1:8000/health && curl -f http://test-app2:3000/health',
    dag=dag,
)

db_update_task = PythonOperator(
    task_id='update_deployment_status',
    python_callable=update_deployment_status,
    dag=dag,
)

completion_task = BashOperator(
    task_id='deployment_complete',
    bash_command='echo "Deployment test completed successfully at $(date)"',
    dag=dag,
)

# Set task dependencies
start_task >> build_task >> test_task >> health_check_task >> db_update_task >> completion_task