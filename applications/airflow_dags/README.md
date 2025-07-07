# Shopify GraphQL Client and Test Framework for Airflow DAGs

This project provides a robust Shopify GraphQL client and comprehensive test framework for Airflow DAGs, designed to handle Shopify data integration workflows with proper authentication, rate limiting, pagination, and database operations.

## Features

### Shopify GraphQL Client (`src/utils/shopify_graphql.py`)
- **Authentication**: Handles Shopify access tokens with proper headers
- **Rate Limiting**: Implements intelligent rate limiting based on GraphQL cost analysis
- **Pagination**: Supports cursor-based pagination for large datasets
- **Error Handling**: Comprehensive error handling and retry logic with exponential backoff
- **Async Operations**: Full async/await support for efficient concurrent operations
- **Specific Queries**: Implements the exact GraphQL queries required:
  - `getAllProductData` - Retrieves all product information including variants and images
  - `getProductImages` - Fetches product images with metadata
  - `getCustomersWithOrders` - Gets customer data with complete order history

### Database Manager (`src/utils/database.py`)
- **Connection Pooling**: Efficient PostgreSQL connection management using asyncpg
- **Schema Management**: Automatic creation of Shopify-specific database tables
- **Data Operations**: Upsert operations for products, customers, and orders
- **Sync Tracking**: Tracks synchronization timestamps for incremental updates
- **Error Recovery**: Robust error handling and transaction management

### Test Framework (`tests/test_shopify_integration.py`)
- **Live Store Testing**: Tests against real Shopify stores with proper authentication
- **Mock Testing**: Unit tests with mocked responses for CI/CD environments
- **Integration Tests**: End-to-end testing of complete sync workflows
- **Performance Tests**: Concurrent operations and batch processing validation
- **Error Recovery**: Tests for handling various failure scenarios

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
export SHOPIFY_STORE_URL="https://your-store.myshopify.com"
export SHOPIFY_ACCESS_TOKEN="your-access-token"
export POSTGRES_PASSWORD="your-database-password"
```

## Usage

### Basic Shopify Client Usage

```python
from src.utils.shopify_graphql import ShopifyGraphQLClient

# Initialize client
client = ShopifyGraphQLClient(
    store_url="https://your-store.myshopify.com",
    access_token="your-access-token"
)

# Use with async context manager
async with client:
    # Test connection
    if await client.test_connection():
        print("Connected successfully")
    
    # Get shop information
    shop_info = await client.get_shop_info()
    print(f"Shop: {shop_info['name']}")
    
    # Get all products with pagination
    async for products_batch in client.get_all_product_data(batch_size=50):
        for product in products_batch:
            print(f"Product: {product['title']}")
    
    # Get customers with orders
    async for customers_batch in client.get_customers_with_orders(batch_size=50):
        for customer in customers_batch:
            print(f"Customer: {customer['email']}")
```

### Database Operations

```python
from src.utils.database import DatabaseManager

# Initialize database manager
async with DatabaseManager() as db:
    # Test connection
    if await db.test_connection():
        print("Database connected")
    
    # Create tables
    await db.create_tables()
    
    # Insert product data
    await db.upsert_product(product_data)
    
    # Insert customer data
    await db.upsert_customer(customer_data)
    
    # Get statistics
    products_count = await db.get_products_count()
    customers_count = await db.get_customers_count()
    print(f"Products: {products_count}, Customers: {customers_count}")
```

### Complete Sync Workflow

```python
from src.utils.shopify_graphql import ShopifyGraphQLClient
from src.utils.database import DatabaseManager

async def sync_shopify_data():
    client = ShopifyGraphQLClient(
        store_url="https://your-store.myshopify.com",
        access_token="your-access-token"
    )
    
    async with client, DatabaseManager() as db:
        # Ensure database tables exist
        await db.create_tables()
        
        # Sync products
        async for products_batch in client.get_all_product_data():
            for product in products_batch:
                await db.upsert_product(product)
        
        # Sync customers
        async for customers_batch in client.get_customers_with_orders():
            for customer in customers_batch:
                await db.upsert_customer(customer)
        
        print("Sync completed successfully")

# Run the sync
import asyncio
asyncio.run(sync_shopify_data())
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/test_shopify_integration.py::TestShopifyGraphQLClient -v
pytest tests/test_shopify_integration.py::TestDatabaseManager -v
pytest tests/test_shopify_integration.py::TestIntegration -v

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# Run only mock tests (skip live API calls)
export SKIP_LIVE_TESTS=true
pytest tests/ -v
```

### Test Configuration

Set these environment variables for live testing:
- `SHOPIFY_STORE_URL`: Your Shopify store URL
- `SHOPIFY_ACCESS_TOKEN`: Shopify access token with appropriate permissions
- `POSTGRES_PASSWORD`: Database password for the pxy6_airflow user
- `SKIP_LIVE_TESTS`: Set to "true" to skip tests requiring live credentials

### Test Categories

1. **Unit Tests**: Test individual components with mocked dependencies
2. **Integration Tests**: Test complete workflows with real Shopify API
3. **Performance Tests**: Validate concurrent operations and batch processing
4. **Error Recovery Tests**: Ensure proper handling of various failure scenarios

## GraphQL Queries

The client implements these specific GraphQL queries:

### getAllProductData
Retrieves comprehensive product information including:
- Product metadata (title, handle, description, etc.)
- Product variants with pricing and inventory
- Product images with metadata
- SEO information and metafields
- Options and variant configurations

### getProductImages
Fetches detailed image information for specific products:
- Image URLs and metadata
- Dimensions and alt text
- Original and transformed sources

### getCustomersWithOrders
Gets customer data with complete order history:
- Customer profile information
- Order history with line items
- Customer journey analytics
- Addresses and metafields
- Purchase behavior metrics

## Database Schema

The database schema includes these tables:

- `shopify_products`: Product information and metadata
- `shopify_product_variants`: Product variants with pricing
- `shopify_product_images`: Product images and metadata
- `shopify_customers`: Customer profiles and preferences
- `shopify_orders`: Order information and status
- `shopify_order_line_items`: Individual order line items

All tables include:
- `synced_at`: Timestamp for tracking data freshness
- `raw_data`: Complete JSON payload for future extensibility
- Proper indexes for performance optimization

## Rate Limiting

The client implements intelligent rate limiting:
- Monitors GraphQL cost analysis from Shopify headers
- Automatically waits when approaching rate limits
- Configurable rate limit buffer to prevent hitting limits
- Exponential backoff for retry operations

## Error Handling

Comprehensive error handling includes:
- Network connectivity issues
- Authentication failures
- Rate limit exceeded scenarios
- GraphQL query errors
- Database connection problems
- Data validation errors

## Configuration

### Environment Variables

- `SHOPIFY_STORE_URL`: Shopify store URL
- `SHOPIFY_ACCESS_TOKEN`: Shopify access token
- `POSTGRES_HOST`: Database host (default: "db")
- `POSTGRES_PORT`: Database port (default: 5432)
- `POSTGRES_DATABASE`: Database name (default: "pxy6")
- `POSTGRES_USER`: Database user (default: "pxy6_airflow")
- `POSTGRES_PASSWORD`: Database password
- `DB_MIN_CONNECTIONS`: Minimum database connections (default: 1)
- `DB_MAX_CONNECTIONS`: Maximum database connections (default: 10)
- `DB_COMMAND_TIMEOUT`: Database command timeout (default: 60)

### Shopify API Permissions

The Shopify access token requires these permissions:
- `read_products`: Access to product information
- `read_customers`: Access to customer data
- `read_orders`: Access to order information
- `read_inventory`: Access to inventory levels
- `read_product_listings`: Access to product listings
- `read_analytics`: Access to analytics data (for customer journey)

## Production Considerations

### Performance
- Use connection pooling for database operations
- Implement proper batch sizes for pagination
- Monitor and respect rate limits
- Use async operations for concurrent processing

### Security
- Store credentials securely (use environment variables or secret management)
- Implement proper access controls for database connections
- Use HTTPS for all API communications
- Validate and sanitize all input data

### Monitoring
- Log all operations for debugging and monitoring
- Track sync times and success rates
- Monitor database performance and growth
- Set up alerts for rate limit warnings

### Scaling
- Consider implementing queue-based processing for large datasets
- Use distributed processing for multiple stores
- Implement incremental sync based on timestamps
- Consider data archiving for historical information

## Contributing

1. Follow Python best practices and PEP 8 style guidelines
2. Add comprehensive tests for new features
3. Update documentation for any API changes
4. Ensure all tests pass before submitting changes
5. Use type hints for better code clarity

## License

This project is part of the continuous deployment starter framework and follows the same licensing terms.