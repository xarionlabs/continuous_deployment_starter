-- Seed test data
\c test_app_db;

-- Insert test users
INSERT INTO users (email, name) VALUES
    ('test1@example.com', 'Test User 1'),
    ('test2@example.com', 'Test User 2'),
    ('test3@example.com', 'Test User 3'),
    ('admin@example.com', 'Admin User')
ON CONFLICT (email) DO NOTHING;

-- Insert test products
INSERT INTO products (name, price, inventory_count) VALUES
    ('Test Product 1', 29.99, 100),
    ('Test Product 2', 49.99, 50),
    ('Test Product 3', 19.99, 75),
    ('Premium Product', 99.99, 25)
ON CONFLICT DO NOTHING;

-- Insert test orders
INSERT INTO orders (user_id, order_number, total_amount, status) VALUES
    (1, 'ORDER-001', 29.99, 'fulfilled'),
    (2, 'ORDER-002', 49.99, 'pending'),
    (3, 'ORDER-003', 19.99, 'fulfilled'),
    (1, 'ORDER-004', 99.99, 'processing')
ON CONFLICT (order_number) DO NOTHING;

-- Insert test Shopify orders
INSERT INTO shopify_orders (shopify_order_id, customer_email, total_price, order_status) VALUES
    ('shopify_001', 'customer1@example.com', 59.99, 'fulfilled'),
    ('shopify_002', 'customer2@example.com', 89.99, 'pending'),
    ('shopify_003', 'customer3@example.com', 39.99, 'fulfilled'),
    ('shopify_004', 'customer1@example.com', 129.99, 'processing')
ON CONFLICT (shopify_order_id) DO NOTHING;

-- Insert test Shopify products
INSERT INTO shopify_products (shopify_product_id, title, vendor, product_type, price, inventory_quantity) VALUES
    ('prod_001', 'Test Shopify Product 1', 'Test Vendor', 'Test Type', 29.99, 50),
    ('prod_002', 'Test Shopify Product 2', 'Test Vendor', 'Test Type', 49.99, 30),
    ('prod_003', 'Premium Shopify Product', 'Premium Vendor', 'Premium Type', 99.99, 10)
ON CONFLICT (shopify_product_id) DO NOTHING;

-- Insert test deployments
INSERT INTO deployments (deployment_id, app_name, version, environment, status, completed_at) VALUES
    ('deploy-test-app1-001', 'test-app1', '1.0.0', 'test', 'completed', CURRENT_TIMESTAMP - INTERVAL '1 day'),
    ('deploy-test-app2-001', 'test-app2', '1.0.0', 'test', 'completed', CURRENT_TIMESTAMP - INTERVAL '1 day'),
    ('deploy-shopify-app-001', 'test-shopify-app', '1.0.0', 'test', 'completed', CURRENT_TIMESTAMP - INTERVAL '1 day'),
    ('deploy-test-app1-002', 'test-app1', '1.0.1', 'test', 'in_progress', NULL)
ON CONFLICT (deployment_id) DO NOTHING;