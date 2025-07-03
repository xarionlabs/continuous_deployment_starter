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
├── .github/
│   └── workflows/          # GitHub Actions workflows
│       ├── build.yml        # Build and test applications
│       ├── e2e-tests.yml    # End-to-end testing
│       └── release.yml      # Release management
├── applications/           # Individual applications
│   ├── app_1/              # Example application 1
│   │   ├── Dockerfile       # Application Dockerfile
│   │   ├── entrypoints/     # Container entrypoint scripts
│   │   ├── src/            # Application source code
│   │   ├── test/           # Unit and integration tests
│   │   └── e2e_tests/      # End-to-end tests
│   └── app_2/              # Example application 2
│       └── ...
└── services/              # Infrastructure services
    ├── 01_postgres/        # PostgreSQL service
    ├── 02_app_1/           # Application 1 service
    └── 03_nginx-proxy/     # Nginx reverse proxy
```

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
   Located in `utils/release_tool/`, this Python application (built into a Docker image) is now responsible for the core tasks of service deployment:
    - **Selective Processing**: It intelligently determines which services are affected by code changes and processes only those, rather than redeploying everything.
    - **Quadlet Generation**: It dynamically generates systemd unit files (e.g., `.container`, `.service`) for each affected service from its Docker Compose definition found in the `services/` directory. This includes handling environment variables, volume mounts, network configurations, secrets, and dependencies.
    - **Image Pulling**: It selectively pulls the latest container images for affected services.
    - **Service Management**: It restarts the affected services and their dependents using `systemctl --user` commands and performs health checks.

   #### Workflow Overview:
   The `release.yml` workflow now performs the following high-level steps for deployment:
    1.  **Build Tool (If Changed)**: A preliminary job (or separate workflow) builds the Python release utility Docker image (`ghcr.io/your-org/your-repo/release-tool:latest`) if its source code in `utils/release_tool/` has changed, and pushes it to the container registry.
    2.  **Determine Changes (GitHub Runner)**: The workflow checks out the main repository and uses `git diff` to identify changed files since the last deployment. This list of changes is used to determine which services might be affected.
    3.  **Remote Execution (via SSH)**:
        *   The latest `release-tool` Docker image is pulled on the remote server.
        *   Host-level setup scripts are run (e.g., `refresh_podman_secrets.sh` to update Podman secrets from GitHub Actions secrets, `create_env_variables.sh` to set up a `.env` file from GitHub Actions variables).
        *   The Python `release-tool` is invoked via `podman run` for its main tasks:
            *   `release-tool determine-changes` (this is actually done on the runner before SSH, the result is passed to other commands).
            *   `release-tool generate-units`: Generates systemd units for affected services. Requires mounts for service definitions and the systemd user unit directory. `VARS_JSON` (from GitHub `vars`) is passed to inject global environment variables.
            *   `release-tool pull-images`: Pulls images for affected services. Requires mounting the Podman socket and the systemd unit directory.
            *   `release-tool manage-services restart`: Restarts services. Requires mounting the Podman socket and the systemd user bus.
        *   Other host-level scripts are run (e.g., `quadlet --dryrun`, `generate_meta_services.sh` for creating overall targets like `all-containers.target`, and `podman auto-update`).

   This approach enhances the reliability, testability, and maintainability of the deployment process. For more details on the Python release utility itself, see `utils/release_tool/README.md`.

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
