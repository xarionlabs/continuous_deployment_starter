"""
Database connectivity utilities for Airflow DAGs

This module provides database connection and management utilities for accessing
the pxy6 database using SQLAlchemy for connection pooling and management.

Example usage:
    db_manager = DatabaseManager()
    result = db_manager.execute_query("SELECT * FROM customers")
    
    # Or using the context manager
    with db_manager.get_session() as session:
        customers = session.execute(text("SELECT * FROM customers")).fetchall()
"""

import logging
from typing import Dict, List, Any, Optional, Union
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import json

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .config import get_config

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

    @property
    def connection_url(self) -> str:
        """Generate SQLAlchemy connection URL"""
        return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class DatabaseManager:
    """
    Database manager using SQLAlchemy for connection pooling and management.
    
    This class provides a simple interface for database operations with
    automatic connection pooling and session management.
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize database manager with configuration
        
        Args:
            config: Database configuration. If None, loads from environment.
        """
        if config is None:
            # Load from environment using pydantic config
            app_config = get_config()
            config = DatabaseConfig(
                host=app_config.pxy6_postgres_host,
                port=app_config.pxy6_postgres_port,
                database=app_config.pxy6_postgres_db,
                user=app_config.pxy6_postgres_user,
                password=app_config.pxy6_postgres_password
            )
        
        self.config = config
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        
        logger.info(f"Database manager initialized for {config.user}@{config.host}")
    
    def connect(self):
        """Establish database connection pool"""
        try:
            self.engine = create_engine(
                self.config.connection_url,
                poolclass=QueuePool,
                pool_size=self.config.min_connections,
                max_overflow=self.config.max_connections - self.config.min_connections,
                pool_timeout=30,
                pool_recycle=3600,  # Recycle connections after 1 hour
                echo=False  # Set to True for SQL debugging
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Test the connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("Database connection pool established")
            
        except Exception as e:
            logger.error(f"Failed to create database connection pool: {e}")
            raise
    
    def close(self):
        """Close database connection pool"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection pool closed")
    
    @contextmanager
    def get_session(self) -> Session:
        """
        Get a database session with automatic cleanup
        
        Returns:
            SQLAlchemy session
        """
        if not self.SessionLocal:
            self.connect()
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None, fetch: bool = False) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a SQL query
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch results
            
        Returns:
            Query results if fetch=True, None otherwise
        """
        with self.get_session() as session:
            result = session.execute(text(query), params or {})
            
            if fetch:
                # Convert results to list of dictionaries
                rows = result.fetchall()
                # SQLAlchemy 1.4 compatibility
                if hasattr(rows[0], '_mapping') if rows else False:
                    return [dict(row._mapping) for row in rows]
                else:
                    return [dict(row) for row in rows]
            
            return None
    
    def create_tables(self):
        """Create database tables for Shopify data"""
        
        customers_table = """
        CREATE TABLE IF NOT EXISTS customers (
            id BIGINT PRIMARY KEY,
            email VARCHAR(255),
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            phone VARCHAR(50),
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            accepts_marketing BOOLEAN,
            state VARCHAR(50),
            tags TEXT,
            total_spent_amount DECIMAL(10,2),
            total_spent_currency VARCHAR(3),
            number_of_orders INTEGER,
            verified_email BOOLEAN,
            tax_exempt BOOLEAN,
            addresses JSONB,
            metafields JSONB,
            shopify_created_at TIMESTAMP,
            shopify_updated_at TIMESTAMP,
            last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        products_table = """
        CREATE TABLE IF NOT EXISTS products (
            id BIGINT PRIMARY KEY,
            title VARCHAR(500),
            handle VARCHAR(255),
            description TEXT,
            description_html TEXT,
            product_type VARCHAR(255),
            vendor VARCHAR(255),
            tags TEXT[],
            status VARCHAR(50),
            total_inventory INTEGER,
            online_store_url TEXT,
            seo_title VARCHAR(500),
            seo_description TEXT,
            options JSONB,
            variants JSONB,
            images JSONB,
            metafields JSONB,
            collections JSONB,
            shopify_created_at TIMESTAMP,
            shopify_updated_at TIMESTAMP,
            published_at TIMESTAMP,
            last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        orders_table = """
        CREATE TABLE IF NOT EXISTS orders (
            id BIGINT PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(255),
            customer_id BIGINT,
            total_price_amount DECIMAL(10,2),
            total_price_currency VARCHAR(3),
            subtotal_price_amount DECIMAL(10,2),
            subtotal_price_currency VARCHAR(3),
            total_tax_amount DECIMAL(10,2),
            total_tax_currency VARCHAR(3),
            total_shipping_amount DECIMAL(10,2),
            total_shipping_currency VARCHAR(3),
            financial_status VARCHAR(50),
            fulfillment_status VARCHAR(50),
            cancelled BOOLEAN,
            cancel_reason VARCHAR(100),
            tags TEXT,
            note TEXT,
            line_items JSONB,
            shipping_address JSONB,
            billing_address JSONB,
            customer_journey JSONB,
            shopify_created_at TIMESTAMP,
            shopify_updated_at TIMESTAMP,
            processed_at TIMESTAMP,
            closed_at TIMESTAMP,
            cancelled_at TIMESTAMP,
            last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Create indexes for better performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);",
            "CREATE INDEX IF NOT EXISTS idx_customers_created_at ON customers(shopify_created_at);",
            "CREATE INDEX IF NOT EXISTS idx_products_handle ON products(handle);",
            "CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);",
            "CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);",
            "CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(shopify_created_at);",
            "CREATE INDEX IF NOT EXISTS idx_orders_financial_status ON orders(financial_status);",
        ]
        
        with self.get_session() as session:
            # Create tables
            session.execute(text(customers_table))
            session.execute(text(products_table))
            session.execute(text(orders_table))
            
            # Create indexes
            for index_sql in indexes:
                session.execute(text(index_sql))
        
        logger.info("Database tables and indexes created successfully")
    
    def upsert_customer(self, customer_data: Dict[str, Any]):
        """Insert or update customer data"""
        
        query = """
        INSERT INTO customers (
            id, email, first_name, last_name, phone, created_at, updated_at,
            accepts_marketing, state, tags, total_spent_amount, total_spent_currency,
            number_of_orders, verified_email, tax_exempt, addresses, metafields,
            shopify_created_at, shopify_updated_at
        ) VALUES (
            :id, :email, :first_name, :last_name, :phone, :created_at, :updated_at,
            :accepts_marketing, :state, :tags, :total_spent_amount, :total_spent_currency,
            :number_of_orders, :verified_email, :tax_exempt, :addresses, :metafields,
            :shopify_created_at, :shopify_updated_at
        )
        ON CONFLICT (id) DO UPDATE SET
            email = EXCLUDED.email,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            phone = EXCLUDED.phone,
            updated_at = EXCLUDED.updated_at,
            accepts_marketing = EXCLUDED.accepts_marketing,
            state = EXCLUDED.state,
            tags = EXCLUDED.tags,
            total_spent_amount = EXCLUDED.total_spent_amount,
            total_spent_currency = EXCLUDED.total_spent_currency,
            number_of_orders = EXCLUDED.number_of_orders,
            verified_email = EXCLUDED.verified_email,
            tax_exempt = EXCLUDED.tax_exempt,
            addresses = EXCLUDED.addresses,
            metafields = EXCLUDED.metafields,
            shopify_updated_at = EXCLUDED.shopify_updated_at,
            last_sync_at = CURRENT_TIMESTAMP
        """
        
        # Process customer data to extract fields
        total_spent = customer_data.get('totalSpentV2', {})
        
        params = {
            'id': int(customer_data['id'].split('/')[-1]),
            'email': customer_data.get('email'),
            'first_name': customer_data.get('firstName'),
            'last_name': customer_data.get('lastName'),
            'phone': customer_data.get('phone'),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'accepts_marketing': customer_data.get('acceptsMarketing', False),
            'state': customer_data.get('state'),
            'tags': customer_data.get('tags'),
            'total_spent_amount': float(total_spent.get('amount', 0)) if total_spent.get('amount') else 0,
            'total_spent_currency': total_spent.get('currencyCode'),
            'number_of_orders': customer_data.get('numberOfOrders', 0),
            'verified_email': customer_data.get('verifiedEmail', False),
            'tax_exempt': customer_data.get('taxExempt', False),
            'addresses': json.dumps(customer_data.get('addresses', [])),
            'metafields': json.dumps(customer_data.get('metafields', {})),
            'shopify_created_at': customer_data.get('createdAt'),
            'shopify_updated_at': customer_data.get('updatedAt')
        }
        
        self.execute_query(query, params)
    
    def upsert_product(self, product_data: Dict[str, Any]):
        """Insert or update product data"""
        
        query = """
        INSERT INTO products (
            id, title, handle, description, description_html, product_type, vendor,
            tags, status, total_inventory, online_store_url, seo_title, seo_description,
            options, variants, images, metafields, collections, shopify_created_at,
            shopify_updated_at, published_at
        ) VALUES (
            :id, :title, :handle, :description, :description_html, :product_type, :vendor,
            :tags, :status, :total_inventory, :online_store_url, :seo_title, :seo_description,
            :options, :variants, :images, :metafields, :collections, :shopify_created_at,
            :shopify_updated_at, :published_at
        )
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            handle = EXCLUDED.handle,
            description = EXCLUDED.description,
            description_html = EXCLUDED.description_html,
            product_type = EXCLUDED.product_type,
            vendor = EXCLUDED.vendor,
            tags = EXCLUDED.tags,
            status = EXCLUDED.status,
            total_inventory = EXCLUDED.total_inventory,
            online_store_url = EXCLUDED.online_store_url,
            seo_title = EXCLUDED.seo_title,
            seo_description = EXCLUDED.seo_description,
            options = EXCLUDED.options,
            variants = EXCLUDED.variants,
            images = EXCLUDED.images,
            metafields = EXCLUDED.metafields,
            collections = EXCLUDED.collections,
            shopify_updated_at = EXCLUDED.shopify_updated_at,
            published_at = EXCLUDED.published_at,
            last_sync_at = CURRENT_TIMESTAMP
        """
        
        # Process product data
        seo = product_data.get('seo', {})
        
        params = {
            'id': int(product_data['id'].split('/')[-1]),
            'title': product_data.get('title'),
            'handle': product_data.get('handle'),
            'description': product_data.get('description'),
            'description_html': product_data.get('descriptionHtml'),
            'product_type': product_data.get('productType'),
            'vendor': product_data.get('vendor'),
            'tags': product_data.get('tags', []),
            'status': product_data.get('status'),
            'total_inventory': product_data.get('totalInventory'),
            'online_store_url': product_data.get('onlineStoreUrl'),
            'seo_title': seo.get('title'),
            'seo_description': seo.get('description'),
            'options': json.dumps(product_data.get('options', [])),
            'variants': json.dumps(product_data.get('variants', {})),
            'images': json.dumps(product_data.get('images', {})),
            'metafields': json.dumps(product_data.get('metafields', {})),
            'collections': json.dumps(product_data.get('collections', {})),
            'shopify_created_at': product_data.get('createdAt'),
            'shopify_updated_at': product_data.get('updatedAt'),
            'published_at': product_data.get('publishedAt')
        }
        
        self.execute_query(query, params)


# Convenience functions for backward compatibility
def get_pxy6_database_config() -> DatabaseConfig:
    """Get database configuration for pxy6 database"""
    app_config = get_config()
    return DatabaseConfig(
        host=app_config.pxy6_postgres_host,
        port=app_config.pxy6_postgres_port,
        database=app_config.pxy6_postgres_db,
        user=app_config.pxy6_postgres_user,
        password=app_config.pxy6_postgres_password
    )


def get_pxy6_database_manager() -> DatabaseManager:
    """Get a database manager instance for pxy6 database"""
    config = get_pxy6_database_config()
    manager = DatabaseManager(config)
    manager.connect()
    return manager


@contextmanager
def get_pxy6_database_connection():
    """Get a database session for pxy6 database with automatic cleanup"""
    manager = get_pxy6_database_manager()
    try:
        with manager.get_session() as session:
            yield session
    finally:
        manager.close()