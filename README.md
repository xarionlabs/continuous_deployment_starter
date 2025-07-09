# Continuous Deployment Starter Kit

A robust, containerized application deployment system with automated CI/CD pipelines for managing multiple services and applications.

## 🚀 Features

- **Automated CI/CD Pipelines**: GitHub Actions workflows for building, testing, and deploying applications
- **Container-First Architecture**: Docker-based deployment with support for multiple environments
- **Service Discovery**: Built-in support for common services (PostgreSQL, Nginx, etc.)
- **Version Management**: Automated version tagging and release management
- **Testing Framework**: Integrated unit, integration, and end-to-end testing
- **Environment Management**: Support for multiple deployment environments (development, staging, production)

## 📁 Project Structure

```
.
├── .github/                          # GitHub Actions workflows and scripts
│   └── workflows/
│       ├── build.yml                 # Build and test applications
│       ├── release.yml               # Deploy services to environments
│       ├── e2e-tests.yml            # End-to-end testing workflow
│       └── scripts/                  # GitHub Actions utility scripts
│           ├── determine_affected_services.sh
│           ├── generate_quadlets.sh
│           └── ...                   # Other deployment scripts
├── applications/                     # Application source code and containers
│   ├── app.pxy6.com/                # Shopify app (Remix + TypeScript)
│   │   ├── Dockerfile
│   │   ├── docker-compose.yaml
│   │   ├── entrypoints/             # Container entry points
│   │   └── src/                     # Application source code
│   ├── pxy6.com/                    # Frontend web app (React + Vite)
│   │   ├── Dockerfile
│   │   ├── docker-compose.yaml
│   │   ├── entrypoints/
│   │   └── src/
│   ├── app_1/                       # Backend API (Python + FastAPI)
│   │   ├── skipped-Dockerfile       # Currently not built
│   │   ├── docker-compose.yaml
│   │   ├── entrypoints/
│   │   └── src/
│   └── airflow_dags/                # Airflow DAGs (deployed to Airflow service)
│       ├── dags/
│       ├── requirements.txt
│       └── tests/
├── services/                        # Service configurations (numbered for startup order)
│   ├── 01_postgres/                 # PostgreSQL database
│   │   └── docker-compose.yml
│   ├── 02_app_1/                    # Backend API service
│   │   └── skipped-docker-compose.yml
│   ├── 03_nginx-proxy/              # Reverse proxy
│   │   └── docker-compose.yml
│   ├── 04_app_pxy6_com/             # Shopify app service
│   │   └── docker-compose.yml
│   ├── 05_pxy6_web/                 # Frontend web service
│   │   ├── docker-compose.yml
│   │   └── pxy6_web_nginx.conf
│   ├── 06_airflow/                  # Airflow orchestration
│   │   ├── docker-compose.yml
│   │   ├── webserver_config.py
│   │   └── configure-db-entrypoint.sh
│   └── example.version.env          # Version environment template
├── tools/                         # Development and deployment utilities
│   ├── deployment/                # Custom deployment tooling (formerly release-tooling/)
│   │   ├── deployment-manager/    # Python-based release utility
│   │   ├── scripts/               # Deployment bash scripts  
│   │   └── tests_e2e_orchestrator/ # E2E tests for deployment
│   ├── automation/                # GitHub workflow utilities (formerly utilities/github-automation/)
│   │   ├── see_workflow_logs.sh   # Check workflow status
│   │   └── parse_workflow_logs.py # Parse workflow output
│   ├── development/               # Development tools
│   │   └── test-docker-builds.sh  # Docker build testing
│   ├── user-management/           # User management utility (formerly utilities/user_management/)
│   │   ├── Dockerfile
│   │   └── src/manage_users.py
│   ├── git-hooks/                 # Git hooks and utilities
│   │   ├── install-hooks.sh       # Install Git hooks
│   │   └── pre-commit             # Pre-commit hook
│   └── testing/                   # Local CI/CD testing framework
│       ├── run-tests.sh           # Main testing script
│       ├── mock-env.sh            # Environment setup
│       └── ...                    # Testing utilities
├── docs/                          # Comprehensive documentation
│   ├── ARCHITECTURE.md            # System design and components
│   ├── RELEASE_PROCESS.md         # Deployment workflow guide
│   ├── LOCAL_TESTING.md           # Local development and testing
│   ├── SECURITY.md                # Security best practices
│   └── TROUBLESHOOTING.md         # Issue resolution guide
└── CLAUDE.md                      # Claude Code assistant instructions
```

## 🛠️ Getting Started

### Prerequisites

- **Docker and Docker Compose**: Container runtime and orchestration
- **GitHub account**: For CI/CD workflows and container registry
- **Git**: Version control system
- **Node.js 18+**: For frontend applications (local development)
- **Python 3.9+**: For backend applications and tooling
- **(Optional) Act**: For local GitHub Actions testing
- **(Optional) Podman**: For rootless container execution in production

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/continuous_deployment_starter.git
   cd continuous_deployment_starter
   ```

2. **Install Git hooks (recommended)**
   ```bash
   ./tools/git-hooks/install-hooks.sh
   ```

3. **Set up environment variables**
   ```bash
   # Copy example environment files
   cp applications/app.pxy6.com/example.env applications/app.pxy6.com/.env
   cp applications/pxy6.com/src/.env.example applications/pxy6.com/src/.env
   
   # Edit the .env files with your configuration
   # See each application's README for specific requirements
   ```

4. **Test locally before deploying**
   ```bash
   # Test the CI/CD workflows locally
   cd tools/testing
   ./mock-env.sh
   ./run-tests.sh build
   ```

5. **Build and run individual applications**
   ```bash
   # Shopify app
   docker-compose -f applications/app.pxy6.com/docker-compose.yaml up --build
   
   # Frontend web app
   docker-compose -f applications/pxy6.com/docker-compose.yaml up --build
   
   # Or test all Docker builds
   ./tools/test-docker-builds.sh
   ```

### Application-Specific Setup

#### Shopify App (app.pxy6.com)
```bash
cd applications/app.pxy6.com/src
npm install
npm run setup  # Generate Prisma client and run migrations
npm run dev     # Start development server
```

#### Frontend Web App (pxy6.com)
```bash
cd applications/pxy6.com/src
npm install
npm run dev     # Start development server
```

#### Backend API (app_1)
```bash
cd applications/app_1
pip install -r requirements.txt
python -m src.api.main  # Start FastAPI server
```

### Deployment Setup

1. **Configure GitHub Secrets** (see [Security Guide](docs/SECURITY.md))
   - `GITHUB_TOKEN`: For container registry access
   - `HOST`: Deployment server hostname
   - `USERNAME`: Deployment server username
   - `KEY`: SSH private key for deployment server
   - Application-specific secrets (database URLs, API keys, etc.)

2. **Configure GitHub Variables**
   - `REGISTRY`: Container registry URL (default: ghcr.io)
   - Environment-specific configuration values

3. **Set up deployment server** (see [Architecture Guide](docs/ARCHITECTURE.md))
   - Install Podman and systemd
   - Configure rootless containers
   - Set up deployment user and SSH access

## 🔄 CI/CD Pipeline

The system implements a comprehensive CI/CD pipeline with automated building, testing, and deployment.

### Workflow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONTINUOUS DEPLOYMENT FLOW                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Developer Push to Main Branch                                           │
│     │                                                                       │
│     ▼                                                                       │
│  2. Build Workflow (.github/workflows/build.yml)                           │
│     ├─ Skip Check (commit message tags: [skip-build], [force-build], etc.) │
│     ├─ Find Changed Applications (scan applications/, tools/, etc.)     │
│     ├─ Build Docker Images (parallel matrix build)                         │
│     ├─ Run Tests (entrypoint_test.sh)                                       │
│     ├─ Push to GHCR (latest + timestamp tags)                              │
│     └─ Update Release Branch                                                │
│     │                                                                       │
│     ▼                                                                       │
│  3. Release Workflow (.github/workflows/release.yml)                       │
│     ├─ STAGING DEPLOYMENT                                                   │
│     │  ├─ Determine Changed Services (git diff analysis)                    │
│     │  ├─ SSH to Staging Server                                             │
│     │  └─ Execute deploy_on_host.sh                                         │
│     │     ├─ Setup Environment (secrets, variables)                         │
│     │     ├─ Generate Systemd Units (Python release tool)                  │
│     │     ├─ Pull Latest Images                                             │
│     │     ├─ Restart Services                                               │
│     │     └─ Health Checks                                                  │
│     │                                                                       │
│     ▼                                                                       │
│  4. E2E Tests (.github/workflows/e2e-tests.yml)                           │
│     ├─ Run Application E2E Tests (staging environment)                     │
│     ├─ Validate Deployment Success                                          │
│     └─ Check Service Integration                                            │
│     │                                                                       │
│     ▼                                                                       │
│  5. PRODUCTION DEPLOYMENT (on staging success)                             │
│     ├─ Same Process as Staging                                              │
│     ├─ Deploy to Production Environment                                     │
│     └─ Final Production E2E Tests                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Workflows

#### 1. Build Workflow (`build.yml`)
- **Triggers**: Push to `main`, manual dispatch, PR events
- **Features**:
  - Intelligent change detection for selective building
  - Commit message tag support for deployment control
  - Parallel matrix builds for multiple applications
  - Container image signing and attestation
  - Automatic version tagging

#### 2. Release Workflow (`release.yml`)
- **Features**:
  - Multi-environment deployment (staging → production)
  - Service dependency analysis and selective deployment
  - SSH-based remote deployment with secure parameter passing
  - Health checks and rollback on failure

#### 3. E2E Testing Workflow (`e2e-tests.yml`)
- **Features**:
  - Automated testing between deployment stages
  - Application-specific test suites
  - Integration validation
  - Deployment gate for production

### Commit Message Tags

Control deployment behavior with commit message tags:

```bash
# Skip entire build and deployment
git commit -m "Update documentation [skip-build]"

# Force build all applications
git commit -m "Update dependencies [force-build]"

# Skip builds, deploy with latest images
git commit -m "Update configuration [release-only]"

# Deploy specific services only
git commit -m "Update app config [deploy-services: 04_app_pxy6_com,05_pxy6_web]"

# Deploy all services
git commit -m "Infrastructure update [deploy-services: all]"
```

### Deployment Architecture

The deployment process uses a multi-layered approach:

1. **GitHub Actions**: Orchestration and environment management
2. **SSH Deployment**: Secure remote execution
3. **Bash Orchestrator**: Host-level script coordination (`deploy_on_host.sh`)
4. **Python Release Tool**: Core deployment logic (containerized)
5. **Systemd + Podman**: Service management and container runtime

## 🏗️ Applications

The system includes several types of applications, each following standardized patterns:

### Application Types

#### Shopify App (app.pxy6.com)
- **Technology**: Remix, TypeScript, Prisma ORM, Polaris UI
- **Purpose**: Shopify admin app with OAuth integration
- **Database**: PostgreSQL with Prisma migrations
- **Testing**: Jest unit tests, TypeScript type checking

#### Frontend Web App (pxy6.com)
- **Technology**: React, Vite, TypeScript, Tailwind CSS, shadcn/ui
- **Purpose**: Customer-facing web application
- **Features**: Analytics tracking, responsive design, performance optimization
- **Testing**: Jest unit tests, Playwright e2e tests

#### Backend API (app_1)
- **Technology**: Python, FastAPI, Streamlit, SQLAlchemy
- **Purpose**: Backend API and admin dashboard
- **Database**: PostgreSQL with Alembic migrations
- **Status**: Currently has `skipped-Dockerfile` (not built in CI/CD)

#### Airflow DAGs (airflow_dags)
- **Technology**: Python, Apache Airflow
- **Purpose**: Data orchestration and Shopify integration
- **Deployment**: Packaged and deployed to Airflow service

### Standard Application Structure

```
applications/app_name/
├── Dockerfile                   # Container definition
├── docker-compose.yaml          # Local development setup
├── entrypoints/                 # Container entry points
│   ├── entrypoint.sh           # Main application entry point
│   ├── entrypoint_test.sh      # Test execution entry point
│   ├── entrypoint_e2e.sh       # End-to-end test entry point
│   └── entrypoint_migrate_db.sh # Database migration entry point
├── src/                        # Application source code
├── test/                       # Unit and integration tests
├── e2e_tests/                  # End-to-end tests
├── example.env                 # Environment variable template
└── README.md                   # Application-specific documentation
```

## 🌐 Infrastructure Services

Services are organized with numbered prefixes for startup order:

- **01_postgres/**: PostgreSQL database with connection pooling
- **02_app_1/**: Backend API service (currently skipped)
- **03_nginx-proxy/**: Reverse proxy with SSL termination
- **04_app_pxy6_com/**: Shopify app service
- **05_pxy6_web/**: Frontend web service with Nginx
- **06_airflow/**: Workflow orchestration with webserver and scheduler

## 🔒 Security

- **Rootless Containers**: Podman for enhanced security
- **Secrets Management**: GitHub Secrets and Podman secrets
- **Image Security**: Vulnerability scanning and signed attestations
- **Network Security**: Internal Docker networks and SSL/TLS termination
- **Access Control**: SSH key authentication and environment isolation

## 📈 Monitoring and Observability

- **Container Logs**: Systemd journal integration
- **Health Checks**: Application-specific health endpoints
- **Deployment Monitoring**: GitHub Actions workflow logs
- **Service Metrics**: Podman stats and systemd status
- **Error Tracking**: Structured logging with JSON format

## 🧪 Testing

### Local Testing Framework
The `test-local/` directory provides comprehensive local testing:

```bash
# Test CI/CD workflows locally
cd test-local
./mock-env.sh
./run-tests.sh build

# Test specific scenarios
./scripts/simulate-workflow.sh push-force-build
./scripts/test-conditions.sh all
```

### Testing Levels
- **Unit Tests**: Jest (JavaScript/TypeScript), pytest (Python)
- **Integration Tests**: Application-specific test suites
- **End-to-End Tests**: Playwright, containerized testing
- **Deployment Tests**: Local workflow simulation with Act

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

### Core Documentation
- **[Architecture Overview](docs/ARCHITECTURE.md)**: System design, components, and data flow
- **[Release Process](docs/RELEASE_PROCESS.md)**: Detailed deployment workflow and processes
- **[Local Testing Guide](docs/LOCAL_TESTING.md)**: Local development and testing framework
- **[Security Best Practices](docs/SECURITY.md)**: Security guidelines and procedures
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)**: Common issues and solutions

### Additional Resources
- **[CLAUDE.md](CLAUDE.md)**: Claude Code assistant instructions
- **[DEPLOYMENT.md](DEPLOYMENT.md)**: Deployment-specific documentation
- **[test-local/README.md](test-local/README.md)**: Detailed local testing documentation

### Quick Reference
- **Commands**: See [CLAUDE.md](CLAUDE.md) for comprehensive command reference
- **Commit Tags**: Use `[skip-build]`, `[force-build]`, `[release-only]`, `[deploy-services: ...]`
- **Local Testing**: `cd test-local && ./run-tests.sh build`
- **Health Checks**: `./tools/github-automation/see_workflow_logs.sh`

## 🚀 Key Features

- **🔄 Automated CI/CD**: GitHub Actions with intelligent change detection
- **🐳 Container-First**: Docker development, Podman production deployment
- **🔒 Security-Focused**: Rootless containers, secrets management, vulnerability scanning
- **🧪 Comprehensive Testing**: Unit, integration, E2E, and local workflow testing
- **📊 Multi-Environment**: Staging and production deployment with health checks
- **🎯 Selective Deployment**: Deploy only changed services for efficiency
- **📈 Monitoring**: Built-in logging, health checks, and deployment validation
- **🛠️ Developer-Friendly**: Local testing framework and detailed documentation

## 🤝 Contributing

1. **Fork the repository**
2. **Install Git hooks**: `./scripts/install-hooks.sh`
3. **Test locally**: `cd test-local && ./run-tests.sh build`
4. **Create a feature branch**: `git checkout -b feature/amazing-feature`
5. **Commit your changes**: `git commit -m 'Add some amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Development Workflow
- Use appropriate commit message tags for deployment control
- Test changes locally before pushing
- Follow the security guidelines in [docs/SECURITY.md](docs/SECURITY.md)
- Update documentation when adding new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📬 Support

For questions, issues, or support:

1. **Check the documentation**: Start with [docs/](docs/) directory
2. **Search existing issues**: GitHub Issues for known problems
3. **Local testing**: Use `test-local/` framework to validate setup
4. **Create an issue**: Provide detailed information and logs
5. **Security issues**: Follow the security policy in [docs/SECURITY.md](docs/SECURITY.md)

### Useful Commands for Support
```bash
# Check system status
./tools/github-automation/see_workflow_logs.sh

# Test locally
cd test-local && ./run-tests.sh -v build

# Collect system information
uname -a && docker --version && git --version
```
