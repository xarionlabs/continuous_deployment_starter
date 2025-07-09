# Airflow DAGs Test Suite

This directory contains comprehensive tests for the Airflow DAGs using real Shopify API response payloads.

## Test Structure

```
tests/
├── README.md                          # This file
├── conftest.py                        # Pytest configuration and fixtures
├── fixtures/
│   └── shopify_responses/
│       ├── products_response.json          # Real Shopify products API response
│       ├── customers_with_orders_response.json  # Real Shopify customers API response
│       └── product_images_response.json    # Real Shopify product images API response
├── test_data_processing.py           # Tests for data processing functions
├── test_dag_functions.py             # Tests for DAG operators and hooks
├── test_dags.py                      # Tests for DAG structure and configuration
├── test_shopify_integration.py       # Integration tests with mocked/real APIs
└── test_utils.py                     # Tests for utility functions
```

## Test Categories

### 1. Data Processing Tests (`test_data_processing.py`)
- **Purpose**: Validate data processing logic using real Shopify API responses
- **Coverage**: 
  - Product data structure validation
  - Customer data structure validation
  - Product images data structure validation
  - Rate limit handling
  - Data integrity across all fixtures
  - Database upsert processing

### 2. DAG Function Tests (`test_dag_functions.py`)
- **Purpose**: Test specific DAG task functions and operators
- **Coverage**:
  - `ShopifyExtractOperator` functionality
  - `ShopifyStoreOperator` functionality
  - `ShopifyHook` operations
  - Data transformation functions
  - Error handling in operators

### 3. DAG Structure Tests (`test_dags.py`)
- **Purpose**: Validate DAG configuration and structure
- **Coverage**:
  - DAG loading without errors
  - Required DAGs presence
  - Task dependencies
  - Default arguments validation
  - Schedule interval configuration

### 4. Integration Tests (`test_shopify_integration.py`)
- **Purpose**: End-to-end testing with real or mocked APIs
- **Coverage**:
  - Shopify GraphQL client functionality
  - Database connectivity
  - Rate limiting behavior
  - Pagination handling
  - Authentication patterns

## Test Fixtures

The test fixtures in `fixtures/shopify_responses/` contain real Shopify API responses:

### `products_response.json`
- Contains comprehensive product data including variants, images, collections
- Tests product catalog synchronization
- Validates complex nested data structures
- Size: ~28,000 tokens (large dataset)

### `customers_with_orders_response.json`
- Contains customer data with associated orders
- Tests customer and order data processing
- Includes rate limiting information
- Validates pagination cursors

### `product_images_response.json`
- Contains product image data and metadata
- Tests image URL handling and metadata processing
- Validates image dimensions and alt text

## Running Tests

### Quick Start
```bash
# Run all tests with the test runner script
./run_payload_tests.sh

# Or run specific test files
python -m pytest tests/test_data_processing.py -v
python -m pytest tests/test_dag_functions.py -v
```

### Test Categories
```bash
# Unit tests only (fast)
python -m pytest -m unit -v

# Integration tests only (may require environment setup)
python -m pytest -m integration -v

# Slow tests (comprehensive data processing)
python -m pytest -m slow -v
```

### With Coverage
```bash
# Generate coverage report
python -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html
```

### Docker Testing
```bash
# Build and test in Docker (recommended for CI/CD)
docker build -t airflow-dags-test .
docker run --rm airflow-dags-test pytest tests/ -v
```

## Test Configuration

### Environment Variables
The tests use these environment variables (set automatically in `conftest.py`):
- `SHOPIFY_SHOP_NAME`: Test shop name
- `SHOPIFY_ACCESS_TOKEN`: Test access token
- `PXY6_POSTGRES_*`: Database connection parameters

### Pytest Markers
- `@pytest.mark.unit`: Unit tests (default for most tests)
- `@pytest.mark.integration`: Integration tests requiring external services
- `@pytest.mark.slow`: Tests that take longer to run

### Fixtures
- `products_fixture`: Loads products response data
- `customers_fixture`: Loads customers response data
- `product_images_fixture`: Loads product images response data
- `mock_shopify_client`: Mocked Shopify client for testing
- `mock_database_manager`: Mocked database manager for testing

## Benefits of Real Payload Testing

1. **Real-World Validation**: Tests use actual Shopify API responses, ensuring compatibility with real data
2. **Data Structure Validation**: Comprehensive validation of nested JSON structures
3. **Edge Case Coverage**: Real data includes edge cases like null values, empty arrays, etc.
4. **Rate Limit Testing**: Uses real rate limiting data from Shopify API responses
5. **Pagination Testing**: Validates cursor-based pagination with real cursors
6. **Schema Evolution**: Helps detect when Shopify API changes affect our DAGs

## Adding New Tests

When adding new tests:

1. **Use Real Data**: Prefer using the fixture data over mocked responses
2. **Test Data Processing**: Validate how your code handles the real data structures
3. **Test Error Cases**: Include tests for malformed or unexpected data
4. **Add Appropriate Markers**: Use `@pytest.mark.unit` or `@pytest.mark.integration`
5. **Update Documentation**: Update this README when adding new test categories

## Maintenance

### Updating Fixtures
When Shopify API changes or you need new test data:

1. Capture new API responses using the actual Shopify GraphQL client
2. Save them in `fixtures/shopify_responses/` with descriptive names
3. Update test files to use the new fixtures
4. Ensure all tests pass with the new data

### Adding New DAG Components
When adding new DAG operators, hooks, or utilities:

1. Create corresponding test files following the naming convention
2. Use the existing fixtures where possible
3. Add new fixtures if testing different API endpoints
4. Update the test runner script if needed

## CI/CD Integration

These tests are designed to run in CI/CD pipelines:

- **Fast Unit Tests**: Run on every commit
- **Integration Tests**: Run on staging deployments
- **Full Test Suite**: Run on release branches

The Docker-based testing ensures consistent results across different environments.