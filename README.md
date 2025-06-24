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
   - Manages versioning and release notes
   - Updates the `releases` branch with version information

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
