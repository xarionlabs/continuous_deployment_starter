"""
Airflow DAGs for Shopify data integration.

This module contains all DAG definitions for orchestrating Shopify data workflows.
Each DAG file should define a single DAG and expose it through a 'dag' variable.

DAGs included:
- shopify_data_pipeline: Main orchestration DAG that coordinates all data workflows
- shopify_past_purchases: Customer purchase data using getCustomersWithOrders query
- shopify_store_metadata: Product catalog data using getAllProductData and getProductImages queries
- shopify_customer_data_dag: Extract and process customer data (legacy)
- shopify_order_data_dag: Extract and process order data (legacy)
"""

# Import all DAGs to make them available to Airflow
# This allows Airflow to discover and load the DAGs when scanning this directory

try:
    # Import main production DAGs
    from .shopify_data_pipeline import dag as shopify_data_pipeline
    from .shopify_past_purchases import dag as shopify_past_purchases
    from .shopify_store_metadata import dag as shopify_store_metadata
    
    # Import legacy DAGs if they exist
    try:
        from .shopify_customer_data_dag import dag as shopify_customer_data_dag
        from .shopify_order_data_dag import dag as shopify_order_data_dag
        legacy_dags = ['shopify_customer_data_dag', 'shopify_order_data_dag']
    except ImportError:
        legacy_dags = []
    
    # List of available DAGs
    __all__ = [
        'shopify_data_pipeline',
        'shopify_past_purchases', 
        'shopify_store_metadata',
    ] + legacy_dags
    
except ImportError as e:
    # In case DAG files don't exist yet, provide a helpful message
    print(f"Warning: Could not import all DAGs: {e}")
    __all__ = []