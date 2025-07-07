"""
Airflow DAGs for Shopify data integration.

This module contains all DAG definitions for orchestrating Shopify data workflows.
Each DAG file should define a single DAG and expose it through a 'dag' variable.

DAGs included:
- shopify_customer_data_dag: Extract and process customer data
- shopify_order_data_dag: Extract and process order data  
- shopify_product_data_dag: Extract and process product data
- shopify_analytics_dag: Generate analytics and insights
"""

# Import all DAGs to make them available to Airflow
# This allows Airflow to discover and load the DAGs when scanning this directory

try:
    # Import example DAGs - these should be replaced with actual DAG implementations
    from .shopify_customer_data_dag import dag as shopify_customer_data_dag
    from .shopify_order_data_dag import dag as shopify_order_data_dag
    
    # List of available DAGs
    __all__ = [
        'shopify_customer_data_dag',
        'shopify_order_data_dag',
    ]
    
except ImportError as e:
    # In case DAG files don't exist yet, provide a helpful message
    print(f"Warning: Could not import all DAGs: {e}")
    __all__ = []