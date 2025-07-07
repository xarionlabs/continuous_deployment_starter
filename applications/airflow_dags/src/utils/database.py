"""
Database connectivity utilities for Airflow DAGs

This module provides database connection and management utilities for accessing
the pxy6 database using the pxy6_airflow user credentials.

The database connection is configured to work with the PostgreSQL instance
running in the continuous deployment environment.

Example usage:
    async with get_database_connection() as conn:
        result = await conn.fetchall("SELECT * FROM customers")
        
    # Or using the context manager
    db_manager = DatabaseManager()
    await db_manager.connect()
    try:
        customers = await db_manager.fetch_customers()
    finally:
        await db_manager.close()
"""

import logging
import os
from typing import Dict, List, Any, Optional, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
import json

import asyncpg
import asyncio
from asyncpg import Connection, Pool


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration parameters"""
    host: str = "db"  # Docker service name
    port: int = 5432
    database: str = "pxy6"
    user: str = "pxy6_airflow"
    password: str = ""
    min_connections: int = 1
    max_connections: int = 10
    command_timeout: int = 60
    
    @classmethod
    def from_environment(cls) -> "DatabaseConfig":
        """Create configuration from environment variables"""
        return cls(
            host=os.getenv("PXY6_POSTGRES_HOST", os.getenv("POSTGRES_HOST", "db")),
            port=int(os.getenv("PXY6_POSTGRES_PORT", os.getenv("POSTGRES_PORT", "5432"))),
            database=os.getenv("PXY6_POSTGRES_DB", os.getenv("POSTGRES_DATABASE", "pxy6")),
            user=os.getenv("PXY6_POSTGRES_USER", "pxy6_airflow"),
            password=os.getenv("PXY6_POSTGRES_PASSWORD", os.getenv("POSTGRES_PASSWORD", "")),
            min_connections=int(os.getenv("DB_MIN_CONNECTIONS", "1")),
            max_connections=int(os.getenv("DB_MAX_CONNECTIONS", "10")),
            command_timeout=int(os.getenv("DB_COMMAND_TIMEOUT", "60"))
        )


class DatabaseManager:
    """
    Database connection manager for Airflow DAGs
    
    Provides connection pooling, transaction management, and common database operations
    for the Shopify data integration workflows.
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize the database manager
        
        Args:
            config: Database configuration. If None, will load from environment
        """
        self.config = config or DatabaseConfig.from_environment()
        self.pool: Optional[Pool] = None
        self._connection: Optional[Connection] = None
        
        logger.info(f"Database manager initialized for {self.config.database}@{self.config.host}")
    
    async def connect(self) -> None:
        """Establish database connection pool"""
        if self.pool is None:
            try:
                self.pool = await asyncpg.create_pool(
                    host=self.config.host,
                    port=self.config.port,
                    database=self.config.database,
                    user=self.config.user,
                    password=self.config.password,
                    min_size=self.config.min_connections,
                    max_size=self.config.max_connections,
                    command_timeout=self.config.command_timeout
                )
                logger.info("Database connection pool established")
            except Exception as e:
                logger.error(f"Failed to create database pool: {e}")
                raise
    
    async def close(self) -> None:
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool"""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute_query(
        self, 
        query: str, 
        params: Optional[Union[tuple, list]] = None,
        fetch: bool = False
    ) -> Union[List[Dict[str, Any]], str, None]:
        """
        Execute a database query
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch results
            
        Returns:
            Query results if fetch=True, otherwise None
        """
        async with self.get_connection() as conn:
            try:
                if fetch:
                    if params:
                        result = await conn.fetch(query, *params)
                    else:
                        result = await conn.fetch(query)
                    return [dict(row) for row in result]
                else:
                    if params:
                        result = await conn.execute(query, *params)
                    else:
                        result = await conn.execute(query)
                    return result
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                logger.error(f"Query: {query}")
                logger.error(f"Params: {params}")
                raise
    
    async def test_connection(self) -> bool:
        """
        Test the database connection
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            result = await self.execute_query("SELECT 1 as test", fetch=True)
            success = result and result[0]["test"] == 1
            if success:
                logger.info("Database connection test successful")
            else:
                logger.error("Database connection test failed: unexpected result")
            return success
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    # Shopify-specific database operations
    
    async def create_tables(self) -> None:
        """Create necessary tables for Shopify data"""
        
        # Products table
        await self.execute_query("""
            CREATE TABLE IF NOT EXISTS shopify_products (
                id VARCHAR(255) PRIMARY KEY,
                title VARCHAR(1000),
                handle VARCHAR(500),
                description_html TEXT,
                product_type VARCHAR(255),
                vendor VARCHAR(255),
                tags TEXT[],
                status VARCHAR(50),
                created_at TIMESTAMP WITH TIME ZONE,
                updated_at TIMESTAMP WITH TIME ZONE,
                published_at TIMESTAMP WITH TIME ZONE,
                total_inventory INTEGER,
                online_store_url TEXT,
                seo_title VARCHAR(1000),
                seo_description TEXT,
                options JSONB,
                metafields JSONB,
                raw_data JSONB,
                synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Product variants table
        await self.execute_query("""
            CREATE TABLE IF NOT EXISTS shopify_product_variants (
                id VARCHAR(255) PRIMARY KEY,
                product_id VARCHAR(255) REFERENCES shopify_products(id),
                title VARCHAR(1000),
                price DECIMAL(10, 2),
                compare_at_price DECIMAL(10, 2),
                sku VARCHAR(255),
                inventory_quantity INTEGER,
                weight DECIMAL(10, 3),
                weight_unit VARCHAR(10),
                barcode VARCHAR(255),
                available_for_sale BOOLEAN,
                created_at TIMESTAMP WITH TIME ZONE,
                updated_at TIMESTAMP WITH TIME ZONE,
                selected_options JSONB,
                inventory_item JSONB,
                raw_data JSONB,
                synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Product images table
        await self.execute_query("""
            CREATE TABLE IF NOT EXISTS shopify_product_images (
                id VARCHAR(255) PRIMARY KEY,
                product_id VARCHAR(255) REFERENCES shopify_products(id),
                url TEXT,
                alt_text VARCHAR(1000),
                width INTEGER,
                height INTEGER,
                original_src TEXT,
                position INTEGER,
                raw_data JSONB,
                synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Customers table
        await self.execute_query("""
            CREATE TABLE IF NOT EXISTS shopify_customers (
                id VARCHAR(255) PRIMARY KEY,
                email VARCHAR(500),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                phone VARCHAR(50),
                created_at TIMESTAMP WITH TIME ZONE,
                updated_at TIMESTAMP WITH TIME ZONE,
                accepts_marketing BOOLEAN,
                accepts_marketing_updated_at TIMESTAMP WITH TIME ZONE,
                state VARCHAR(50),
                tags TEXT[],
                note TEXT,
                verified_email BOOLEAN,
                tax_exempt BOOLEAN,
                total_spent_amount DECIMAL(10, 2),
                total_spent_currency_code VARCHAR(10),
                number_of_orders INTEGER,
                addresses JSONB,
                metafields JSONB,
                raw_data JSONB,
                synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Orders table
        await self.execute_query("""
            CREATE TABLE IF NOT EXISTS shopify_orders (
                id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255),
                email VARCHAR(500),
                customer_id VARCHAR(255) REFERENCES shopify_customers(id),
                created_at TIMESTAMP WITH TIME ZONE,
                updated_at TIMESTAMP WITH TIME ZONE,
                processed_at TIMESTAMP WITH TIME ZONE,
                closed_at TIMESTAMP WITH TIME ZONE,
                cancelled BOOLEAN,
                cancelled_at TIMESTAMP WITH TIME ZONE,
                cancel_reason VARCHAR(255),
                total_price_amount DECIMAL(10, 2),
                total_price_currency_code VARCHAR(10),
                subtotal_price_amount DECIMAL(10, 2),
                subtotal_price_currency_code VARCHAR(10),
                total_tax_amount DECIMAL(10, 2),
                total_tax_currency_code VARCHAR(10),
                total_shipping_price_amount DECIMAL(10, 2),
                total_shipping_price_currency_code VARCHAR(10),
                financial_status VARCHAR(50),
                fulfillment_status VARCHAR(50),
                tags TEXT[],
                note TEXT,
                customer_journey_summary JSONB,
                raw_data JSONB,
                synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Order line items table
        await self.execute_query("""
            CREATE TABLE IF NOT EXISTS shopify_order_line_items (
                id VARCHAR(255) PRIMARY KEY,
                order_id VARCHAR(255) REFERENCES shopify_orders(id),
                name VARCHAR(1000),
                quantity INTEGER,
                original_total_amount DECIMAL(10, 2),
                original_total_currency_code VARCHAR(10),
                variant_id VARCHAR(255) REFERENCES shopify_product_variants(id),
                variant_title VARCHAR(1000),
                variant_price DECIMAL(10, 2),
                variant_sku VARCHAR(255),
                product_id VARCHAR(255) REFERENCES shopify_products(id),
                product_title VARCHAR(1000),
                product_handle VARCHAR(500),
                product_type VARCHAR(255),
                product_vendor VARCHAR(255),
                raw_data JSONB,
                synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create indexes for better performance
        await self.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_shopify_products_updated_at 
            ON shopify_products(updated_at);
        """)
        
        await self.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_shopify_customers_email 
            ON shopify_customers(email);
        """)
        
        await self.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_shopify_orders_created_at 
            ON shopify_orders(created_at);
        """)
        
        await self.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_shopify_orders_customer_id 
            ON shopify_orders(customer_id);
        """)
        
        logger.info("Shopify database tables created successfully")
    
    async def upsert_product(self, product_data: Dict[str, Any]) -> None:
        """
        Upsert a product into the database
        
        Args:
            product_data: Product data from Shopify GraphQL API
        """
        query = """
            INSERT INTO shopify_products (
                id, title, handle, description_html, product_type, vendor, tags,
                status, created_at, updated_at, published_at, total_inventory,
                online_store_url, seo_title, seo_description, options, metafields,
                raw_data, synced_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                handle = EXCLUDED.handle,
                description_html = EXCLUDED.description_html,
                product_type = EXCLUDED.product_type,
                vendor = EXCLUDED.vendor,
                tags = EXCLUDED.tags,
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at,
                published_at = EXCLUDED.published_at,
                total_inventory = EXCLUDED.total_inventory,
                online_store_url = EXCLUDED.online_store_url,
                seo_title = EXCLUDED.seo_title,
                seo_description = EXCLUDED.seo_description,
                options = EXCLUDED.options,
                metafields = EXCLUDED.metafields,
                raw_data = EXCLUDED.raw_data,
                synced_at = EXCLUDED.synced_at
        """
        
        # Extract SEO data
        seo = product_data.get("seo", {})
        seo_title = seo.get("title") if seo else None
        seo_description = seo.get("description") if seo else None
        
        # Process metafields
        metafields = {}
        if "metafields" in product_data and product_data["metafields"]["edges"]:
            for edge in product_data["metafields"]["edges"]:
                field = edge["node"]
                metafields[f"{field['namespace']}.{field['key']}"] = {
                    "value": field["value"],
                    "type": field["type"],
                    "description": field.get("description")
                }
        
        params = (
            product_data["id"],
            product_data.get("title"),
            product_data.get("handle"),
            product_data.get("descriptionHtml"),
            product_data.get("productType"),
            product_data.get("vendor"),
            product_data.get("tags", []),
            product_data.get("status"),
            datetime.fromisoformat(product_data["createdAt"].replace("Z", "+00:00")) if product_data.get("createdAt") else None,
            datetime.fromisoformat(product_data["updatedAt"].replace("Z", "+00:00")) if product_data.get("updatedAt") else None,
            datetime.fromisoformat(product_data["publishedAt"].replace("Z", "+00:00")) if product_data.get("publishedAt") else None,
            product_data.get("totalInventory"),
            product_data.get("onlineStoreUrl"),
            seo_title,
            seo_description,
            json.dumps(product_data.get("options", [])),
            json.dumps(metafields),
            json.dumps(product_data),
            datetime.now()
        )
        
        await self.execute_query(query, params)
    
    async def upsert_customer(self, customer_data: Dict[str, Any]) -> None:
        """
        Upsert a customer into the database
        
        Args:
            customer_data: Customer data from Shopify GraphQL API
        """
        query = """
            INSERT INTO shopify_customers (
                id, email, first_name, last_name, phone, created_at, updated_at,
                accepts_marketing, accepts_marketing_updated_at, state, tags, note,
                verified_email, tax_exempt, total_spent_amount, total_spent_currency_code,
                number_of_orders, addresses, metafields, raw_data, synced_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                phone = EXCLUDED.phone,
                updated_at = EXCLUDED.updated_at,
                accepts_marketing = EXCLUDED.accepts_marketing,
                accepts_marketing_updated_at = EXCLUDED.accepts_marketing_updated_at,
                state = EXCLUDED.state,
                tags = EXCLUDED.tags,
                note = EXCLUDED.note,
                verified_email = EXCLUDED.verified_email,
                tax_exempt = EXCLUDED.tax_exempt,
                total_spent_amount = EXCLUDED.total_spent_amount,
                total_spent_currency_code = EXCLUDED.total_spent_currency_code,
                number_of_orders = EXCLUDED.number_of_orders,
                addresses = EXCLUDED.addresses,
                metafields = EXCLUDED.metafields,
                raw_data = EXCLUDED.raw_data,
                synced_at = EXCLUDED.synced_at
        """
        
        # Process total spent
        total_spent = customer_data.get("totalSpentV2", {})
        total_spent_amount = float(total_spent.get("amount", 0)) if total_spent.get("amount") else None
        total_spent_currency = total_spent.get("currencyCode")
        
        # Process metafields
        metafields = {}
        if "metafields" in customer_data and customer_data["metafields"]["edges"]:
            for edge in customer_data["metafields"]["edges"]:
                field = edge["node"]
                metafields[f"{field['namespace']}.{field['key']}"] = {
                    "value": field["value"],
                    "type": field["type"],
                    "description": field.get("description")
                }
        
        params = (
            customer_data["id"],
            customer_data.get("email"),
            customer_data.get("firstName"),
            customer_data.get("lastName"),
            customer_data.get("phone"),
            datetime.fromisoformat(customer_data["createdAt"].replace("Z", "+00:00")) if customer_data.get("createdAt") else None,
            datetime.fromisoformat(customer_data["updatedAt"].replace("Z", "+00:00")) if customer_data.get("updatedAt") else None,
            customer_data.get("acceptsMarketing"),
            datetime.fromisoformat(customer_data["acceptsMarketingUpdatedAt"].replace("Z", "+00:00")) if customer_data.get("acceptsMarketingUpdatedAt") else None,
            customer_data.get("state"),
            customer_data.get("tags", []),
            customer_data.get("note"),
            customer_data.get("verifiedEmail"),
            customer_data.get("taxExempt"),
            total_spent_amount,
            total_spent_currency,
            customer_data.get("numberOfOrders"),
            json.dumps(customer_data.get("addresses", [])),
            json.dumps(metafields),
            json.dumps(customer_data),
            datetime.now()
        )
        
        await self.execute_query(query, params)
    
    async def get_last_sync_time(self, table_name: str) -> Optional[datetime]:
        """
        Get the last sync time for a specific table
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            Last sync timestamp or None if no records exist
        """
        query = f"SELECT MAX(synced_at) as last_sync FROM {table_name}"
        result = await self.execute_query(query, fetch=True)
        
        if result and result[0]["last_sync"]:
            return result[0]["last_sync"]
        return None
    
    async def get_products_count(self) -> int:
        """Get the total number of products in the database"""
        result = await self.execute_query("SELECT COUNT(*) as count FROM shopify_products", fetch=True)
        return result[0]["count"] if result else 0
    
    async def get_customers_count(self) -> int:
        """Get the total number of customers in the database"""
        result = await self.execute_query("SELECT COUNT(*) as count FROM shopify_customers", fetch=True)
        return result[0]["count"] if result else 0
    
    async def get_orders_count(self) -> int:
        """Get the total number of orders in the database"""
        result = await self.execute_query("SELECT COUNT(*) as count FROM shopify_orders", fetch=True)
        return result[0]["count"] if result else 0
    
    async def get_table_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive table statistics for monitoring
        
        Returns:
            Dictionary with table statistics
        """
        stats = {
            "table_counts": {},
            "table_sizes": {},
            "index_usage": {},
            "last_analyzed": {},
            "data_freshness": {}
        }
        
        try:
            # Get table counts
            tables = ["shopify_products", "shopify_customers", "shopify_orders", 
                     "shopify_product_variants", "shopify_product_images", "shopify_order_line_items"]
            
            for table in tables:
                try:
                    result = await self.execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch=True)
                    stats["table_counts"][table] = result[0]["count"] if result else 0
                except Exception as e:
                    logger.warning(f"Could not get count for table {table}: {str(e)}")
                    stats["table_counts"][table] = 0
            
            # Get table sizes
            size_result = await self.execute_query("""
                SELECT 
                    tablename,
                    pg_size_pretty(pg_total_relation_size(tablename::regclass)) as size_pretty,
                    pg_total_relation_size(tablename::regclass) as size_bytes
                FROM pg_tables 
                WHERE tablename LIKE 'shopify_%'
                ORDER BY pg_total_relation_size(tablename::regclass) DESC
            """, fetch=True)
            
            if size_result:
                for row in size_result:
                    stats["table_sizes"][row["tablename"]] = {
                        "size_pretty": row["size_pretty"],
                        "size_bytes": row["size_bytes"]
                    }
            
            # Get data freshness (latest synced_at times)
            for table in tables:
                try:
                    freshness_result = await self.execute_query(f"""
                        SELECT 
                            MAX(synced_at) as latest_sync,
                            COUNT(CASE WHEN synced_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as recent_records
                        FROM {table}
                    """, fetch=True)
                    
                    if freshness_result:
                        stats["data_freshness"][table] = {
                            "latest_sync": freshness_result[0]["latest_sync"],
                            "recent_records": freshness_result[0]["recent_records"]
                        }
                except Exception as e:
                    logger.warning(f"Could not get freshness for table {table}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error getting table statistics: {str(e)}")
        
        return stats


@asynccontextmanager
async def get_database_connection():
    """
    Context manager for getting a database connection
    
    Usage:
        async with get_database_connection() as conn:
            result = await conn.fetchall("SELECT * FROM customers")
    """
    db_manager = DatabaseManager()
    await db_manager.connect()
    try:
        async with db_manager.get_connection() as conn:
            yield conn
    finally:
        await db_manager.close()


@asynccontextmanager
async def get_pxy6_database_connection():
    """
    Context manager for getting a pxy6 database connection using pxy6_airflow user
    
    Usage:
        async with get_pxy6_database_connection() as conn:
            result = await conn.fetchall("SELECT * FROM shopify_customers")
    """
    config = DatabaseConfig.from_environment()
    db_manager = DatabaseManager(config)
    await db_manager.connect()
    try:
        async with db_manager.get_connection() as conn:
            yield conn
    finally:
        await db_manager.close()


def get_pxy6_database_manager() -> DatabaseManager:
    """
    Get a DatabaseManager instance configured for the pxy6 database
    
    Returns:
        DatabaseManager configured for pxy6 database with pxy6_airflow user
    """
    config = DatabaseConfig.from_environment()
    return DatabaseManager(config)


def get_pxy6_session():
    """
    Get a PXY6 database session for use in DAG tasks.
    
    This is a simple wrapper around DatabaseManager for DAG compatibility.
    Returns a DatabaseManager instance that can be used with context manager.
    
    Usage:
        with get_pxy6_session() as session:
            # Use session for database operations
            pass
    """
    return DatabaseManager()


# Example usage
"""
# Basic usage with context manager
async def main():
    async with DatabaseManager() as db:
        # Test connection
        if await db.test_connection():
            print("Database connected successfully")
            
            # Create tables
            await db.create_tables()
            
            # Get statistics
            products_count = await db.get_products_count()
            customers_count = await db.get_customers_count()
            orders_count = await db.get_orders_count()
            
            print(f"Products: {products_count}")
            print(f"Customers: {customers_count}")
            print(f"Orders: {orders_count}")

# Run the example
if __name__ == "__main__":
    asyncio.run(main())
"""