# Test Environment

This directory contains a comprehensive test environment that simulates the production deployment pipeline with mock services. The test environment allows you to validate the complete release cycle without affecting production systems.

## Overview

The test environment includes:
- **Mock Services**: Simulated versions of all production services
- **Test Data**: Fixtures and seed data for testing
- **Integration Tests**: Comprehensive test suite for the release workflow
- **Automation**: Scripts for setup, testing, and cleanup
- **CI/CD Integration**: GitHub Actions workflow for automated testing

## Architecture

```
test-environment/
├── docker-compose.yml          # Main orchestration file
├── mock-services/              # Mock service implementations
│   ├── nginx/                  # Nginx proxy configuration
│   ├── app1/                   # FastAPI/Streamlit mock app
│   ├── app2/                   # React/Vite mock app
│   ├── shopify-app/           # Shopify Remix mock app
│   └── airflow/               # Airflow mock service
├── fixtures/                   # Test data and fixtures
│   ├── postgres/              # Database seed scripts
│   └── airflow/               # Airflow DAGs for testing
├── tests/                      # Test suites
│   ├── test_services.py       # Service health and integration tests
│   ├── test_release_workflow.py # Release workflow tests
│   └── conftest.py            # Test configuration and fixtures
└── scripts/                    # Automation scripts
    ├── setup-test-environment.sh
    ├── run-tests.sh
    ├── health-check.sh
    └── cleanup.sh
```

## Services

### Infrastructure Services

| Service | Port | Description |
|---------|------|-------------|
| **PostgreSQL** | 5433 | Test database with seed data |
| **Nginx** | 8080 | Reverse proxy for all services |
| **Registry** | 5000 | Mock container registry |

### Application Services

| Service | Port | Description |
|---------|------|-------------|
| **App1** | 8001/8501 | FastAPI + Streamlit mock application |
| **App2** | 3000 | React/Vite mock application |
| **Shopify App** | 3001 | Shopify Remix mock application |
| **Airflow** | 8082 | Apache Airflow with test DAGs |

### Test Services

| Service | Description |
|---------|-------------|
| **Test Runner** | Python-based test execution environment |

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM available for containers
- Ports 3000, 3001, 5000, 5433, 8001, 8080, 8082, 8501 available

### Setup and Run Tests

1. **Setup the test environment:**
   ```bash
   cd test-environment
   ./scripts/setup-test-environment.sh
   ```

2. **Run all tests:**
   ```bash
   ./scripts/run-tests.sh
   ```

3. **Run specific test categories:**
   ```bash
   ./scripts/run-tests.sh services    # Service health tests only
   ./scripts/run-tests.sh workflow    # Release workflow tests only
   ```

4. **Check service health:**
   ```bash
   ./scripts/health-check.sh
   ```

5. **Cleanup when done:**
   ```bash
   ./scripts/cleanup.sh
   ```

## Test Categories

### Service Health Tests (`test_services.py`)

Tests that verify all services are running and healthy:

- **TestServiceHealth**: Basic health checks for all services
- **TestServiceIntegration**: Service-to-service communication
- **TestDeploymentSimulation**: Deployment endpoint functionality
- **TestNginxProxyRouting**: Proxy configuration and routing

### Release Workflow Tests (`test_release_workflow.py`)

Tests that simulate the complete release pipeline:

- **TestReleaseWorkflow**: End-to-end release pipeline simulation
- **TestErrorHandling**: Error scenarios and recovery

## Manual Testing

### Service URLs

Once the environment is running, you can access services at:

- **App1 (FastAPI)**: http://localhost:8001
- **App1 (Streamlit)**: http://localhost:8501
- **App2 (React)**: http://localhost:3000
- **Shopify App**: http://localhost:3001
- **Nginx Proxy**: http://localhost:8080
- **Airflow**: http://localhost:8082 (admin/admin)
- **Registry**: http://localhost:5000

### Database Access

Connect to the test database:
```bash
psql -h localhost -p 5433 -U test_user -d test_db
# Password: test_password
```

### Service Logs

View logs for any service:
```bash
docker-compose logs test-app1
docker-compose logs test-postgres
docker-compose logs test-nginx
```

## CI/CD Integration

The test environment integrates with GitHub Actions through the `test-release.yml` workflow:

### Workflow Triggers

- **Manual**: Workflow dispatch with configurable test types
- **Pull Request**: Automatic testing on PR to main/develop
- **Push**: Automatic testing on push to main

### Test Types

- **all**: Run all test categories (default)
- **services**: Service health tests only
- **workflow**: Release workflow tests only
- **performance**: Performance and load tests

### Usage

1. **Manual trigger**: Go to Actions → Test Release Environment → Run workflow
2. **PR trigger**: Create a PR with changes to test environment
3. **Push trigger**: Push changes to main branch

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TEST_ENV` | Test environment identifier | `test` |
| `TEST_RUN_ID` | Unique test run identifier | Generated |
| `DATABASE_URL` | PostgreSQL connection string | Auto-configured |

### Test Data

The test environment includes realistic test data:

- **Users**: Sample user accounts
- **Orders**: Mock order data
- **Products**: Sample product catalog
- **Deployments**: Historical deployment records
- **Shopify Data**: Mock Shopify orders and products

## Development

### Adding New Tests

1. Create test files in `tests/` directory
2. Use existing fixtures from `conftest.py`
3. Follow the naming convention `test_*.py`
4. Add to the appropriate test category

### Adding New Mock Services

1. Create service directory under `mock-services/`
2. Add Dockerfile and application code
3. Update `docker-compose.yml` with service definition
4. Add health check endpoint
5. Update test suites to include new service

### Modifying Test Data

1. Update SQL files in `fixtures/postgres/`
2. Restart the test environment to apply changes
3. Update tests if data structure changes

## Troubleshooting

### Common Issues

1. **Services not starting**: Check Docker resource limits
2. **Database connection errors**: Verify PostgreSQL is healthy
3. **Port conflicts**: Ensure required ports are available
4. **Test failures**: Check service logs for errors

### Debug Commands

```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs <service_name>

# Restart a service
docker-compose restart <service_name>

# Rebuild services
docker-compose up -d --build

# Clean restart
docker-compose down -v
docker-compose up -d --build
```

### Performance Tuning

- Increase Docker memory limit to 8GB for better performance
- Use SSD storage for faster container startup
- Adjust service health check intervals if needed

## Security

The test environment uses:
- Isolated Docker network
- Non-privileged containers
- Test-only credentials
- No persistent data storage outside containers

## Maintenance

### Regular Tasks

1. **Update base images**: Rebuild with latest security patches
2. **Update test data**: Keep fixtures current with production schema
3. **Review test coverage**: Ensure all critical paths are tested
4. **Monitor performance**: Adjust resource limits as needed

### Cleanup

The test environment is designed to be ephemeral:
- All data is destroyed when containers are removed
- No persistent volumes outside the test session
- Automatic cleanup in CI/CD pipeline

## Contributing

When contributing to the test environment:

1. **Test locally**: Run the full test suite before submitting
2. **Update documentation**: Keep this README current
3. **Add tests**: Include tests for new functionality
4. **Follow patterns**: Use existing service patterns for consistency

## Support

For issues with the test environment:

1. Check the troubleshooting section
2. Review service logs
3. Verify system requirements
4. Check for port conflicts
5. Ensure Docker has sufficient resources

## Related Documentation

- [Main Project README](../README.md)
- [CLAUDE.md](../CLAUDE.md) - Project instructions
- [GitHub Actions Workflows](../.github/workflows/)
- [Application Documentation](../applications/)