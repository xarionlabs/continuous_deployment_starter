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

│   └── workflows/
│       ├── build-mock-applications.yml # Builds mock application images for testing
│       ├── build-release-tool.yml    # Builds the Python release-tool image
│       ├── release.yml               # Main release workflow (deploys actual services)
│       ├── test-release-tooling.yml  # Workflow to test the release process itself
│       └── scripts/                  # Other GitHub Actions specific utility scripts (if any)
├── applications/                     # Your actual application Dockerfiles & source
│   └── my-app-1/
│       └── Dockerfile
├── services/                       # Your actual service definitions (docker-compose.yml files)
│   └── my-app-1/
│       └── docker-compose.yml
├── release-tooling/                  # All custom release tooling and its tests
│   ├── pytool/                       # Python-based release utility
│   │   ├── release_tool/             # Python package source for the tool
│   │   ├── tests/                    # Unit tests for the pytool
│   │   ├── pyproject.toml
│   │   ├── Dockerfile                # Dockerfile for the pytool
│   │   └── README.md
│   ├── scripts/                      # Bash scripts used in deployment
│   │   ├── deploy_on_host.sh         # Main orchestrator script for remote host
│   │   ├── refresh_podman_secrets.sh # Example host script
│   │   └── ...                       # Other deployment-related bash scripts
│   ├── tests_e2e_orchestrator/       # Pytest E2E tests for deploy_on_host.sh
│   │   └── test_deploy_orchestrator.py
│   └── release-testing-assets/       # Assets for testing the release tooling itself
│       ├── applications/             # Mock application sources & Dockerfiles
│       │   └── mock-app-alpha/
│       │       ├── Dockerfile
│       │       └── app_source_code/
│       ├── services/                 # Mock service definitions (docker-compose.yml)
│       │   └── mock-app-alpha/
│       │       └── docker-compose.yml
│       └── tests_verification/       # Pytest tests to verify mock deployments
│           └── test_mock_deployments.py
├── tests/                          # Top-level directory for application E2E/integration tests
│                                   # (distinct from release tooling tests)
└── utils/                          # Other general utilities (if any, now excludes deployment utils)


## 🛠️ Getting Started

### Prerequisites

- Docker and Docker Compose
- GitHub account
- (Optional) Podman for rootless container execution

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/continuous_deployment_starter.git
   cd continuous_deployment_starter
   ```

2. **Set up environment variables**
   ```bash
   cp applications/app_1/example.env applications/app_1/.env
   # Edit the .env file with your configuration
   ```

3. **Build and run locally**
   ```bash
   docker-compose -f applications/app_1/docker-compose.yaml up --build
   ```

## 🔄 CI/CD Pipeline

The project includes GitHub Actions workflows for:

1. **Build Workflow** (`build.yml`)
   - Triggered on pushes to `main` or manually
   - Builds and tests changed applications
   - Creates and pushes Docker images to GitHub Container Registry
   - Tags successful builds with timestamps

2. **End-to-End Testing** (`e2e-tests.yml`)
   - Runs after successful builds
   - Verifies application functionality in a test environment

3. **Release Management** (`release.yml`)
   - Manages versioning, release notes, and deploys services to the target environment.
   - Updates the `releases` branch with version information.
   - **Core Deployment Logic**: The deployment process orchestrated by `release.yml` has been significantly enhanced by introducing a containerized Python-based release utility.

   #### Python Release Utility
   Located in `release-tooling/pytool/`, this Python application (built into a Docker image) is now responsible for the core tasks of service deployment:
    - **Selective Processing**: It intelligently determines which services are affected by code changes and processes only those, rather than redeploying everything.
    - **Quadlet Generation**: It dynamically generates systemd unit files (e.g., `.container`, `.service`) for each affected service from its Docker Compose definition found in the `services/` directory. This includes handling environment variables, volume mounts, network configurations, secrets, and dependencies.
    - **Image Pulling**: It selectively pulls the latest container images for affected services.
    - **Service Management**: It restarts the affected services and their dependents using `systemctl --user` commands and performs health checks.

   #### Workflow Overview:
   The `release.yml` workflow orchestrates the deployment through these main stages:
    1.  **Build Release Utility (Conditional)**: A dedicated job, typically defined in `.github/workflows/build-release-tool.yml` and called by `release.yml`, builds the Python `release-tool` Docker image (from `release-tooling/pytool/Dockerfile`) and pushes it to a container registry (e.g., GHCR). This job usually runs only if changes are detected in the `release-tooling/pytool/` directory.
    2.  **Determine Affected Services (GitHub Runner)**: Before deploying, the `release.yml` workflow checks out the main repository and uses `git diff` to identify changed files. The output of `git diff` along with contextual flags (like whether it's a manual/scheduled run) are passed to the `release-tool determine-changes` command (itself run in Docker on the runner using the freshly built image) to get a list of affected service names.
    3.  **Execute Deployment on Remote Host (via SSH)**:
        *   The `ssh-action` connects to the target server.
        *   Its primary role is now to execute the `release-tooling/scripts/deploy_on_host.sh` script located on the remote host (after being synced from the repository).
        *   Necessary parameters like the list of affected services, `VARS_JSON` (GitHub Actions variables), and `SECRETS_JSON` (GitHub Actions secrets) are passed as arguments to `deploy_on_host.sh`.

   #### The `deploy_on_host.sh` Orchestrator Script
   This Bash script, located at `release-tooling/scripts/deploy_on_host.sh` within the repository, is the main orchestrator on the deployment target. Its key responsibilities include:
    *   **Parameter Handling**: Accepts `AFFECTED_SERVICES`, `VARS_JSON_STR`, and `SECRETS_JSON_STR` from the `release.yml` workflow.
    *   **Environment Setup**: Defines critical paths (potentially overridden by `TEST_OVERRIDE_*` variables for testing) and pulls the latest `release-tool` Docker image (e.g., `ghcr.io/YOUR_ORG/YOUR_REPO/release-tool:latest`).
    *   **Host-Level Script Execution**: Runs essential Bash scripts directly on the host:
        *   `refresh_podman_secrets.sh`: Updates Podman secrets using `SECRETS_JSON_STR`.
        *   `create_env_variables.sh`: Creates the `.env` file (potentially using `VARS_JSON_STR`).
        *   Sources `.env` files.
        *   `check-service-envs.sh`: Validates environment setup.
        *   `generate_meta_services.sh`: Creates overall systemd targets (e.g., `all-containers.target`).
        *   `quadlet --dryrun`: Validates generated unit files.
        *   `podman auto-update`: Checks for image updates for running containers.
    *   **Python Release Tool Invocation**: Calls the containerized Python `release-tool` via `podman run` for its core tasks, ensuring necessary volumes (for service definitions, systemd unit paths, Podman socket, systemd bus) are mounted and arguments are passed:
        *   `release-tool generate-units`: Generates systemd units for affected services.
        *   `release-tool pull-images`: Pulls images for these services.
        *   `release-tool manage-services restart`: Restarts the services and their dependents, and checks their status.
    *   **Testability**: The script is designed to be testable by allowing critical paths (like script locations, unit directories, Quadlet executable path) to be overridden by `TEST_OVERRIDE_*` environment variables. End-to-end tests for this script are located in `release-tooling/tests_e2e_orchestrator/` and use `pytest` to execute the script and mock its dependencies.

   This layered approach (GitHub Actions workflow -> `deploy_on_host.sh` -> Python `release-tool` in Docker) enhances local testability, modularity, and maintainability of the deployment process. For more details on the Python release utility itself, see `release-tooling/pytool/README.md`.

## 🏗️ Application Structure

Each application should follow this structure:

```
app_name/
├── Dockerfile           # Container definition
├── docker-compose.yaml  # Local development setup
├── entrypoints/        # Container entrypoint scripts
│   ├── entrypoint.sh   # Main container entrypoint
│   └── entrypoint_test.sh  # Test entrypoint
├── src/                # Application source code
├── test/               # Unit and integration tests
├── e2e_tests/          # End-to-end tests
└── requirements.txt    # Python dependencies (if applicable)
```

## 🌐 Service Discovery

The `services/` directory contains configurations for infrastructure services:

- `01_postgres/`: PostgreSQL database service
- `02_app_1/`: Application 1 service configuration
- `03_nginx-proxy/`: Nginx reverse proxy for routing

## 🔒 Security

- **Secrets Management**: Environment variables are used for sensitive configuration
- **Container Security**: Rootless container execution with Podman
- **Dependency Scanning**: Integrated security scanning in CI/CD pipeline

## 📈 Monitoring and Logging

- Container logs are captured by Docker
- Application metrics can be exposed via `/metrics` endpoint
- Structured logging in JSON format

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📬 Contact

For questions or support, please open an issue in the repository.
