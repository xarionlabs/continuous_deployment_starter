"""
Shopify Customer Data DAG

This DAG extracts customer data from Shopify using the GraphQL API
and stores it in the PXY6 application database.

Schedule: Daily at 2:00 AM UTC
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import asyncio
from airflow.operators.bash import BashOperator
import structlog

from utils.shopify_client import ShopifyGraphQLClient
from utils.database import DatabaseManager

logger = structlog.get_logger(__name__)

# DAG default arguments
default_args = {
    'owner': 'pxy6-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'catchup': False,
}

# DAG definition
dag = DAG(
    'shopify_customer_data',
    default_args=default_args,
    description='Extract and process Shopify customer data',
    schedule='0 2 * * *',  # Daily at 2:00 AM UTC
    max_active_runs=1,
    tags=['shopify', 'customers', 'data-extraction'],
)


def extract_customer_data(**context):
    """
    Extract customer data from Shopify GraphQL API.
    
    Args:
        **context: Airflow context containing task instance info
    """
    logger.info("Starting customer data extraction")
    
    # Initialize Shopify client
    shopify_client = ShopifyGraphQLClient()
    
    # Test connection
    if not shopify_client.test_connection():
        raise Exception("Failed to connect to Shopify API")
    
    customers = []
    cursor = None
    page_count = 0
    
    try:
        # Extract customers with pagination
        while True:
            page_count += 1
            logger.info(f"Extracting customer page {page_count}")
            
            result = shopify_client.get_customers(limit=100, cursor=cursor)
            
            # Extract customer data from GraphQL result
            edges = result.get('customers', {}).get('edges', [])
            
            if not edges:
                break
            
            # Process customer data
            for edge in edges:
                customer_data = edge['node']
                customers.append({
                    'shopify_id': customer_data['id'],
                    'email': customer_data.get('email'),
                    'first_name': customer_data.get('firstName'),
                    'last_name': customer_data.get('lastName'),
                    'created_at': customer_data.get('createdAt'),
                    'updated_at': customer_data.get('updatedAt'),
                    'orders_count': customer_data.get('ordersCount', 0),
                    'total_spent': customer_data.get('totalSpent', '0.00'),
                    'tags': customer_data.get('tags', []),
                    'phone': customer_data.get('phone'),
                    'accepts_marketing': customer_data.get('acceptsMarketing', False),
                    'accepts_marketing_updated_at': customer_data.get('acceptsMarketingUpdatedAt'),
                })
            
            # Check if there are more pages
            page_info = result.get('customers', {}).get('pageInfo', {})
            if not page_info.get('hasNextPage', False):
                break
            
            cursor = page_info.get('endCursor')
    
    except Exception as e:
        logger.error(f"Error extracting customer data: {e}")
        raise
    
    logger.info(f"Extracted {len(customers)} customers from {page_count} pages")
    
    # Store extracted data in XCom for the next task
    context['task_instance'].xcom_push(key='customer_data', value=customers)
    
    return len(customers)


def store_customer_data(**context):
    """
    Sync wrapper for async store_customer_data function.
    """
    return asyncio.run(_store_customer_data(**context))


async def _store_customer_data(**context):
    """
    Store customer data in the PXY6 application database.
    
    Args:
        **context: Airflow context containing task instance info
    """
    logger.info("Starting customer data storage")
    
    # Get customer data from previous task
    customer_data = context['task_instance'].xcom_pull(
        task_ids='extract_customer_data', 
        key='customer_data'
    )
    
    if not customer_data:
        logger.warning("No customer data found to store")
        return 0
    
    try:
        async with DatabaseManager() as db_manager:
            # Ensure tables exist
            await db_manager.create_tables()
            
            stored_count = 0
            
            for customer in customer_data:
                logger.debug(f"Storing customer: {customer.get('email')}")
                
                # Convert to format expected by upsert_customer
                customer_record = {
                    'id': customer.get('shopify_id'),
                    'email': customer.get('email'),
                    'firstName': customer.get('first_name'),
                    'lastName': customer.get('last_name'),
                    'phone': customer.get('phone'),
                    'createdAt': customer.get('created_at'),
                    'updatedAt': customer.get('updated_at'),
                    'acceptsMarketing': customer.get('accepts_marketing'),
                    'acceptsMarketingUpdatedAt': customer.get('accepts_marketing_updated_at'),
                    'tags': customer.get('tags', []),
                    'numberOfOrders': customer.get('orders_count', 0),
                    'totalSpentV2': {
                        'amount': customer.get('total_spent', '0.00'),
                        'currencyCode': 'USD'
                    }
                }
                
                await db_manager.upsert_customer(customer_record)
                stored_count += 1
            
    except Exception as e:
        logger.error(f"Error storing customer data: {e}")
        raise
    
    logger.info(f"Successfully stored {stored_count} customer records")
    
    return stored_count


def validate_customer_data(**context):
    """
    Sync wrapper for async validate_customer_data function.
    """
    return asyncio.run(_validate_customer_data(**context))


async def _validate_customer_data(**context):
    """
    Validate the stored customer data.
    
    Args:
        **context: Airflow context containing task instance info
    """
    logger.info("Starting customer data validation")
    
    try:
        async with DatabaseManager() as db_manager:
            # Perform validation queries
            total_customers = await db_manager.get_customers_count()
            
            # Check for customers with email addresses
            customers_with_email_result = await db_manager.execute_query(
                "SELECT COUNT(*) as count FROM shopify_customers WHERE email IS NOT NULL",
                fetch=True
            )
            customers_with_email = customers_with_email_result[0]["count"] if customers_with_email_result else 0
            
            # Check for customers with orders
            customers_with_orders_result = await db_manager.execute_query(
                "SELECT COUNT(*) as count FROM shopify_customers WHERE number_of_orders > 0",
                fetch=True
            )
            customers_with_orders = customers_with_orders_result[0]["count"] if customers_with_orders_result else 0
            
            validation_results = {
                'total_customers': total_customers,
                'customers_with_email': customers_with_email,
                'customers_with_orders': customers_with_orders,
            }
            
            logger.info("Customer data validation completed", **validation_results)
            
            return validation_results
    
    except Exception as e:
        logger.error(f"Error validating customer data: {e}")
        raise


# Define DAG tasks
extract_task = PythonOperator(
    task_id='extract_customer_data',
    python_callable=extract_customer_data,
    dag=dag,
)

store_task = PythonOperator(
    task_id='store_customer_data',
    python_callable=store_customer_data,
    dag=dag,
)

validate_task = PythonOperator(
    task_id='validate_customer_data',
    python_callable=validate_customer_data,
    dag=dag,
)

# Health check task
health_check_task = BashOperator(
    task_id='health_check',
    bash_command='echo "Customer data pipeline completed successfully"',
    dag=dag,
)

# Set task dependencies
extract_task >> store_task >> validate_task >> health_check_task