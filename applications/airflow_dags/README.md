# Airflow DAGs Package

This package contains Apache Airflow DAGs for syncing Shopify data to PostgreSQL using GraphQL queries.

## Project Structure

```
airflow_dags/
├── src/                  # Source directory (installed as pxy6 package)
│   ├── operators/        # Custom operators → pxy6.operators
│   ├── hooks/            # Custom hooks → pxy6.hooks
│   ├── utils/            # Utility functions → pxy6.utils
│   └── __init__.py       # Package initialization
├── dags/                 # DAG definitions (top-level, not in package)
├── tests/                # Test files
├── entrypoints/          # Docker entrypoints
├── setup.py             # Package setup configuration
├── pyproject.toml       # Modern Python project configuration
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container definition
└── README.md           # This file
```

## Architecture

This project follows standard Airflow patterns:

- **DAGs folder contains only DAGs** - Pure DAG files with no package structure
- **Dependencies come from installed packages** - The `pxy6` package is installed during Docker build
- **Clean separation** - DAGs import from the installed `pxy6` package, not relative imports

## Local Development

### Prerequisites

- Python 3.9+
- Docker
- Access to Shopify store with Admin API permissions

### Setup

1. **Install the package in development mode:**
   ```bash
   pip install -e .
   ```

2. **Set environment variables:**
   ```bash
   export SHOPIFY_SHOP_NAME="your-shop-name"
   export SHOPIFY_ACCESS_TOKEN="your-access-token"
   export PXY6_POSTGRES_HOST="localhost"
   export PXY6_POSTGRES_PASSWORD="your-password"
   ```

3. **Run tests:**
   ```bash
   python -m pytest tests/ -v
   ```

### DAG Development

- Place DAG files in `dags/` (top-level directory)
- Import from the `pxy6` package: `from pxy6.operators.shopify_operator import ShopifyOperator`
- Add operators, hooks, and utilities to the `pxy6/` package
- Follow existing patterns for error handling and logging

### Testing

- Unit tests: `tests/test_utils.py`
- Integration tests: `tests/test_shopify_integration.py`
- DAG structure tests: `tests/test_dags.py`

## Docker Usage

### Build and Test

```bash
# Build the image (installs pxy6 package)
docker build -t airflow-dags .

# Run tests
docker run --rm airflow-dags

# Run specific test
docker run --rm airflow-dags pytest tests/test_dags.py -v
```

### Local Development with Docker

```bash
# Build for development
docker build -t airflow-dags-dev .

# Run with environment variables
docker run --rm \
  -e SHOPIFY_SHOP_NAME=your-shop \
  -e SHOPIFY_ACCESS_TOKEN=your-token \
  airflow-dags-dev
```

## DAG Overview

### shopify_customer_data
- **Schedule**: Daily at 2:00 AM UTC
- **Purpose**: Extract customer data from Shopify
- **Data**: Customer profiles, contact information, segments

### shopify_order_data  
- **Schedule**: Every 4 hours
- **Purpose**: Extract order data from Shopify
- **Data**: Orders, line items, fulfillment status

### shopify_past_purchases
- **Schedule**: Daily at 2:00 AM UTC
- **Purpose**: Extract comprehensive customer purchase history
- **Data**: Customer orders with complete purchase journey

### shopify_store_metadata
- **Schedule**: Daily at 3:00 AM UTC
- **Purpose**: Extract product catalog and store metadata
- **Data**: Products, variants, collections, images

### shopify_data_pipeline
- **Schedule**: Daily at 1:00 AM UTC
- **Purpose**: Main orchestration DAG
- **Data**: Coordinates all other DAGs and provides unified monitoring

## Configuration

### Environment Variables

- `SHOPIFY_SHOP_NAME`: Your Shopify store name (without .myshopify.com)
- `SHOPIFY_ACCESS_TOKEN`: Admin API access token
- `PXY6_POSTGRES_HOST`: PostgreSQL host for app.pxy6.com database
- `PXY6_POSTGRES_PASSWORD`: PostgreSQL password for pxy6_airflow user

### Database Connection

The DAGs connect to the app.pxy6.com PostgreSQL database using the `pxy6_airflow` user. This user has read/write access to tables needed for Shopify data synchronization.

## Monitoring

- All DAGs include comprehensive logging using structlog
- Error handling with exponential backoff for API calls
- Rate limit monitoring for Shopify API
- Database connection health checks

## API Integration

### Shopify GraphQL API

- Uses Admin API version 2023-10
- Implements rate limiting and retry logic
- Supports both incremental and full sync modes
- Comprehensive error handling for API failures

### Key Queries

- `getCustomersWithOrders`: Customer purchase data
- `getAllProductData`: Product catalog information
- `getProductImages`: Product image metadata

## Development Guidelines

1. **Package Structure**: Use the `pxy6` package for reusable components
2. **DAG Imports**: Always import from `pxy6.module` not relative imports
3. **Error Handling**: Always include proper error handling and logging
4. **Rate Limiting**: Respect Shopify API rate limits
5. **Idempotency**: Ensure DAGs can be re-run safely
6. **Testing**: Write tests for new functionality
7. **Documentation**: Update README for new features

## Troubleshooting

### Common Issues

1. **Import Errors**: Check that imports use `from pxy6.module import ...`
2. **Database Connection**: Verify credentials and network access
3. **API Rate Limits**: Check Shopify API usage and implement backoff
4. **Memory Issues**: Monitor large data sets and implement chunking

### Debugging

```bash
# Check DAG imports
python -c "from dags.shopify_data_pipeline import dag"

# Test pxy6 package imports
python -c "from pxy6.utils.database import get_pxy6_database_manager; print('DB OK')"

# Test Shopify connection
python -c "from pxy6.utils.shopify_graphql import ShopifyGraphQLClient; print('Shopify OK')"
```

## Contributing

1. Follow existing code patterns
2. Use the `pxy6` package for shared components
3. Write tests for new features
4. Update documentation
5. Test in Docker environment
6. Ensure all DAGs load without errors