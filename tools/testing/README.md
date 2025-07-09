# Local CI/CD Testing Environment

This directory provides a comprehensive local testing environment for the CI/CD pipeline, allowing developers to test GitHub Actions workflows locally without pushing to GitHub.

## Quick Start

1. **Install Prerequisites**
   ```bash
   # Install act (GitHub Actions local runner)
   curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
   
   # Or using package managers
   brew install act              # macOS
   # or
   choco install act-cli         # Windows
   # or
   sudo apt install act          # Ubuntu (from GitHub releases)
   ```

2. **Setup Test Environment**
   ```bash
   cd test-local
   ./mock-env.sh                 # Setup mock environment variables
   ```

3. **Run Tests**
   ```bash
   # Test build workflow
   ./run-tests.sh build
   
   # Test all workflows interactively
   ./run-tests.sh -i
   
   # Test specific scenario
   ./scripts/simulate-workflow.sh push-force-build
   ```

## Directory Structure

```
test-local/
├── README.md                   # This documentation
├── docker-compose.test.yml     # Testing infrastructure
├── run-tests.sh               # Main testing script
├── mock-env.sh                # Environment setup script
├── events/                    # GitHub event payloads
│   ├── push.json
│   ├── workflow_dispatch.json
│   ├── push-force-build.json
│   └── ...
├── scripts/                   # Testing utilities
│   ├── simulate-workflow.sh
│   └── test-conditions.sh
├── logs/                      # Test execution logs
├── artifacts/                 # Test artifacts
└── [generated files]          # Environment files (test.env, secrets.env, etc.)
```

## Core Components

### 1. `.actrc` Configuration

The `.actrc` file in the project root provides optimized defaults for act:
- Uses Ubuntu 22.04 for better compatibility
- Sets up default environment variables
- Configures networking and container options
- Points to test event payloads and environment files

### 2. Docker Compose Test Infrastructure

`docker-compose.test.yml` provides:
- **PostgreSQL Test Database**: Isolated database for testing
- **Redis Test Instance**: Caching and session storage
- **Local Container Registry**: For testing image builds
- **Mock Services**: WireMock for external API simulation
- **Test Utilities**: Alpine container with testing tools

### 3. Main Testing Script

`run-tests.sh` is the primary interface for local testing:

```bash
# Basic usage
./run-tests.sh [OPTIONS] [WORKFLOW]

# Examples
./run-tests.sh build                           # Test build workflow
./run-tests.sh -e staging release              # Test release workflow for staging
./run-tests.sh -p integration-test all         # Test with integration test profile
./run-tests.sh -c -v build                     # Test with cleanup and verbose output
./run-tests.sh -i                              # Interactive mode
```

**Options:**
- `-e, --environment`: Environment to test (test, staging, live)
- `-p, --profile`: Docker Compose profile (default, integration-test, mock-services)
- `-c, --cleanup`: Clean up test environment after running
- `-v, --verbose`: Enable verbose output
- `-i, --interactive`: Run in interactive mode
- `-s, --skip-setup`: Skip infrastructure setup

### 4. Environment Setup

`mock-env.sh` creates mock GitHub Actions environment:

```bash
# Setup mock environment
./mock-env.sh

# Export variables to current shell
./mock-env.sh --export

# Validate environment setup
./mock-env.sh --validate

# Clean up mock environment
./mock-env.sh --cleanup
```

Creates three main files:
- `test.env`: GitHub Actions environment variables
- `secrets.env`: Mock secrets for testing
- `variables.env`: Public configuration variables

## Testing Scenarios

### Workflow Event Simulation

Use `scripts/simulate-workflow.sh` to test specific scenarios:

```bash
# Test normal push event
./scripts/simulate-workflow.sh push-normal build

# Test force build scenario
./scripts/simulate-workflow.sh push-force-build

# Test skip build scenario
./scripts/simulate-workflow.sh push-skip-build

# Test selective service deployment
./scripts/simulate-workflow.sh push-deploy-services

# Test release-only mode
./scripts/simulate-workflow.sh push-release-only

# Test manual workflow dispatch
./scripts/simulate-workflow.sh manual-dispatch

# Test scheduled workflow
./scripts/simulate-workflow.sh scheduled-run

# Test staging release
./scripts/simulate-workflow.sh -e staging release-staging

# Test live release
./scripts/simulate-workflow.sh -e live release-live
```

### Condition Testing

Use `scripts/test-conditions.sh` to validate workflow logic:

```bash
# Test commit message tag detection
./scripts/test-conditions.sh commit-tags

# Test file change detection logic
./scripts/test-conditions.sh file-changes

# Test service affection detection
./scripts/test-conditions.sh service-detection

# Test environment variable handling
./scripts/test-conditions.sh environment-vars

# Test error conditions
./scripts/test-conditions.sh error-conditions

# Test build matrix generation
./scripts/test-conditions.sh build-matrix

# Test service dependency ordering
./scripts/test-conditions.sh dependency-order

# Run all tests
./scripts/test-conditions.sh all
```

## Event Payloads

The `events/` directory contains JSON payloads for different GitHub events:

### Standard Events
- `push.json`: Normal push event with file changes
- `workflow_dispatch.json`: Manual workflow dispatch
- `workflow_call.json`: Workflow call event
- `schedule.json`: Scheduled workflow run

### Commit Message Tag Events
- `push-force-build.json`: Push with `[force-build]` tag
- `push-skip-build.json`: Push with `[skip-build]` tag
- `push-deploy-services.json`: Push with `[deploy-services: ...]` tag
- `push-release-only.json`: Push with `[release-only]` tag

## Docker Compose Profiles

### Default Profile
Basic testing infrastructure:
- PostgreSQL test database
- Redis test instance
- Local container registry
- Test utilities

```bash
./run-tests.sh -p default build
```

### Integration Test Profile
Includes test applications for full integration testing:
- All default services
- Test application instances
- Application-specific configurations

```bash
./run-tests.sh -p integration-test all
```

### Mock Services Profile
Includes external service mocking:
- All default services
- WireMock for API simulation
- External service configurations

```bash
./run-tests.sh -p mock-services build
```

## Testing Commit Message Tags

The CI/CD pipeline supports several commit message tags that control workflow behavior:

### Force Build
```bash
git commit -m "Update configuration [force-build]"
```
- Forces building all applications regardless of changes
- Useful for testing complete pipeline

### Skip Build
```bash
git commit -m "Update documentation [skip-build]"
```
- Skips the entire build and release process
- Useful for documentation-only changes

### Deploy Specific Services
```bash
git commit -m "Update apps [deploy-services: 04_app_pxy6_com,05_pxy6_web]"
```
- Deploys only specified services
- Services must match directory names in `services/`

### Deploy All Services
```bash
git commit -m "Update infrastructure [deploy-services: all]"
```
- Forces deployment of all services
- Equivalent to full deployment

### Release Only Mode
```bash
git commit -m "Configuration update [release-only]"
```
- Skips builds but proceeds with releases using latest images
- Useful for configuration-only deployments

## Environment Variables

### GitHub Actions Variables
Automatically set by `mock-env.sh`:
- `GITHUB_REPOSITORY`: Repository name
- `GITHUB_REF`: Git reference
- `GITHUB_SHA`: Commit SHA
- `GITHUB_EVENT_NAME`: Event type
- `GITHUB_ACTOR`: User who triggered the action
- `GITHUB_WORKSPACE`: Workspace directory

### Application Variables
- `DATABASE_URL`: Test database connection
- `REDIS_URL`: Test Redis connection
- `REGISTRY`: Container registry URL
- `APP_ENV`: Application environment (test)
- `NODE_ENV`: Node environment (test)

### Feature Flags
- `FORCE_BUILD`: Force build all applications
- `SKIP_BUILD`: Skip build process
- `RELEASE_ONLY`: Release only mode
- `DEPLOY_SERVICES`: Specific services to deploy

## Testing Infrastructure Services

### PostgreSQL Test Database
- **Host**: `postgres-test`
- **Port**: `5433` (external), `5432` (internal)
- **Database**: `test_db`
- **User**: `test_user`
- **Password**: `test_password`

### Redis Test Instance
- **Host**: `redis-test`
- **Port**: `6380` (external), `6379` (internal)
- **No authentication**

### Local Container Registry
- **URL**: `localhost:5000`
- **API**: `http://localhost:5000/v2/`
- **Used for testing image builds and pushes**

### Mock Services (WireMock)
- **URL**: `http://localhost:8090`
- **Admin**: `http://localhost:8090/__admin`
- **Used for mocking external APIs**

## Troubleshooting

### Common Issues

#### Act Not Found
```bash
# Install act
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

#### Docker Not Running
```bash
# Start Docker service
sudo systemctl start docker    # Linux
# or start Docker Desktop      # macOS/Windows
```

#### Permission Denied
```bash
# Make scripts executable
chmod +x test-local/*.sh
chmod +x test-local/scripts/*.sh
```

#### Container Build Failures
```bash
# Clean Docker cache
docker system prune -a

# Rebuild without cache
docker-compose -f test-local/docker-compose.test.yml build --no-cache
```

#### Port Conflicts
```bash
# Check what's using ports
lsof -i :5433    # PostgreSQL
lsof -i :6380    # Redis
lsof -i :5000    # Registry
lsof -i :8090    # WireMock

# Stop conflicting services or change ports in docker-compose.test.yml
```

### Logs and Debugging

#### View Container Logs
```bash
# All services
docker-compose -f test-local/docker-compose.test.yml logs

# Specific service
docker-compose -f test-local/docker-compose.test.yml logs postgres-test
```

#### View Test Logs
```bash
# Test execution logs
ls test-local/logs/

# View specific log
less test-local/logs/build-push.log
```

#### Debug Act Execution
```bash
# Verbose output
./run-tests.sh -v build

# List available workflows
act -l

# Dry run
act push --dry-run
```

### Environment Issues

#### Check Environment Setup
```bash
# Validate environment
./mock-env.sh --validate

# Show environment summary
./mock-env.sh --summary

# Check specific variables
grep GITHUB test-local/test.env
```

#### Reset Environment
```bash
# Clean up and restart
./mock-env.sh --cleanup
./mock-env.sh
```

## Advanced Usage

### Custom Event Payloads

Create custom event payloads in `events/` directory:

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

### Custom Environment Variables

Modify generated environment files:

```bash
# Edit test environment
nano test-local/test.env

# Add custom variables
echo "CUSTOM_VAR=custom_value" >> test-local/test.env
```

### Integration with CI/CD

Use local testing in development workflow:

```bash
# Before pushing changes
./test-local/run-tests.sh build

# Test specific deployment scenario
./test-local/scripts/simulate-workflow.sh push-deploy-services

# Validate workflow conditions
./test-local/scripts/test-conditions.sh all
```

## Best Practices

### 1. Test Before Push
Always run local tests before pushing changes:
```bash
./test-local/run-tests.sh all
```

### 2. Use Appropriate Profiles
Choose the right testing profile for your needs:
- Use `default` for basic workflow testing
- Use `integration-test` for full application testing
- Use `mock-services` for external dependency testing

### 3. Clean Up Resources
Clean up test resources regularly:
```bash
./test-local/run-tests.sh -c build
docker system prune
```

### 4. Version Control
Don't commit generated files:
```gitignore
test-local/test.env
test-local/secrets.env
test-local/variables.env
test-local/logs/
test-local/artifacts/
```

### 5. Document Custom Scenarios
Document any custom testing scenarios for your team:
```bash
# Add team-specific scenarios to simulate-workflow.sh
# Create team-specific event payloads
# Document environment-specific requirements
```

## Contributing

### Adding New Test Scenarios

1. Create event payload in `events/`
2. Add scenario to `simulate-workflow.sh`
3. Test the scenario
4. Update documentation

### Adding New Conditions

1. Add test case to `test-conditions.sh`
2. Implement validation logic
3. Test edge cases
4. Update documentation

### Improving Infrastructure

1. Update `docker-compose.test.yml`
2. Test with different profiles
3. Validate service interactions
4. Update documentation

## Support

For issues with local testing:
1. Check troubleshooting section
2. Review logs in `test-local/logs/`
3. Validate environment with `mock-env.sh --validate`
4. Check Docker service status
5. Consult act documentation: https://github.com/nektos/act