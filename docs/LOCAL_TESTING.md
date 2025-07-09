# Local Testing Guide

## Overview

This guide provides comprehensive instructions for testing the continuous deployment system locally before pushing changes to production. The local testing framework allows you to validate GitHub Actions workflows, test deployment logic, and ensure system reliability without affecting live environments.

## Prerequisites

### System Requirements
- **Operating System**: macOS, Linux, or Windows (with WSL2)
- **Docker**: Docker Desktop or Docker Engine
- **Git**: Version control system
- **Act**: GitHub Actions local runner
- **Python**: Version 3.9 or higher (for development)
- **Node.js**: Version 18 or higher (for frontend applications)

### Installing Act

Act is the primary tool for running GitHub Actions workflows locally.

#### macOS
```bash
# Using Homebrew
brew install act

# Or using curl
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

#### Linux
```bash
# Using curl
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Or using package manager (Ubuntu/Debian)
sudo apt install act
```

#### Windows
```bash
# Using Chocolatey
choco install act-cli

# Or using Scoop
scoop install act
```

## Quick Start

### 1. Set Up Local Testing Environment

Navigate to the tools/testing directory and initialize the testing environment:

```bash
cd tools/testing
./mock-env.sh                 # Setup mock environment variables
```

### 2. Run Your First Test

Test the build workflow:

```bash
# Test build workflow
./run-tests.sh build

# Test all workflows interactively
./run-tests.sh -i

# Test specific scenario
./scripts/simulate-workflow.sh push-force-build
```

### 3. Verify Results

Check the test results and logs:

```bash
# View test logs
ls logs/

# Check specific log file
less logs/build-push.log

# View test artifacts
ls artifacts/
```

## Testing Framework Architecture

### Directory Structure

```
tools/testing/
├── README.md                   # Detailed testing documentation
├── docker-compose.test.yml     # Testing infrastructure
├── run-tests.sh               # Main testing script
├── mock-env.sh                # Environment setup script
├── events/                    # GitHub event payloads
│   ├── push.json              # Standard push event
│   ├── push-force-build.json  # Force build scenario
│   ├── push-skip-build.json   # Skip build scenario
│   ├── push-deploy-services.json # Selective deployment
│   ├── push-release-only.json # Release-only mode
│   ├── workflow_dispatch.json # Manual trigger
│   └── schedule.json          # Scheduled run
├── scripts/                   # Testing utilities
│   ├── simulate-workflow.sh   # Workflow simulation
│   └── test-conditions.sh     # Logic validation
├── test-configs/              # Test configurations
│   └── nginx.conf            # Nginx test config
├── logs/                      # Test execution logs
├── artifacts/                 # Test artifacts
└── [generated files]          # Environment files
```

### Core Components

#### 1. Main Testing Script (`run-tests.sh`)

The primary interface for all testing operations:

```bash
# Basic usage
./run-tests.sh [OPTIONS] [WORKFLOW]

# Options:
-e, --environment    # Environment to test (test, staging, live)
-p, --profile       # Docker Compose profile 
-c, --cleanup       # Clean up after testing
-v, --verbose       # Enable verbose output
-i, --interactive   # Interactive mode
-s, --skip-setup    # Skip infrastructure setup
```

#### 2. Environment Setup (`mock-env.sh`)

Creates a mock GitHub Actions environment:

```bash
# Setup mock environment
./mock-env.sh

# Export to current shell
./mock-env.sh --export

# Validate setup
./mock-env.sh --validate

# Clean up
./mock-env.sh --cleanup
```

#### 3. Docker Compose Test Infrastructure

Provides isolated testing services:

- **PostgreSQL Test Database**: `postgres-test:5433`
- **Redis Test Instance**: `redis-test:6380`
- **Local Container Registry**: `localhost:5000`
- **Mock Services**: WireMock for API simulation
- **Test Utilities**: Alpine container with tools

## Testing Scenarios

### 1. Standard Workflow Testing

#### Build Workflow
```bash
# Test normal build process
./run-tests.sh build

# Test with specific environment
./run-tests.sh -e staging build

# Test with verbose output
./run-tests.sh -v build

# Test with cleanup
./run-tests.sh -c build
```

#### Release Workflow
```bash
# Test staging release
./run-tests.sh -e staging release

# Test production release
./run-tests.sh -e live release

# Test with integration profile
./run-tests.sh -p integration-test release
```

#### E2E Testing
```bash
# Test end-to-end workflow
./run-tests.sh e2e

# Test specific application E2E
./run-tests.sh -e staging e2e
```

### 2. Commit Message Tag Testing

#### Force Build
```bash
# Test force build scenario
./scripts/simulate-workflow.sh push-force-build

# Or using event file directly
act push -e events/push-force-build.json
```

#### Skip Build
```bash
# Test skip build scenario
./scripts/simulate-workflow.sh push-skip-build

# Verify workflow is skipped
act push -e events/push-skip-build.json --dry-run
```

#### Deploy Specific Services
```bash
# Test selective deployment
./scripts/simulate-workflow.sh push-deploy-services

# Test deploy all services
./scripts/simulate-workflow.sh push-deploy-all
```

#### Release-Only Mode
```bash
# Test release-only scenario
./scripts/simulate-workflow.sh push-release-only

# Verify builds are skipped
act push -e events/push-release-only.json -v
```

### 3. Condition Testing

Use `test-conditions.sh` to validate workflow logic:

```bash
# Test all conditions
./scripts/test-conditions.sh all

# Test specific conditions
./scripts/test-conditions.sh commit-tags
./scripts/test-conditions.sh file-changes
./scripts/test-conditions.sh service-detection
./scripts/test-conditions.sh environment-vars
./scripts/test-conditions.sh error-conditions
```

### 4. Application-Specific Testing

#### Shopify App (app.pxy6.com)
```bash
# Test Shopify app build
./run-tests.sh -v build

# Test with specific changes
echo "applications/app.pxy6.com/src/app/routes/_index.tsx" > /tmp/changed_files
./scripts/test-conditions.sh file-changes
```

#### React App (pxy6.com)
```bash
# Test React app build
./run-tests.sh -p integration-test build

# Test E2E for React app
./run-tests.sh -e staging e2e
```

#### Python App (app_1)
```bash
# Note: app_1 has skipped-Dockerfile, so build testing is limited
./scripts/test-conditions.sh service-detection
```

### 5. Infrastructure Testing

#### PostgreSQL Service
```bash
# Test with PostgreSQL profile
./run-tests.sh -p default build

# Test database connections
docker-compose -f docker-compose.test.yml exec postgres-test psql -U test_user -d test_db -c "\l"
```

#### Nginx Proxy
```bash
# Test with nginx configuration
./run-tests.sh -p integration-test build

# Test nginx config
docker-compose -f docker-compose.test.yml exec nginx-test nginx -t
```

#### Airflow Integration
```bash
# Test Airflow DAGs
./run-tests.sh -p integration-test build

# Test DAG imports
docker-compose -f docker-compose.test.yml exec airflow-test python -c "from dags.shopify_dag import dag"
```

## Docker Compose Profiles

### Default Profile
Basic testing infrastructure:
```bash
./run-tests.sh -p default build
```

Services included:
- PostgreSQL test database
- Redis test instance
- Local container registry
- Test utilities

### Integration Test Profile
Full application testing:
```bash
./run-tests.sh -p integration-test all
```

Services included:
- All default services
- Test application instances
- Application-specific configurations
- Database with test data

### Mock Services Profile
External service simulation:
```bash
./run-tests.sh -p mock-services build
```

Services included:
- All default services
- WireMock for API mocking
- External service configurations
- Test data for mocked services

## Environment Configuration

### Test Environment Variables

The testing framework creates three main environment files:

#### `test.env` - GitHub Actions Variables
```bash
GITHUB_REPOSITORY=test-org/test-repo
GITHUB_REF=refs/heads/main
GITHUB_SHA=abc123def456
GITHUB_EVENT_NAME=push
GITHUB_ACTOR=test-user
GITHUB_WORKSPACE=/workspace
```

#### `secrets.env` - Mock Secrets
```bash
GITHUB_TOKEN=ghp_test_token
DATABASE_URL=postgresql://test_user:test_password@postgres-test:5432/test_db
REDIS_URL=redis://redis-test:6379
HOST=test-server
USERNAME=test-user
KEY=test-ssh-key
```

#### `variables.env` - Public Variables
```bash
REGISTRY=localhost:5000
APP_ENV=test
NODE_ENV=test
DATABASE_HOST=postgres-test
REDIS_HOST=redis-test
```

### Custom Environment Variables

Add custom variables for testing:

```bash
# Add to test.env
echo "CUSTOM_VAR=custom_value" >> tools/testing/test.env

# Add to secrets.env
echo "CUSTOM_SECRET=secret_value" >> tools/testing/secrets.env

# Use in tests
./run-tests.sh -v build
```

## Testing Best Practices

### 1. Test Before Push

Always run local tests before pushing changes:

```bash
# Complete test suite
./tools/testing/run-tests.sh all

# Quick smoke test
./tools/testing/run-tests.sh build
```

### 2. Use Appropriate Profiles

Choose the right testing profile:

- **Default**: Basic workflow testing
- **Integration-test**: Full application testing
- **Mock-services**: External dependency testing

### 3. Validate Specific Scenarios

Test edge cases and specific scenarios:

```bash
# Test error conditions
./tools/testing/scripts/test-conditions.sh error-conditions

# Test service dependencies
./tools/testing/scripts/test-conditions.sh dependency-order

# Test build matrix
./tools/testing/scripts/test-conditions.sh build-matrix
```

### 4. Clean Up Resources

Regularly clean up test resources:

```bash
# Clean up after tests
./tools/testing/run-tests.sh -c build

# Clean Docker resources
docker system prune -a

# Clean test environment
./tools/testing/mock-env.sh --cleanup
```

### 5. Monitor Test Results

Check test results and logs:

```bash
# View test summary
./tools/testing/run-tests.sh --summary

# Check specific logs
less tools/testing/logs/build-push.log

# View test artifacts
ls tools/testing/artifacts/
```

## Advanced Testing Scenarios

### 1. Custom Event Payloads

Create custom test scenarios:

```json
{
  "ref": "refs/heads/feature-branch",
  "commits": [
    {
      "message": "Custom test scenario [force-build]",
      "modified": ["applications/custom-app/src/file.js"]
    }
  ]
}
```

Save as `tools/testing/events/custom-scenario.json` and run:

```bash
act push -e tools/testing/events/custom-scenario.json
```

### 2. Service-Specific Testing

Test specific services in isolation:

```bash
# Test only PostgreSQL changes
echo "services/01_postgres/docker-compose.yml" > /tmp/changed_files
./scripts/test-conditions.sh service-detection

# Test only Nginx changes
echo "services/03_nginx-proxy/nginx.conf" > /tmp/changed_files
./scripts/test-conditions.sh service-detection
```

### 3. Dependency Chain Testing

Test service dependency chains:

```bash
# Test dependency ordering
./scripts/test-conditions.sh dependency-order

# Test cross-service impacts
./scripts/test-conditions.sh service-detection
```

### 4. Performance Testing

Test workflow performance:

```bash
# Time workflow execution
time ./run-tests.sh build

# Profile resource usage
docker stats --no-stream
```

### 5. Security Testing

Test security aspects:

```bash
# Test secret handling
./scripts/test-conditions.sh environment-vars

# Test container security
docker run --rm -it --security-opt seccomp=unconfined alpine sh
```

## Troubleshooting Local Testing

### Common Issues

#### Act Not Found
```bash
# Install act
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Verify installation
act --version

# Alternative installation methods
brew install act                    # macOS
choco install act-cli              # Windows
sudo snap install act             # Ubuntu Snap
```

#### Docker Not Running
```bash
# Start Docker
sudo systemctl start docker       # Linux
# Or start Docker Desktop         # macOS/Windows

# Verify Docker
docker --version
docker run hello-world

# Check Docker daemon status
sudo systemctl status docker      # Linux
```

#### Permission Denied
```bash
# Make scripts executable
chmod +x tools/testing/*.sh
chmod +x tools/testing/scripts/*.sh

# Fix Docker permissions (Linux)
sudo usermod -aG docker $USER
newgrp docker  # Apply group changes without logout

# Verify Docker access
docker ps
```

#### Container Build Failures
```bash
# Clean Docker cache
docker system prune -a

# Clean specific images
docker rmi $(docker images -q)

# Rebuild without cache
docker-compose -f tools/testing/docker-compose.test.yml build --no-cache

# Check build context
du -sh . # Ensure build context isn't too large
```

#### Port Conflicts
```bash
# Check port usage
lsof -i :5433    # PostgreSQL test
lsof -i :6380    # Redis test
lsof -i :5000    # Registry
lsof -i :8090    # WireMock

# Check all listening ports
netstat -tulpn | grep LISTEN

# Kill conflicting processes
sudo kill -9 $(lsof -t -i :5433)

# Alternative: Use different ports in test.env
echo "POSTGRES_PORT=5434" >> tools/testing/test.env
echo "REDIS_PORT=6381" >> tools/testing/test.env
```

### Advanced Troubleshooting

#### Environment Variable Issues
```bash
# Debug environment loading
./tools/testing/mock-env.sh --validate --verbose

# Check specific environment variables
env | grep -E '(GITHUB_|DOCKER_|TEST_)'

# Verify environment file format
cat tools/testing/test.env | head -10

# Test environment variable expansion
echo "GITHUB_REPOSITORY: $GITHUB_REPOSITORY"
echo "REGISTRY: $REGISTRY"
```

#### GitHub Actions Simulation Problems
```bash
# Debug act execution
act push -v --dryrun

# Check workflow syntax
act -l  # List available workflows and jobs

# Test with specific event
act push -e tools/testing/events/push-force-build.json -v

# Use different runner image
act push --platform ubuntu-latest=node:16-buster-slim
```

#### Docker Compose Test Infrastructure Issues
```bash
# Check service dependencies
docker-compose -f tools/testing/docker-compose.test.yml config

# Start services individually
docker-compose -f tools/testing/docker-compose.test.yml up postgres-test
docker-compose -f tools/testing/docker-compose.test.yml up redis-test

# Check service logs
docker-compose -f tools/testing/docker-compose.test.yml logs postgres-test
docker-compose -f tools/testing/docker-compose.test.yml logs wiremock

# Test service connectivity
docker-compose -f tools/testing/docker-compose.test.yml exec postgres-test pg_isready
docker-compose -f tools/testing/docker-compose.test.yml exec redis-test redis-cli ping
```

#### Test Script Failures
```bash
# Debug run-tests.sh
./tools/testing/run-tests.sh -v build 2>&1 | tee debug.log

# Check script dependencies
which docker docker-compose act

# Verify test conditions
./tools/testing/scripts/test-conditions.sh all --debug

# Manual workflow simulation
cd tools/testing
act push -e events/push.json --artifact-server-path ./artifacts
```

#### Mock Service Issues
```bash
# Check WireMock setup
curl http://localhost:8090/__admin/mappings

# Reset mock services
curl -X POST http://localhost:8090/__admin/reset

# Check mock service logs
docker-compose -f tools/testing/docker-compose.test.yml logs wiremock

# Validate mock configurations
cat tools/testing/test-environment/mock-services/mappings/*.json
```

#### Resource Constraints
```bash
# Check system resources
free -h
df -h
docker system df

# Clean up test resources
./tools/testing/run-tests.sh --cleanup
docker system prune -f

# Monitor resource usage during tests
top -p $(pgrep -f run-tests.sh)
```

### Application-Specific Troubleshooting

#### Shopify App Testing Issues
```bash
# Check Node.js version
node --version
npm --version

# Debug package installation
cd applications/app.pxy6.com/src
npm install --verbose

# Test Prisma connection
npx prisma migrate status
npx prisma db pull

# Debug build process
npm run build -- --verbose
```

#### React App Testing Issues
```bash
# Check Vite configuration
cd applications/pxy6.com/src
npm run build -- --mode test

# Debug TypeScript issues
npm run typecheck

# Test production build
npm run preview
```

#### Python App Testing Issues
```bash
# Check Python version
python3 --version
pip --version

# Debug package installation
cd applications/app_1
pip install -r requirements.txt --verbose

# Test database connections
python -c "from src.data.db.connections import get_connection; print('DB OK')"

# Debug API startup
python -m src.api.main --debug
```

### Performance Troubleshooting

#### Slow Test Execution
```bash
# Profile test execution
time ./tools/testing/run-tests.sh build

# Check Docker stats
docker stats --no-stream

# Monitor disk I/O
iostat -x 1 10

# Check network usage
netstat -i
```

#### Memory Issues
```bash
# Check memory usage
free -h
cat /proc/meminfo

# Monitor container memory
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Increase available memory (Docker Desktop)
# Settings > Resources > Advanced > Memory: 4GB+
```

#### Build Cache Issues
```bash
# Clear all caches
docker builder prune -a
npm cache clean --force
pip cache purge

# Check cache usage
docker system df -v

# Disable cache for testing
export DOCKER_BUILDKIT=0
docker build --no-cache -t test-image .
```

### Network Troubleshooting

#### Container Networking
```bash
# List Docker networks
docker network ls

# Inspect test network
docker network inspect test-local_default

# Test container connectivity
docker exec test-container ping postgres-test
docker exec test-container nslookup postgres-test
```

#### DNS Resolution Issues
```bash
# Check DNS in containers
docker exec test-container cat /etc/resolv.conf
docker exec test-container nslookup google.com

# Test external connectivity
docker exec test-container curl -I https://github.com
```

#### Proxy and Registry Issues
```bash
# Test local registry
curl http://localhost:5000/v2/_catalog

# Check registry authentication
docker login localhost:5000

# Debug image push/pull
docker push localhost:5000/test-image:latest -v
docker pull localhost:5000/test-image:latest -v
```

### CI/CD Workflow Specific Issues

#### Workflow Trigger Problems
```bash
# Debug event payloads
cat tools/testing/events/push.json | jq '.'

# Validate event format
act push -e tools/testing/events/push.json --dry-run

# Check workflow conditions
grep -r "if:" .github/workflows/
```

#### Matrix Build Issues
```bash
# Debug application discovery
find applications -name Dockerfile -type f

# Test change detection
git diff --name-only HEAD~1 HEAD | grep -E '^(applications|utilities)/'

# Simulate matrix output
echo '["app.pxy6.com", "pxy6.com"]' | jq '.'
```

#### Secret and Variable Handling
```bash
# Check secret availability in workflow
act push -s GITHUB_TOKEN=test-token

# Debug environment variable passing
env | grep -E '(INPUT_|GITHUB_)' | sort

# Validate secret format
echo "test-secret" | base64 -d
```

### Recovery Procedures

#### Complete Test Environment Reset
```bash
# Stop all containers
docker stop $(docker ps -aq)

# Remove all containers
docker rm $(docker ps -aq)

# Remove test networks
docker network prune -f

# Remove test volumes
docker volume prune -f

# Restart test environment
cd tools/testing
./mock-env.sh --cleanup
./mock-env.sh
./run-tests.sh build
```

#### Partial Reset Procedures
```bash
# Reset only databases
docker-compose -f tools/testing/docker-compose.test.yml stop postgres-test redis-test
docker-compose -f tools/testing/docker-compose.test.yml rm -f postgres-test redis-test
docker-compose -f tools/testing/docker-compose.test.yml up -d postgres-test redis-test

# Reset only mock services
docker-compose -f tools/testing/docker-compose.test.yml restart wiremock
curl -X POST http://localhost:8090/__admin/reset
```

### Getting Additional Help

#### Collecting Debug Information
```bash
# System information
uname -a
docker version
act --version

# Test environment state
./tools/testing/mock-env.sh --validate
docker-compose -f tools/testing/docker-compose.test.yml ps

# Recent logs
find tools/testing/logs -name "*.log" -mtime -1 -exec ls -la {} \;
```

#### Reporting Issues
When reporting testing issues, include:

1. **Environment Information**:
   ```bash
   uname -a
   docker version
   act --version
   node --version
   python3 --version
   ```

2. **Error Messages**:
   ```bash
   ./tools/testing/run-tests.sh build 2>&1 | tee error.log
   ```

3. **Configuration**:
   ```bash
   cat tools/testing/test.env | grep -v PASSWORD
   docker-compose -f tools/testing/docker-compose.test.yml config
   ```

4. **Resource Usage**:
   ```bash
   free -h
   df -h
   docker stats --no-stream
   ```

### Debug Mode

Enable debug mode for detailed output:

```bash
# Verbose act execution
act push -v

# Debug workflow execution
./run-tests.sh -v build

# Debug environment setup
./mock-env.sh --validate --verbose
```

### Log Analysis

Analyze test logs for issues:

```bash
# View all logs
ls tools/testing/logs/

# Search for errors
grep -r "ERROR" tools/testing/logs/

# Check specific workflow
less tools/testing/logs/build-push.log
```

## Integration with Development Workflow

### Pre-commit Testing

Add local testing to your pre-commit workflow:

```bash
# Add to .git/hooks/pre-commit
#!/bin/bash
cd tools/testing
./run-tests.sh build
if [ $? -ne 0 ]; then
    echo "Local tests failed. Commit aborted."
    exit 1
fi
```

### CI/CD Validation

Use local testing to validate CI/CD changes:

```bash
# Test workflow changes
./tools/testing/run-tests.sh all

# Test specific scenarios
./tools/testing/scripts/simulate-workflow.sh push-force-build
```

### Development Iteration

Use local testing during development:

```bash
# Quick iteration cycle
./tools/testing/run-tests.sh build
# Make changes
./tools/testing/run-tests.sh build
# Repeat
```

## Related Documentation

- [Release Process](RELEASE_PROCESS.md)
- [Architecture Overview](ARCHITECTURE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Security Best Practices](SECURITY.md)

## Support

For issues with local testing:

1. Check the [troubleshooting section](#troubleshooting-local-testing)
2. Review logs in `tools/testing/logs/`
3. Validate environment with `./mock-env.sh --validate`
4. Check Docker service status
5. Consult the [Act documentation](https://github.com/nektos/act)
6. Review the detailed `tools/testing/README.md`