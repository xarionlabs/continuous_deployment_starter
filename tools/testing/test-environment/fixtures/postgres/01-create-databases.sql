-- Create multiple databases for testing
CREATE DATABASE test_app_db;
CREATE DATABASE test_airflow_db;

-- Create test tables in app database
\c test_app_db;

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    inventory_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create shopify-specific tables
CREATE TABLE IF NOT EXISTS shopify_orders (
    id SERIAL PRIMARY KEY,
    shopify_order_id VARCHAR(50) UNIQUE NOT NULL,
    customer_email VARCHAR(255),
    total_price DECIMAL(10, 2),
    order_status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shopify_products (
    id SERIAL PRIMARY KEY,
    shopify_product_id VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255),
    vendor VARCHAR(255),
    product_type VARCHAR(255),
    price DECIMAL(10, 2),
    inventory_quantity INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create deployment tracking table
CREATE TABLE IF NOT EXISTS deployments (
    id SERIAL PRIMARY KEY,
    deployment_id VARCHAR(100) UNIQUE NOT NULL,
    app_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    environment VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    logs TEXT
);