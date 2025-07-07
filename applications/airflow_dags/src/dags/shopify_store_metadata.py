"""
Shopify Store Metadata DAG - Product Catalog Synchronization

This DAG handles comprehensive synchronization of product catalog data from Shopify
using the getAllProductData and getProductImages GraphQL queries. It extracts complete
product information including variants, images, metafields, collections, and inventory data.

Features:
- Uses Airflow 3.0.2 @task decorators for modern workflow patterns
- Connects to pxy6 database using pxy6_airflow user
- Comprehensive product data extraction with variants and images
- Advanced error handling and retry logic
- Incremental and full sync modes with intelligent change detection
- Data quality validation and consistency checks
- REST API triggerable for manual execution
- Comprehensive logging and performance monitoring

Schedule: Daily at 3:00 AM UTC
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import json
import hashlib

from airflow import DAG
from airflow.decorators import task, task_group
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import BranchPythonOperator
from airflow.utils.trigger_rule import TriggerRule
from airflow.exceptions import AirflowException
from airflow.models import Variable
from airflow.sensors.time_delta import TimeDeltaSensor

import structlog
from hooks.shopify_hook import ShopifyHook
from utils.database import DatabaseManager
from utils.shopify_graphql import ShopifyGraphQLClient

logger = structlog.get_logger(__name__)

# DAG Configuration
DAG_ID = "shopify_store_metadata"
DESCRIPTION = "Synchronize product catalog data from Shopify using getAllProductData and getProductImages queries"
SCHEDULE_INTERVAL = "0 3 * * *"  # Daily at 3:00 AM UTC
START_DATE = datetime(2024, 1, 1)
CATCHUP = False
MAX_ACTIVE_RUNS = 1
MAX_ACTIVE_TASKS = 6
DAGRUN_TIMEOUT = timedelta(hours=6)

# Default arguments with comprehensive error handling
default_args = {
    "owner": "pxy6-data-team",
    "depends_on_past": False,
    "start_date": START_DATE,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "execution_timeout": timedelta(hours=3),
}

# Create DAG
dag = DAG(
    DAG_ID,
    default_args=default_args,
    description=DESCRIPTION,
    schedule_interval=SCHEDULE_INTERVAL,
    catchup=CATCHUP,
    max_active_runs=MAX_ACTIVE_RUNS,
    max_active_tasks=MAX_ACTIVE_TASKS,
    dagrun_timeout=DAGRUN_TIMEOUT,
    tags=["shopify", "products", "catalog", "metadata", "etl"],
    doc_md=__doc__,
)

# Configuration Tasks
@task(dag=dag)
def get_catalog_sync_config(**context) -> Dict[str, Any]:
    """
    Get synchronization configuration for product catalog
    
    Returns:
        Dictionary containing sync configuration
    """
    logger.info("Getting product catalog sync configuration")
    
    config = {
        "sync_mode": Variable.get("shopify_catalog_sync_mode", "incremental"),
        "batch_size": int(Variable.get("shopify_catalog_batch_size", "50")),
        "max_pages": int(Variable.get("shopify_catalog_max_pages", "0")) or None,
        "lookback_hours": int(Variable.get("shopify_catalog_lookback_hours", "24")),
        "include_variants": Variable.get("shopify_catalog_include_variants", "true").lower() == "true",
        "include_images": Variable.get("shopify_catalog_include_images", "true").lower() == "true",
        "include_metafields": Variable.get("shopify_catalog_include_metafields", "true").lower() == "true",
        "include_collections": Variable.get("shopify_catalog_include_collections", "true").lower() == "true",
        "include_inventory": Variable.get("shopify_catalog_include_inventory", "true").lower() == "true",
        "validation_enabled": Variable.get("shopify_catalog_validation", "true").lower() == "true",
        "image_sync_enabled": Variable.get("shopify_catalog_image_sync", "true").lower() == "true",
        "data_quality_threshold": float(Variable.get("shopify_catalog_quality_threshold", "0.98")),
        "parallel_processing": Variable.get("shopify_catalog_parallel", "true").lower() == "true",
        "change_detection": Variable.get("shopify_catalog_change_detection", "true").lower() == "true",
    }
    
    logger.info(f"Product catalog sync configuration: {config}")
    return config

@task(dag=dag)
def validate_catalog_connections(**context) -> Dict[str, Any]:
    """
    Validate Shopify and database connections for catalog sync
    
    Returns:
        Dictionary with connection validation results
    """
    logger.info("Validating connections for catalog sync")
    
    validation_results = {
        "shopify_connection": False,
        "postgres_connection": False,
        "shopify_product_access": False,
        "database_tables_exist": False,
        "overall_status": "FAILED"
    }
    
    try:
        # Test Shopify connection
        shopify_hook = ShopifyHook(shopify_conn_id="shopify_default")
        validation_results["shopify_connection"] = shopify_hook.test_connection()
        
        # Test Shopify GraphQL access for products with enhanced validation
        graphql_client = ShopifyGraphQLClient()
        try:
            # Test with minimal query
            test_result = graphql_client.get_all_product_data(limit=1)
            products_data = test_result.get("products", {})
            edges = products_data.get("edges", [])
            validation_results["shopify_product_access"] = bool(edges is not None)
            
            # Additional validation - check if we can access product images
            if edges and len(edges) > 0:
                product_id = edges[0]["node"]["id"]
                try:
                    images_result = graphql_client.get_product_images(product_id, limit=1)
                    validation_results["shopify_images_access"] = bool(images_result.get("product"))
                    logger.info(f"Product and image access verified for product: {product_id}")
                except Exception as img_error:
                    logger.warning(f"Product images access test failed: {str(img_error)}")
                    validation_results["shopify_images_access"] = False
            else:
                validation_results["shopify_images_access"] = True  # No products to test
                
        except Exception as e:
            logger.warning(f"Product access test failed: {str(e)}")
            validation_results["shopify_product_access"] = False
            validation_results["shopify_images_access"] = False
            validation_results["product_access_error"] = str(e)
        
        shopify_hook.close()
        
        # Test PostgreSQL connection and tables
        async def test_postgres():
            db_manager = DatabaseManager()
            try:
                await db_manager.connect()
                connection_result = await db_manager.test_connection()
                
                # Check if required tables exist
                tables_result = await db_manager.execute_query("""
                    SELECT COUNT(*) as table_count FROM information_schema.tables 
                    WHERE table_name IN ('shopify_products', 'shopify_product_variants', 'shopify_product_images')
                """, fetch=True)
                
                tables_exist = tables_result[0]["table_count"] == 3 if tables_result else False
                
                return connection_result, tables_exist
            finally:
                await db_manager.close()
        
        postgres_conn, tables_exist = asyncio.run(test_postgres())
        validation_results["postgres_connection"] = postgres_conn
        validation_results["database_tables_exist"] = tables_exist
        
        # Overall status
        if all([
            validation_results["shopify_connection"],
            validation_results["postgres_connection"],
            validation_results["shopify_product_access"],
            validation_results["database_tables_exist"]
        ]):
            validation_results["overall_status"] = "PASSED"
        
    except Exception as e:
        logger.error(f"Connection validation failed: {str(e)}")
        validation_results["error"] = str(e)
    
    logger.info(f"Catalog connection validation results: {validation_results}")
    
    if validation_results["overall_status"] == "FAILED":
        raise AirflowException(f"Connection validation failed: {validation_results}")
    
    return validation_results

@task(dag=dag)
def prepare_catalog_database(**context) -> Dict[str, Any]:
    """
    Prepare database tables for product catalog data
    
    Returns:
        Dictionary with database preparation results
    """
    logger.info("Preparing database tables for product catalog")
    
    async def setup_catalog_tables():
        db_manager = DatabaseManager()
        try:
            await db_manager.connect()
            
            # Create base tables
            await db_manager.create_tables()
            
            # Create enhanced product collections table
            await db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS shopify_product_collections (
                    id SERIAL PRIMARY KEY,
                    product_id VARCHAR(255) REFERENCES shopify_products(id),
                    collection_id VARCHAR(255),
                    collection_title VARCHAR(500),
                    collection_handle VARCHAR(500),
                    position INTEGER,
                    raw_data JSONB,
                    synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(product_id, collection_id)
                );
            """)
            
            # Create inventory tracking table
            await db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS shopify_inventory_levels (
                    id SERIAL PRIMARY KEY,
                    variant_id VARCHAR(255) REFERENCES shopify_product_variants(id),
                    location_id VARCHAR(255),
                    location_name VARCHAR(500),
                    available INTEGER,
                    updated_at TIMESTAMP WITH TIME ZONE,
                    raw_data JSONB,
                    synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(variant_id, location_id)
                );
            """)
            
            # Create product analytics table
            await db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS shopify_product_analytics (
                    product_id VARCHAR(255) PRIMARY KEY REFERENCES shopify_products(id),
                    total_variants INTEGER DEFAULT 0,
                    total_images INTEGER DEFAULT 0,
                    total_inventory INTEGER DEFAULT 0,
                    available_variants INTEGER DEFAULT 0,
                    price_range_min DECIMAL(10, 2),
                    price_range_max DECIMAL(10, 2),
                    last_updated TIMESTAMP WITH TIME ZONE,
                    days_since_update INTEGER,
                    has_metafields BOOLEAN DEFAULT FALSE,
                    has_seo BOOLEAN DEFAULT FALSE,
                    collection_count INTEGER DEFAULT 0,
                    data_completeness_score DECIMAL(5, 4),
                    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create product change tracking table
            await db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS shopify_product_changes (
                    id SERIAL PRIMARY KEY,
                    product_id VARCHAR(255),
                    change_type VARCHAR(50), -- created, updated, deleted
                    field_name VARCHAR(100),
                    old_value TEXT,
                    new_value TEXT,
                    change_hash VARCHAR(64),
                    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create additional indexes for performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_shopify_product_collections_product_id ON shopify_product_collections(product_id);",
                "CREATE INDEX IF NOT EXISTS idx_shopify_product_collections_collection_id ON shopify_product_collections(collection_id);",
                "CREATE INDEX IF NOT EXISTS idx_shopify_inventory_levels_variant_id ON shopify_inventory_levels(variant_id);",
                "CREATE INDEX IF NOT EXISTS idx_shopify_inventory_levels_location_id ON shopify_inventory_levels(location_id);",
                "CREATE INDEX IF NOT EXISTS idx_shopify_product_changes_product_id ON shopify_product_changes(product_id);",
                "CREATE INDEX IF NOT EXISTS idx_shopify_product_changes_detected_at ON shopify_product_changes(detected_at);",
                "CREATE INDEX IF NOT EXISTS idx_shopify_products_status ON shopify_products(status);",
                "CREATE INDEX IF NOT EXISTS idx_shopify_products_product_type ON shopify_products(product_type);",
                "CREATE INDEX IF NOT EXISTS idx_shopify_products_vendor ON shopify_products(vendor);",
                "CREATE INDEX IF NOT EXISTS idx_shopify_product_variants_product_id ON shopify_product_variants(product_id);",
                "CREATE INDEX IF NOT EXISTS idx_shopify_product_variants_sku ON shopify_product_variants(sku);",
                "CREATE INDEX IF NOT EXISTS idx_shopify_product_images_product_id ON shopify_product_images(product_id);"
            ]
            
            for index_query in indexes:
                try:
                    await db_manager.execute_query(index_query)
                except Exception as e:
                    logger.warning(f"Index creation warning: {str(e)}")
            
            # Get current statistics
            stats = {
                "products_count": await db_manager.get_products_count(),
                "variants_count": await get_variants_count(db_manager),
                "images_count": await get_images_count(db_manager),
                "setup_status": "SUCCESS"
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Catalog database setup failed: {str(e)}")
            return {"setup_status": "FAILED", "error": str(e)}
        finally:
            await db_manager.close()
    
    result = asyncio.run(setup_catalog_tables())
    
    if result.get("setup_status") == "FAILED":
        raise AirflowException(f"Catalog database preparation failed: {result.get('error')}")
    
    logger.info(f"Catalog database preparation completed: {result}")
    return result

def decide_catalog_sync_mode(**context) -> str:
    """
    Decide whether to run full or incremental catalog sync
    
    Returns:
        Task ID for the chosen sync mode
    """
    config = context["task_instance"].xcom_pull(task_ids="get_catalog_sync_config")
    sync_mode = config.get("sync_mode", "incremental")
    
    logger.info(f"Catalog sync mode decision: {sync_mode}")
    
    if sync_mode == "full":
        return "full_catalog_sync_group.extract_all_products"
    else:
        return "incremental_catalog_sync_group.extract_updated_products"

# Sync Mode Decision
catalog_sync_decision = BranchPythonOperator(
    task_id="decide_catalog_sync_mode",
    python_callable=decide_catalog_sync_mode,
    dag=dag,
)

# Full Catalog Sync Task Group
@task_group(group_id="full_catalog_sync_group", dag=dag)
def full_catalog_sync_operations():
    """Task group for full synchronization of product catalog data"""
    
    @task
    def extract_all_products(**context) -> Dict[str, Any]:
        """Extract all products with complete metadata"""
        logger.info("Starting full extraction of product catalog")
        
        config = context["task_instance"].xcom_pull(task_ids="get_catalog_sync_config")
        batch_size = config.get("batch_size", 50)
        max_pages = config.get("max_pages")
        
        try:
            graphql_client = ShopifyGraphQLClient()
            
            products_data = []
            cursor = None
            page_count = 0
            
            while True:
                page_count += 1
                logger.info(f"Extracting page {page_count} of products")
                
                # Get all product data using the GraphQL client
                result = graphql_client.get_all_product_data(
                    limit=batch_size,
                    cursor=cursor
                )
                
                products = result.get("products", {})
                edges = products.get("edges", [])
                
                if not edges:
                    logger.info("No more products to extract")
                    break
                
                # Process product data
                for edge in edges:
                    product_node = edge["node"]
                    products_data.append(product_node)
                
                logger.info(f"Extracted {len(edges)} products on page {page_count}")
                
                # Check pagination
                page_info = products.get("pageInfo", {})
                if not page_info.get("hasNextPage", False):
                    break
                
                cursor = page_info.get("endCursor")
                
                # Check max pages limit
                if max_pages and page_count >= max_pages:
                    logger.info(f"Reached max pages limit: {max_pages}")
                    break
            
            extraction_result = {
                "total_products": len(products_data),
                "pages_processed": page_count,
                "extraction_status": "SUCCESS"
            }
            
            logger.info(f"Full product extraction completed: {extraction_result}")
            
            # Store data for processing
            context["task_instance"].xcom_push(
                key="all_products_data",
                value=products_data
            )
            
            return extraction_result
            
        except Exception as e:
            logger.error(f"Full product extraction failed: {str(e)}")
            raise AirflowException(f"Full product extraction failed: {str(e)}")
    
    @task
    def process_all_product_data(**context) -> Dict[str, Any]:
        """Process and load all product data into database"""
        logger.info("Processing all product data for full sync")
        
        products_data = context["task_instance"].xcom_pull(
            task_ids="full_catalog_sync_group.extract_all_products",
            key="all_products_data"
        )
        
        if not products_data:
            raise AirflowException("No product data available for processing")
        
        config = context["task_instance"].xcom_pull(task_ids="get_catalog_sync_config")
        
        async def process_all_data():
            db_manager = DatabaseManager()
            try:
                await db_manager.connect()
                
                processed_products = 0
                processed_variants = 0
                processed_images = 0
                processed_collections = 0
                error_count = 0
                
                for product_data in products_data:
                    try:
                        # Process product
                        await db_manager.upsert_product(product_data)
                        processed_products += 1
                        
                        # Process variants if enabled
                        if config.get("include_variants", True):
                            variants = product_data.get("variants", {}).get("edges", [])
                            for variant_edge in variants:
                                variant_data = variant_edge["node"]
                                variant_data["product_id"] = product_data["id"]
                                
                                await upsert_product_variant(db_manager, variant_data)
                                processed_variants += 1
                                
                                # Process inventory levels
                                if config.get("include_inventory", True):
                                    inventory_item = variant_data.get("inventoryItem", {})
                                    inventory_levels = inventory_item.get("inventoryLevels", {}).get("edges", [])
                                    for level_edge in inventory_levels:
                                        level_data = level_edge["node"]
                                        level_data["variant_id"] = variant_data["id"]
                                        
                                        await upsert_inventory_level(db_manager, level_data)
                        
                        # Process images if enabled
                        if config.get("include_images", True):
                            images = product_data.get("images", {}).get("edges", [])
                            for image_edge in images:
                                image_data = image_edge["node"]
                                image_data["product_id"] = product_data["id"]
                                
                                await upsert_product_image(db_manager, image_data)
                                processed_images += 1
                        
                        # Process collections if enabled
                        if config.get("include_collections", True):
                            collections = product_data.get("collections", {}).get("edges", [])
                            for collection_edge in collections:
                                collection_data = collection_edge["node"]
                                
                                await upsert_product_collection(
                                    db_manager, 
                                    product_data["id"], 
                                    collection_data
                                )
                                processed_collections += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing product {product_data.get('id', 'unknown')}: {str(e)}")
                        error_count += 1
                
                # Calculate product analytics
                await calculate_product_analytics(db_manager)
                
                result = {
                    "processed_products": processed_products,
                    "processed_variants": processed_variants,
                    "processed_images": processed_images,
                    "processed_collections": processed_collections,
                    "error_count": error_count,
                    "processing_status": "SUCCESS"
                }
                
                return result
                
            finally:
                await db_manager.close()
        
        result = asyncio.run(process_all_data())
        
        logger.info(f"All product data processing completed: {result}")
        return result
    
    # Task dependencies
    extract_task = extract_all_products()
    process_task = process_all_product_data()
    
    extract_task >> process_task
    
    return process_task

# Incremental Catalog Sync Task Group
@task_group(group_id="incremental_catalog_sync_group", dag=dag)
def incremental_catalog_sync_operations():
    """Task group for incremental synchronization of product catalog data"""
    
    @task
    def extract_updated_products(**context) -> Dict[str, Any]:
        """Extract products with recent updates"""
        logger.info("Starting incremental extraction of updated products")
        
        config = context["task_instance"].xcom_pull(task_ids="get_catalog_sync_config")
        batch_size = config.get("batch_size", 50)
        lookback_hours = config.get("lookback_hours", 24)
        
        try:
            # Calculate lookback time
            lookback_time = datetime.now() - timedelta(hours=lookback_hours)
            
            graphql_client = ShopifyGraphQLClient()
            
            updated_products = []
            cursor = None
            page_count = 0
            
            while True:
                page_count += 1
                logger.info(f"Extracting page {page_count} of products for updates")
                
                # Get all products (we'll filter for updates locally)
                result = graphql_client.get_all_product_data(
                    limit=batch_size,
                    cursor=cursor
                )
                
                products = result.get("products", {})
                edges = products.get("edges", [])
                
                if not edges:
                    break
                
                # Filter products with recent updates
                for edge in edges:
                    product_node = edge["node"]
                    
                    # Check if product has been updated recently
                    updated_at_str = product_node.get("updatedAt", "")
                    if updated_at_str:
                        try:
                            updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                            if updated_at >= lookback_time:
                                updated_products.append(product_node)
                        except ValueError:
                            logger.warning(f"Invalid date format for product {product_node.get('id')}: {updated_at_str}")
                
                # Check pagination
                page_info = products.get("pageInfo", {})
                if not page_info.get("hasNextPage", False):
                    break
                
                cursor = page_info.get("endCursor")
            
            extraction_result = {
                "total_products_checked": page_count * batch_size,
                "updated_products": len(updated_products),
                "pages_processed": page_count,
                "lookback_hours": lookback_hours,
                "extraction_status": "SUCCESS"
            }
            
            logger.info(f"Incremental product extraction completed: {extraction_result}")
            
            # Store data for processing
            context["task_instance"].xcom_push(
                key="updated_products_data",
                value=updated_products
            )
            
            return extraction_result
            
        except Exception as e:
            logger.error(f"Incremental product extraction failed: {str(e)}")
            raise AirflowException(f"Incremental product extraction failed: {str(e)}")
    
    @task
    def process_updated_product_data(**context) -> Dict[str, Any]:
        """Process and load updated product data"""
        logger.info("Processing updated product data for incremental sync")
        
        products_data = context["task_instance"].xcom_pull(
            task_ids="incremental_catalog_sync_group.extract_updated_products",
            key="updated_products_data"
        )
        
        if not products_data:
            logger.info("No updated product data to process")
            return {"processed_products": 0, "processing_status": "SUCCESS"}
        
        config = context["task_instance"].xcom_pull(task_ids="get_catalog_sync_config")
        
        async def process_updated_data():
            db_manager = DatabaseManager()
            try:
                await db_manager.connect()
                
                processed_products = 0
                processed_variants = 0
                processed_images = 0
                error_count = 0
                changes_detected = 0
                
                for product_data in products_data:
                    try:
                        # Detect changes if enabled
                        if config.get("change_detection", True):
                            change_detected = await detect_product_changes(db_manager, product_data)
                            if change_detected:
                                changes_detected += 1
                        
                        # Process product
                        await db_manager.upsert_product(product_data)
                        processed_products += 1
                        
                        # Process variants, images, etc. (similar to full sync)
                        if config.get("include_variants", True):
                            variants = product_data.get("variants", {}).get("edges", [])
                            for variant_edge in variants:
                                variant_data = variant_edge["node"]
                                variant_data["product_id"] = product_data["id"]
                                
                                await upsert_product_variant(db_manager, variant_data)
                                processed_variants += 1
                        
                        if config.get("include_images", True):
                            images = product_data.get("images", {}).get("edges", [])
                            for image_edge in images:
                                image_data = image_edge["node"]
                                image_data["product_id"] = product_data["id"]
                                
                                await upsert_product_image(db_manager, image_data)
                                processed_images += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing product {product_data.get('id', 'unknown')}: {str(e)}")
                        error_count += 1
                
                # Update analytics for processed products
                product_ids = [p["id"] for p in products_data]
                await calculate_product_analytics(db_manager, product_ids)
                
                result = {
                    "processed_products": processed_products,
                    "processed_variants": processed_variants,
                    "processed_images": processed_images,
                    "changes_detected": changes_detected,
                    "error_count": error_count,
                    "processing_status": "SUCCESS"
                }
                
                return result
                
            finally:
                await db_manager.close()
        
        result = asyncio.run(process_updated_data())
        
        logger.info(f"Updated product data processing completed: {result}")
        return result
    
    # Task dependencies
    extract_task = extract_updated_products()
    process_task = process_updated_product_data()
    
    extract_task >> process_task
    
    return process_task

# Product Image Sync Task Group
@task_group(group_id="image_sync_group", dag=dag)
def image_sync_operations():
    """Task group for dedicated product image synchronization"""
    
    @task
    def extract_product_images(**context) -> Dict[str, Any]:
        """Extract detailed product image data"""
        logger.info("Starting product image extraction")
        
        config = context["task_instance"].xcom_pull(task_ids="get_catalog_sync_config")
        
        if not config.get("image_sync_enabled", True):
            logger.info("Image sync is disabled")
            return {"extraction_status": "SKIPPED"}
        
        async def get_products_for_image_sync():
            db_manager = DatabaseManager()
            try:
                await db_manager.connect()
                
                # Get products that need image updates
                products_result = await db_manager.execute_query("""
                    SELECT DISTINCT p.id 
                    FROM shopify_products p
                    LEFT JOIN shopify_product_images pi ON p.id = pi.product_id
                    WHERE pi.product_id IS NULL 
                    OR p.updated_at > pi.synced_at
                    LIMIT 100
                """, fetch=True)
                
                return [row["id"] for row in products_result]
                
            finally:
                await db_manager.close()
        
        try:
            product_ids = asyncio.run(get_products_for_image_sync())
            
            if not product_ids:
                logger.info("No products need image updates")
                return {"extraction_status": "NO_UPDATES_NEEDED", "products_processed": 0}
            
            graphql_client = ShopifyGraphQLClient()
            total_images = 0
            
            for product_id in product_ids:
                try:
                    # Get product images using dedicated query
                    result = graphql_client.get_product_images(product_id, limit=50)
                    
                    product_data = result.get("product", {})
                    if product_data:
                        images = product_data.get("images", {}).get("edges", [])
                        total_images += len(images)
                        
                        # Store image data for processing
                        context["task_instance"].xcom_push(
                            key=f"product_images_{product_id}",
                            value=images
                        )
                
                except Exception as e:
                    logger.error(f"Failed to extract images for product {product_id}: {str(e)}")
            
            extraction_result = {
                "products_processed": len(product_ids),
                "total_images": total_images,
                "extraction_status": "SUCCESS"
            }
            
            # Store product IDs for processing
            context["task_instance"].xcom_push(
                key="product_ids_for_images",
                value=product_ids
            )
            
            logger.info(f"Product image extraction completed: {extraction_result}")
            return extraction_result
            
        except Exception as e:
            logger.error(f"Product image extraction failed: {str(e)}")
            raise AirflowException(f"Product image extraction failed: {str(e)}")
    
    @task
    def process_product_images(**context) -> Dict[str, Any]:
        """Process and load product image data"""
        logger.info("Processing product image data")
        
        product_ids = context["task_instance"].xcom_pull(
            task_ids="image_sync_group.extract_product_images",
            key="product_ids_for_images"
        )
        
        if not product_ids:
            return {"processed_images": 0, "processing_status": "NO_DATA"}
        
        async def process_images():
            db_manager = DatabaseManager()
            try:
                await db_manager.connect()
                
                processed_images = 0
                error_count = 0
                
                for product_id in product_ids:
                    try:
                        images = context["task_instance"].xcom_pull(
                            task_ids="image_sync_group.extract_product_images",
                            key=f"product_images_{product_id}"
                        )
                        
                        if images:
                            for position, image_edge in enumerate(images):
                                image_data = image_edge["node"]
                                image_data["product_id"] = product_id
                                image_data["position"] = position + 1
                                
                                await upsert_product_image(db_manager, image_data)
                                processed_images += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing images for product {product_id}: {str(e)}")
                        error_count += 1
                
                result = {
                    "processed_images": processed_images,
                    "error_count": error_count,
                    "processing_status": "SUCCESS"
                }
                
                return result
                
            finally:
                await db_manager.close()
        
        result = asyncio.run(process_images())
        
        logger.info(f"Product image processing completed: {result}")
        return result
    
    # Task dependencies
    extract_task = extract_product_images()
    process_task = process_product_images()
    
    extract_task >> process_task
    
    return process_task

# Helper functions for data processing
async def upsert_product_variant(db_manager: DatabaseManager, variant_data: Dict[str, Any]) -> None:
    """Upsert product variant data into the database"""
    query = """
        INSERT INTO shopify_product_variants (
            id, product_id, title, price, compare_at_price, sku, inventory_quantity,
            weight, weight_unit, barcode, available_for_sale, created_at, updated_at,
            selected_options, inventory_item, raw_data, synced_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            price = EXCLUDED.price,
            compare_at_price = EXCLUDED.compare_at_price,
            sku = EXCLUDED.sku,
            inventory_quantity = EXCLUDED.inventory_quantity,
            weight = EXCLUDED.weight,
            weight_unit = EXCLUDED.weight_unit,
            barcode = EXCLUDED.barcode,
            available_for_sale = EXCLUDED.available_for_sale,
            updated_at = EXCLUDED.updated_at,
            selected_options = EXCLUDED.selected_options,
            inventory_item = EXCLUDED.inventory_item,
            raw_data = EXCLUDED.raw_data,
            synced_at = EXCLUDED.synced_at
    """
    
    params = (
        variant_data["id"],
        variant_data.get("product_id"),
        variant_data.get("title"),
        float(variant_data.get("price", 0)) if variant_data.get("price") else None,
        float(variant_data.get("compareAtPrice", 0)) if variant_data.get("compareAtPrice") else None,
        variant_data.get("sku"),
        variant_data.get("inventoryQuantity"),
        float(variant_data.get("weight", 0)) if variant_data.get("weight") else None,
        variant_data.get("weightUnit"),
        variant_data.get("barcode"),
        variant_data.get("availableForSale", False),
        datetime.fromisoformat(variant_data["createdAt"].replace("Z", "+00:00")) if variant_data.get("createdAt") else None,
        datetime.fromisoformat(variant_data["updatedAt"].replace("Z", "+00:00")) if variant_data.get("updatedAt") else None,
        json.dumps(variant_data.get("selectedOptions", [])),
        json.dumps(variant_data.get("inventoryItem", {})),
        json.dumps(variant_data),
        datetime.now()
    )
    
    await db_manager.execute_query(query, params)

async def upsert_product_image(db_manager: DatabaseManager, image_data: Dict[str, Any]) -> None:
    """Upsert product image data into the database"""
    query = """
        INSERT INTO shopify_product_images (
            id, product_id, url, alt_text, width, height, original_src, position, raw_data, synced_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (id) DO UPDATE SET
            url = EXCLUDED.url,
            alt_text = EXCLUDED.alt_text,
            width = EXCLUDED.width,
            height = EXCLUDED.height,
            original_src = EXCLUDED.original_src,
            position = EXCLUDED.position,
            raw_data = EXCLUDED.raw_data,
            synced_at = EXCLUDED.synced_at
    """
    
    params = (
        image_data["id"],
        image_data.get("product_id"),
        image_data.get("url"),
        image_data.get("altText"),
        image_data.get("width"),
        image_data.get("height"),
        image_data.get("originalSrc"),
        image_data.get("position", 1),
        json.dumps(image_data),
        datetime.now()
    )
    
    await db_manager.execute_query(query, params)

async def upsert_product_collection(
    db_manager: DatabaseManager, 
    product_id: str, 
    collection_data: Dict[str, Any]
) -> None:
    """Upsert product collection relationship"""
    query = """
        INSERT INTO shopify_product_collections (
            product_id, collection_id, collection_title, collection_handle, raw_data, synced_at
        ) VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (product_id, collection_id) DO UPDATE SET
            collection_title = EXCLUDED.collection_title,
            collection_handle = EXCLUDED.collection_handle,
            raw_data = EXCLUDED.raw_data,
            synced_at = EXCLUDED.synced_at
    """
    
    params = (
        product_id,
        collection_data["id"],
        collection_data.get("title"),
        collection_data.get("handle"),
        json.dumps(collection_data),
        datetime.now()
    )
    
    await db_manager.execute_query(query, params)

async def upsert_inventory_level(db_manager: DatabaseManager, level_data: Dict[str, Any]) -> None:
    """Upsert inventory level data"""
    query = """
        INSERT INTO shopify_inventory_levels (
            variant_id, location_id, location_name, available, raw_data, synced_at
        ) VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (variant_id, location_id) DO UPDATE SET
            location_name = EXCLUDED.location_name,
            available = EXCLUDED.available,
            raw_data = EXCLUDED.raw_data,
            synced_at = EXCLUDED.synced_at
    """
    
    location = level_data.get("location", {})
    
    params = (
        level_data.get("variant_id"),
        location.get("id"),
        location.get("name"),
        level_data.get("available"),
        json.dumps(level_data),
        datetime.now()
    )
    
    await db_manager.execute_query(query, params)

async def detect_product_changes(db_manager: DatabaseManager, product_data: Dict[str, Any]) -> bool:
    """Detect changes in product data"""
    try:
        # Get existing product data
        existing_result = await db_manager.execute_query(
            "SELECT raw_data FROM shopify_products WHERE id = $1",
            [product_data["id"]],
            fetch=True
        )
        
        if not existing_result:
            # New product
            await log_product_change(db_manager, product_data["id"], "created", None, product_data)
            return True
        
        existing_data = existing_result[0]["raw_data"]
        
        # Compare data hashes
        existing_hash = hashlib.md5(json.dumps(existing_data, sort_keys=True).encode()).hexdigest()
        new_hash = hashlib.md5(json.dumps(product_data, sort_keys=True).encode()).hexdigest()
        
        if existing_hash != new_hash:
            await log_product_change(db_manager, product_data["id"], "updated", existing_data, product_data)
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error detecting changes for product {product_data.get('id')}: {str(e)}")
        return False

async def log_product_change(
    db_manager: DatabaseManager, 
    product_id: str, 
    change_type: str, 
    old_data: Optional[Dict[str, Any]], 
    new_data: Dict[str, Any]
) -> None:
    """Log product changes"""
    change_hash = hashlib.md5(f"{product_id}_{change_type}_{datetime.now().isoformat()}".encode()).hexdigest()
    
    query = """
        INSERT INTO shopify_product_changes (
            product_id, change_type, field_name, old_value, new_value, change_hash, synced_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
    """
    
    params = (
        product_id,
        change_type,
        "full_product",
        json.dumps(old_data) if old_data else None,
        json.dumps(new_data),
        change_hash,
        datetime.now()
    )
    
    await db_manager.execute_query(query, params)

async def calculate_product_analytics(
    db_manager: DatabaseManager, 
    product_ids: Optional[List[str]] = None
) -> None:
    """Calculate and update product analytics"""
    if product_ids:
        # Update analytics for specific products
        product_filter = f"WHERE p.id = ANY($1)"
        params = [product_ids]
    else:
        # Update analytics for all products
        product_filter = ""
        params = []
    
    query = f"""
        INSERT INTO shopify_product_analytics (
            product_id, total_variants, total_images, total_inventory, available_variants,
            price_range_min, price_range_max, last_updated, days_since_update,
            has_metafields, has_seo, collection_count, data_completeness_score,
            calculated_at, synced_at
        )
        SELECT 
            p.id,
            COUNT(DISTINCT pv.id) as total_variants,
            COUNT(DISTINCT pi.id) as total_images,
            p.total_inventory,
            COUNT(DISTINCT CASE WHEN pv.available_for_sale = true THEN pv.id END) as available_variants,
            MIN(pv.price) as price_range_min,
            MAX(pv.price) as price_range_max,
            p.updated_at as last_updated,
            EXTRACT(DAYS FROM NOW() - p.updated_at) as days_since_update,
            CASE WHEN p.metafields::text != '{{}}' THEN true ELSE false END as has_metafields,
            CASE WHEN p.seo_title IS NOT NULL OR p.seo_description IS NOT NULL THEN true ELSE false END as has_seo,
            COUNT(DISTINCT pc.collection_id) as collection_count,
            CASE 
                WHEN p.title IS NOT NULL AND p.description_html IS NOT NULL 
                     AND COUNT(DISTINCT pv.id) > 0 AND COUNT(DISTINCT pi.id) > 0 
                THEN 1.0
                WHEN p.title IS NOT NULL AND COUNT(DISTINCT pv.id) > 0 
                THEN 0.7
                WHEN p.title IS NOT NULL 
                THEN 0.5
                ELSE 0.2
            END as data_completeness_score,
            NOW() as calculated_at,
            NOW() as synced_at
        FROM shopify_products p
        LEFT JOIN shopify_product_variants pv ON p.id = pv.product_id
        LEFT JOIN shopify_product_images pi ON p.id = pi.product_id
        LEFT JOIN shopify_product_collections pc ON p.id = pc.product_id
        {product_filter}
        GROUP BY p.id, p.total_inventory, p.updated_at, p.metafields, p.seo_title, p.seo_description, p.title, p.description_html
        ON CONFLICT (product_id) DO UPDATE SET
            total_variants = EXCLUDED.total_variants,
            total_images = EXCLUDED.total_images,
            total_inventory = EXCLUDED.total_inventory,
            available_variants = EXCLUDED.available_variants,
            price_range_min = EXCLUDED.price_range_min,
            price_range_max = EXCLUDED.price_range_max,
            last_updated = EXCLUDED.last_updated,
            days_since_update = EXCLUDED.days_since_update,
            has_metafields = EXCLUDED.has_metafields,
            has_seo = EXCLUDED.has_seo,
            collection_count = EXCLUDED.collection_count,
            data_completeness_score = EXCLUDED.data_completeness_score,
            calculated_at = EXCLUDED.calculated_at,
            synced_at = EXCLUDED.synced_at
    """
    
    await db_manager.execute_query(query, params)

async def get_variants_count(db_manager: DatabaseManager) -> int:
    """Get total number of product variants"""
    result = await db_manager.execute_query("SELECT COUNT(*) as count FROM shopify_product_variants", fetch=True)
    return result[0]["count"] if result else 0

async def get_images_count(db_manager: DatabaseManager) -> int:
    """Get total number of product images"""
    result = await db_manager.execute_query("SELECT COUNT(*) as count FROM shopify_product_images", fetch=True)
    return result[0]["count"] if result else 0

# Data Validation Task
@task(dag=dag)
def validate_catalog_data(**context) -> Dict[str, Any]:
    """
    Validate product catalog data quality
    
    Returns:
        Dictionary with validation results
    """
    logger.info("Starting catalog data validation")
    
    async def validate_data():
        db_manager = DatabaseManager()
        try:
            await db_manager.connect()
            
            validation_results = {
                "total_products": 0,
                "total_variants": 0,
                "total_images": 0,
                "validation_checks": [],
                "passed_checks": 0,
                "failed_checks": 0,
                "overall_status": "PASSED"
            }
            
            # Get counts
            validation_results["total_products"] = await db_manager.get_products_count()
            validation_results["total_variants"] = await get_variants_count(db_manager)
            validation_results["total_images"] = await get_images_count(db_manager)
            
            # Validation checks
            checks = [
                {
                    "name": "products_with_variants",
                    "query": "SELECT COUNT(*) FROM shopify_products WHERE id IN (SELECT DISTINCT product_id FROM shopify_product_variants)",
                    "description": "Products with at least one variant"
                },
                {
                    "name": "products_with_images",
                    "query": "SELECT COUNT(*) FROM shopify_products WHERE id IN (SELECT DISTINCT product_id FROM shopify_product_images)",
                    "description": "Products with images"
                },
                {
                    "name": "products_with_title",
                    "query": "SELECT COUNT(*) FROM shopify_products WHERE title IS NOT NULL AND title != ''",
                    "description": "Products with titles"
                },
                {
                    "name": "products_with_status",
                    "query": "SELECT COUNT(*) FROM shopify_products WHERE status IS NOT NULL",
                    "description": "Products with status"
                },
                {
                    "name": "variants_with_price",
                    "query": "SELECT COUNT(*) FROM shopify_product_variants WHERE price > 0",
                    "description": "Variants with positive price"
                },
                {
                    "name": "recent_sync_products",
                    "query": "SELECT COUNT(*) FROM shopify_products WHERE synced_at >= NOW() - INTERVAL '24 hours'",
                    "description": "Recently synced products"
                },
                {
                    "name": "data_completeness_high",
                    "query": "SELECT COUNT(*) FROM shopify_product_analytics WHERE data_completeness_score >= 0.8",
                    "description": "Products with high data completeness"
                }
            ]
            
            for check in checks:
                try:
                    result = await db_manager.execute_query(check["query"], fetch=True)
                    count = result[0]["count"] if result else 0
                    
                    check_result = {
                        "name": check["name"],
                        "description": check["description"],
                        "count": count,
                        "status": "PASSED" if count > 0 else "FAILED"
                    }
                    
                    validation_results["validation_checks"].append(check_result)
                    
                    if check_result["status"] == "PASSED":
                        validation_results["passed_checks"] += 1
                    else:
                        validation_results["failed_checks"] += 1
                        validation_results["overall_status"] = "FAILED"
                        
                except Exception as e:
                    check_result = {
                        "name": check["name"],
                        "description": check["description"],
                        "error": str(e),
                        "status": "FAILED"
                    }
                    validation_results["validation_checks"].append(check_result)
                    validation_results["failed_checks"] += 1
                    validation_results["overall_status"] = "FAILED"
            
            return validation_results
            
        finally:
            await db_manager.close()
    
    result = asyncio.run(validate_data())
    
    logger.info(f"Catalog data validation completed: {result}")
    return result

# Reporting Task
@task(dag=dag)
def generate_catalog_report(**context) -> Dict[str, Any]:
    """
    Generate comprehensive catalog sync report
    
    Returns:
        Dictionary with catalog sync report data
    """
    logger.info("Generating catalog sync report")
    
    async def generate_report():
        db_manager = DatabaseManager()
        try:
            await db_manager.connect()
            
            # Get basic statistics
            products_count = await db_manager.get_products_count()
            variants_count = await get_variants_count(db_manager)
            images_count = await get_images_count(db_manager)
            
            # Get product analytics summary
            analytics_result = await db_manager.execute_query("""
                SELECT 
                    COUNT(*) as products_with_analytics,
                    AVG(total_variants) as avg_variants_per_product,
                    AVG(total_images) as avg_images_per_product,
                    AVG(data_completeness_score) as avg_completeness_score,
                    COUNT(CASE WHEN data_completeness_score >= 0.8 THEN 1 END) as high_quality_products
                FROM shopify_product_analytics
            """, fetch=True)
            
            analytics_summary = analytics_result[0] if analytics_result else {}
            
            # Get product status distribution
            status_result = await db_manager.execute_query("""
                SELECT status, COUNT(*) as count
                FROM shopify_products
                GROUP BY status
            """, fetch=True)
            
            status_distribution = {row["status"]: row["count"] for row in status_result}
            
            # Get top product types
            product_types_result = await db_manager.execute_query("""
                SELECT product_type, COUNT(*) as count
                FROM shopify_products
                WHERE product_type IS NOT NULL
                GROUP BY product_type
                ORDER BY count DESC
                LIMIT 10
            """, fetch=True)
            
            top_product_types = [
                {"type": row["product_type"], "count": row["count"]} 
                for row in product_types_result
            ]
            
            # Get inventory summary
            inventory_result = await db_manager.execute_query("""
                SELECT 
                    SUM(total_inventory) as total_inventory,
                    COUNT(CASE WHEN total_inventory > 0 THEN 1 END) as products_in_stock,
                    COUNT(CASE WHEN total_inventory = 0 THEN 1 END) as products_out_of_stock
                FROM shopify_products
            """, fetch=True)
            
            inventory_summary = inventory_result[0] if inventory_result else {}
            
            report = {
                "sync_timestamp": datetime.now().isoformat(),
                "basic_stats": {
                    "total_products": products_count,
                    "total_variants": variants_count,
                    "total_images": images_count
                },
                "analytics_summary": {
                    "products_with_analytics": analytics_summary.get("products_with_analytics", 0),
                    "avg_variants_per_product": float(analytics_summary.get("avg_variants_per_product", 0) or 0),
                    "avg_images_per_product": float(analytics_summary.get("avg_images_per_product", 0) or 0),
                    "avg_completeness_score": float(analytics_summary.get("avg_completeness_score", 0) or 0),
                    "high_quality_products": analytics_summary.get("high_quality_products", 0)
                },
                "status_distribution": status_distribution,
                "top_product_types": top_product_types,
                "inventory_summary": {
                    "total_inventory": inventory_summary.get("total_inventory", 0),
                    "products_in_stock": inventory_summary.get("products_in_stock", 0),
                    "products_out_of_stock": inventory_summary.get("products_out_of_stock", 0)
                },
                "report_status": "SUCCESS"
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate catalog report: {str(e)}")
            return {"report_status": "FAILED", "error": str(e)}
        finally:
            await db_manager.close()
    
    report = asyncio.run(generate_report())
    
    logger.info(f"Catalog sync report generated: {report}")
    return report

# Pipeline End
catalog_pipeline_end = DummyOperator(
    task_id="catalog_pipeline_end",
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    dag=dag,
)

# Set up task dependencies
config = get_catalog_sync_config()
validation = validate_catalog_connections()
database_prep = prepare_catalog_database()

# Main pipeline flow
config >> validation >> database_prep >> catalog_sync_decision

# Full sync path
full_catalog_sync = full_catalog_sync_operations()
catalog_sync_decision >> full_catalog_sync

# Incremental sync path
incremental_catalog_sync = incremental_catalog_sync_operations()
catalog_sync_decision >> incremental_catalog_sync

# Image sync (runs in parallel with main sync)
image_sync = image_sync_operations()
[full_catalog_sync, incremental_catalog_sync] >> image_sync

# Validation and reporting
catalog_validation = validate_catalog_data()
catalog_report = generate_catalog_report()

# Connect all operations to validation and reporting
[full_catalog_sync, incremental_catalog_sync, image_sync] >> catalog_validation >> catalog_report >> catalog_pipeline_end

if __name__ == "__main__":
    dag.test()