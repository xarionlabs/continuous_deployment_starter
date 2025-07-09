# Release Process Documentation

## Overview

This document provides a comprehensive guide to the release process for the continuous deployment system. The release process is designed to be automated, safe, and capable of handling multiple applications and services efficiently.

## Release Architecture

The release system consists of several interconnected components:

1. **GitHub Actions Workflows**: Build, test, and orchestrate deployments
2. **Container Registry**: Stores versioned Docker images (GitHub Container Registry)
3. **Python Release Tool**: Manages service deployments and systemd unit generation
4. **Remote Host Orchestration**: Manages deployment on target servers
5. **Local Testing Framework**: Allows testing workflows before production deployment

## Release Workflow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONTINUOUS DEPLOYMENT FLOW                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Code Push/PR Merge                                                      │
│     │                                                                       │
│     ▼                                                                       │
│  2. Build Workflow (.github/workflows/build.yml)                           │
│     ├─ Skip Check (commit message tags)                                     │
│     ├─ Find Changed Applications                                            │
│     ├─ Build Docker Images                                                  │
│     ├─ Run Tests                                                            │
│     ├─ Push to GHCR                                                         │
│     └─ Update Release Branch                                                │
│     │                                                                       │
│     ▼                                                                       │
│  3. Release Workflow (.github/workflows/release.yml)                       │
│     ├─ STAGING DEPLOYMENT                                                   │
│     │  ├─ Determine Changed Services                                        │
│     │  ├─ SSH to Staging Server                                             │
│     │  └─ Execute deploy_on_host.sh                                         │
│     │     ├─ Pull Latest Images                                             │
│     │     ├─ Generate systemd Units                                         │
│     │     ├─ Restart Services                                               │
│     │     └─ Health Checks                                                  │
│     │                                                                       │
│     ▼                                                                       │
│  4. E2E Tests (.github/workflows/e2e-tests.yml)                           │
│     ├─ Run Application E2E Tests                                           │
│     └─ Validate Deployment                                                  │
│     │                                                                       │
│     ▼                                                                       │
│  5. PRODUCTION DEPLOYMENT                                                   │
│     ├─ Same as Staging Process                                              │
│     └─ Final Production E2E Tests                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Detailed Workflow Steps

### 1. Build Workflow (build.yml)

The build workflow is triggered on:
- Push to `main` branch
- Manual workflow dispatch
- Pull request events

#### Key Steps:

1. **Skip Check**: Analyzes commit messages for control tags:
   - `[skip-build]`: Skips entire workflow
   - `[force-build]`: Forces build of all applications
   - `[release-only]`: Skips builds, proceeds with releases using latest images
   - `[deploy-services: service1,service2]`: Deploys only specified services
   - `[deploy-services: all]`: Deploys all services

2. **Find Changed Applications**: 
   - Scans `applications/`, `utilities/`, and `tools/deployment/` directories
   - Identifies changed files and maps them to buildable applications
   - Outputs a JSON array of applications to build

3. **Build Applications**:
   - Builds Docker images for changed applications
   - Runs tests using `entrypoint_test.sh`
   - Pushes images to GitHub Container Registry with tags:
     - `latest`: Always updated
     - `YYYYMMDD-HHMMSS`: Timestamp-based version tag

4. **Tag Creation**: Creates git tags for successful builds

5. **Release Branch Update**: Updates the `releases` branch with:
   - Latest code changes
   - Updated `services/version.env` file

### 2. Release Workflow (release.yml)

The release workflow is called by the build workflow and handles actual deployments.

#### Environment-Specific Deployments:

1. **Staging Deployment**:
   - Determines changed services using git diff
   - Executes remote deployment via SSH
   - Runs `deploy_on_host.sh` on staging server

2. **Production Deployment**:
   - Only proceeds if staging deployment and E2E tests pass
   - Uses same process as staging
   - Deploys to production environment

#### Key Components:

1. **Change Detection**:
   ```bash
   # Compares current release branch with previous commit
   git diff --name-only $PREVIOUS_COMMIT HEAD
   ```

2. **Service Determination**:
   - Uses `determine_affected_services.sh` to map changed files to services
   - Considers service dependencies
   - Handles special cases (manual triggers, environment changes)

3. **Remote Execution**:
   - Uses SSH action to connect to deployment servers
   - Passes environment variables, secrets, and service lists
   - Executes the orchestration script

### 3. Remote Host Orchestration (deploy_on_host.sh)

This script runs on the deployment target and orchestrates the entire deployment process.

#### Key Responsibilities:

1. **Environment Setup**:
   - Pulls latest code from repository
   - Updates Podman secrets from GitHub secrets
   - Creates environment files from GitHub variables
   - Validates service configurations

2. **Python Release Tool Execution**:
   - Pulls latest `release-tool` Docker image
   - Executes containerized Python tool for core tasks:
     - `generate-units`: Creates systemd unit files
     - `pull-images`: Downloads container images
     - `manage-services restart`: Restarts services

3. **Host-Level Operations**:
   - Runs systemd validation (`quadlet --dryrun`)
   - Performs auto-updates (`podman auto-update`)
   - Manages systemd targets and dependencies

### 4. Python Release Tool

The containerized Python tool (`tools/deployment/deployment-manager/`) handles the core deployment logic:

#### Commands:

1. **`determine-changes`**:
   - Analyzes changed files to determine affected services
   - Considers service dependencies and configurations
   - Outputs list of services requiring updates

2. **`generate-units`**:
   - Converts Docker Compose files to systemd Quadlet units
   - Handles environment variables, volumes, networks
   - Creates service dependencies and targets

3. **`pull-images`**:
   - Pulls required container images using Podman
   - Handles authentication and registry connections
   - Optimizes image pulling for affected services only

4. **`manage-services`**:
   - Restarts affected services and their dependents
   - Performs health checks on restarted services
   - Manages systemd service states

### 5. E2E Testing (e2e-tests.yml)

End-to-end testing validates deployments in each environment:

1. **Application Discovery**:
   - Finds applications with `entrypoint_e2e.sh` files
   - Loads version information from `services/version.env`

2. **Test Execution**:
   - Runs E2E tests using deployed application images
   - Uses environment-specific configurations
   - Validates application functionality

3. **Validation**:
   - Ensures all applications are accessible
   - Validates integration between services
   - Confirms environment-specific configurations

## Commit Message Tags

The system supports several commit message tags to control deployment behavior:

### `[skip-build]`
Skips the entire build and deployment process.

**Use Cases**:
- Documentation updates
- README changes
- Configuration file updates that don't affect runtime

**Examples**:
```bash
git commit -m "Update documentation [skip-build]"
git commit -m "Fix typos in README [skip-build]"
git commit -m "Update GitHub Actions workflow comments [skip-build]"
```

### `[force-build]`
Forces building of all applications regardless of changes.

**Use Cases**:
- Dependency updates affecting all applications
- Base image updates
- Security patches requiring full rebuild

**Examples**:
```bash
git commit -m "Update Node.js to latest LTS [force-build]"
git commit -m "Security patch for base images [force-build]"
git commit -m "Update shared dependencies [force-build]"
```

**Example Output**:
```
Applications to build: ["app.pxy6.com", "pxy6.com", "airflow_dags", "release-tool"]
Force build enabled - building all applications
```

### `[release-only]`
Skips builds but proceeds with releases using the latest available images.

**Use Cases**:
- Configuration changes in services/ directory
- Environment variable updates
- Infrastructure configuration changes

**Examples**:
```bash
git commit -m "Update production database URL [release-only]"
git commit -m "Increase container resource limits [release-only]"
git commit -m "Update nginx configuration [release-only]"
```

**Important Notes**:
- Ensure latest images are available in registry
- Use for changes that don't require code rebuilds
- Always test configuration changes in staging first

### `[deploy-services: service1,service2]`
Deploys only the specified services.

**Use Cases**:
- Targeted deployments for specific applications
- Rolling updates for individual services
- Quick fixes for specific components

**Examples**:
```bash
# Deploy only Shopify app and web frontend
git commit -m "Update app configuration [deploy-services: 04_app_pxy6_com,05_pxy6_web]"

# Deploy only database service
git commit -m "Update PostgreSQL configuration [deploy-services: 01_postgres]"

# Deploy only proxy configuration
git commit -m "Update nginx SSL certificates [deploy-services: 03_nginx-proxy]"
```

**Service Name Reference**:
- `01_postgres`: PostgreSQL database
- `02_app_1`: Backend API (if enabled)
- `03_nginx-proxy`: Reverse proxy
- `04_app_pxy6_com`: Shopify application
- `05_pxy6_web`: Frontend web application
- `06_airflow`: Airflow orchestration

### `[deploy-services: all]`
Forces deployment of all services.

**Use Cases**:
- Infrastructure-wide changes
- Major version updates
- Emergency deployments

**Examples**:
```bash
git commit -m "Infrastructure update [deploy-services: all]"
git commit -m "Critical security patch [deploy-services: all]"
git commit -m "Environment variable updates [deploy-services: all]"
```

### Advanced Tag Combinations

You can combine tags for complex deployment scenarios:

```bash
# Force build all applications and deploy all services
git commit -m "Major update with new features [force-build] [deploy-services: all]"

# Skip build but deploy specific services (useful for config-only changes)
git commit -m "Update app config [skip-build] [deploy-services: 04_app_pxy6_com]"
```

### Tag Parsing Examples

The system parses commit messages to extract tags:

```bash
# Valid tag formats
"Update feature [force-build]"
"Fix bug [deploy-services: 04_app_pxy6_com,05_pxy6_web]"
"Documentation update [skip-build]"

# Invalid formats (will be ignored)
"Update feature [force build]"    # No hyphen
"Fix bug [deploy-services:app1]"  # No space after colon
"Doc update [SKIP-BUILD]"         # Case sensitive
```

## Version Management

The system uses timestamp-based versioning:

### Version Format
- Format: `YYYYMMDD-HHMMSS`
- Example: `20240315-143022`
- Timezone: Europe/Amsterdam

### Version Storage
- Git tags: Created for each successful build
- `services/version.env`: Contains current deployed version
- Container tags: Both `latest` and timestamp tags

### Version Propagation
1. Build workflow creates timestamp tag
2. Updates `services/version.env` in releases branch
3. E2E tests use version from `services/version.env`
4. Deployment uses specific version tags

## Service Discovery and Dependencies

### Service Structure
Services are organized in the `services/` directory:
```
services/
├── 01_postgres/          # Database service
├── 02_app_1/            # Application service
├── 03_nginx-proxy/      # Reverse proxy
├── 04_app_pxy6_com/     # Shopify app
├── 05_pxy6_web/         # Web frontend
└── 06_airflow/          # Airflow orchestration
```

### Dependency Management
- Services are numbered for startup order
- Dependencies are managed through systemd targets
- The Python tool automatically handles dependency chains

### Service Detection
The system automatically detects affected services by:
1. Mapping changed files to service directories
2. Analyzing Docker Compose configurations
3. Considering service dependencies
4. Handling cross-service impacts

## Environment Management

### Supported Environments
- **Staging**: Pre-production testing environment
- **Production/Live**: Production environment

### Environment Configuration
- GitHub Actions environments define deployment targets
- Environment-specific variables and secrets
- Different deployment servers for each environment

### Environment Variables
- **GitHub Variables**: Public configuration values
- **GitHub Secrets**: Sensitive configuration values
- **Service-specific**: Defined in service Docker Compose files

## Security Considerations

### Access Control
- SSH key-based authentication for deployment servers
- GitHub Actions environments require approval for production
- Secrets are encrypted and only accessible during deployment

### Container Security
- Images are signed with attestations
- Vulnerability scanning in CI/CD pipeline
- Rootless container execution with Podman

### Network Security
- Services communicate through internal Docker networks
- External access controlled through Nginx reverse proxy
- SSL/TLS termination at proxy level

## Rollback Procedures

### Automatic Rollback
- Failed deployments automatically stop the pipeline
- Services remain in their previous state if deployment fails
- Health checks prevent unhealthy services from receiving traffic

### Manual Rollback

#### Step-by-Step Rollback Process

1. **Identify the previous successful version**:
   ```bash
   # List recent tags sorted by version
   git tag --sort=-version:refname | head -10
   
   # Example output:
   # 20240315-143022
   # 20240315-120045
   # 20240314-183012
   # 20240314-165522
   ```

2. **Check the target version details**:
   ```bash
   # View commit details for the target version
   git show 20240315-120045
   
   # Check what was changed in that version
   git diff 20240315-120045^ 20240315-120045 --name-only
   ```

3. **Update version and trigger rollback**:
   ```bash
   # Method 1: Update version.env (recommended)
   echo "APP_VERSION=20240315-120045" > services/version.env
   git add services/version.env
   git commit -m "Rollback to version 20240315-120045 [deploy-services: all]"
   git push origin main
   
   # Method 2: Selective service rollback
   git commit -m "Rollback Shopify app [deploy-services: 04_app_pxy6_com]"
   ```

4. **Monitor rollback deployment**:
   ```bash
   # Watch GitHub Actions workflow
   gh run watch
   
   # Check deployment logs
   ./utilities/github-automation/see_workflow_logs.sh
   ```

5. **Validate functionality**:
   ```bash
   # Check service health endpoints
   curl -f https://staging.example.com/health
   curl -f https://app.staging.example.com/api/health
   
   # Run E2E tests
   cd test-local
   ./run-tests.sh -e staging e2e
   ```

### Emergency Rollback

For critical production issues requiring immediate action:

#### Quick SSH Rollback (Emergency)

1. **SSH to deployment server**:
   ```bash
   ssh deployment-user@production-server
   ```

2. **Stop affected services**:
   ```bash
   # Stop specific service
   systemctl --user stop app-pxy6-com
   systemctl --user stop pxy6-web
   
   # Or stop all services
   systemctl --user stop all-containers.target
   ```

3. **Manually restart with previous images**:
   ```bash
   # Check available images
   podman images | grep ghcr.io/org/repo
   
   # Start with previous image tag
   podman run -d --name app-pxy6-com-emergency \
     ghcr.io/org/repo/app.pxy6.com:20240315-120045
   
   # Or regenerate services with previous version
   export APP_VERSION=20240315-120045
   ./tools/deployment/scripts/deploy_on_host.sh "04_app_pxy6_com" "{}" "{}"
   ```

4. **Verify emergency rollback**:
   ```bash
   # Check service status
   systemctl --user status app-pxy6-com
   podman ps
   
   # Test application
   curl -f http://localhost:8080/health
   ```

5. **Follow up with proper rollback**:
   ```bash
   # Update git repository to reflect emergency rollback
   echo "APP_VERSION=20240315-120045" > services/version.env
   git commit -m "Emergency rollback to 20240315-120045 [skip-build]"
   git push origin main
   ```

#### Service-Specific Emergency Procedures

**Database Emergency Rollback**:
```bash
# Stop database connections
systemctl --user stop app-pxy6-com pxy6-web

# Restore database backup (if needed)
pg_dump -h localhost -U postgres appdb > emergency_backup.sql
dropdb appdb
createdb appdb
psql appdb < backup_20240315_120045.sql

# Restart services
systemctl --user start postgres
systemctl --user start app-pxy6-com pxy6-web
```

**Proxy Emergency Rollback**:
```bash
# Restore previous nginx configuration
cp /opt/deployment/backups/nginx_20240315_120045.conf /opt/deployment/nginx/nginx.conf

# Restart nginx
systemctl --user restart nginx-proxy

# Test proxy
curl -I https://example.com
```

#### Rollback Validation Checklist

After any rollback procedure:

- [ ] All services are running and healthy
- [ ] Application endpoints respond correctly
- [ ] Database connections are working
- [ ] User authentication is functional
- [ ] Critical business functions are operational
- [ ] Monitoring and logging are active
- [ ] Version tracking is updated in git repository

## Monitoring and Observability

### Deployment Monitoring
- GitHub Actions provide build and deployment logs
- Service health checks during deployment
- Automated E2E test validation

### Application Monitoring
- Container logs accessible via `journalctl`
- Service status via `systemctl --user status`
- Health endpoints for application monitoring

### Alerting
- Failed deployments trigger GitHub Actions notifications
- Service failures logged in systemd journal
- E2E test failures block production deployments

## Troubleshooting Common Issues

### Build Failures
1. Check application tests: `docker run --entrypoint=/app/entrypoints/entrypoint_test.sh IMAGE`
2. Verify Dockerfile syntax and dependencies
3. Check for missing environment variables

### Deployment Failures
1. Check SSH connectivity to deployment server
2. Verify service configurations in Docker Compose files
3. Check systemd unit file generation
4. Validate environment variables and secrets

### Service Startup Issues
1. Check service logs: `journalctl --user -u service-name`
2. Verify image availability and versions
3. Check service dependencies and startup order
4. Validate port conflicts and network configurations

## Best Practices

### Development Workflow
1. Test changes locally using `tools/testing/` framework
2. Use appropriate commit message tags
3. Monitor build and deployment logs
4. Validate deployments with E2E tests

### Service Management
1. Follow semantic versioning for major changes
2. Use health checks in all services
3. Implement graceful shutdown procedures
4. Monitor resource usage and performance

### Security Practices
1. Regularly rotate SSH keys and secrets
2. Use least-privilege access principles
3. Keep dependencies updated
4. Implement proper logging and monitoring

## Related Documentation

- [Local Testing Guide](LOCAL_TESTING.md)
- [Architecture Overview](ARCHITECTURE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Security Best Practices](SECURITY.md)