# Python Release Utility

This directory contains a Python-based command-line utility designed to manage the selective build, release, and deployment of services. It is intended to be run as a containerized application during the GitHub Actions release workflow.

## Purpose

This tool replaces several Bash scripts previously used in the release process, aiming to provide:
- Improved testability through Python's testing frameworks.
- Better maintainability for complex logic.
- More robust error handling.
- Clearer structuring of release tasks.

## Core Functionality

The tool provides the following main commands:

- `determine-changes`: Analyzes changed files in the main repository to determine which services are affected and require updating.
- `generate-units`: Generates Quadlet-compatible systemd unit files (`.container`, `.volume`, `.network`, `.service`) for affected services based on their Docker Compose definitions. It handles merging global environment variables, processing service-specific configurations, and setting up dependencies.
- `pull-images`: Pulls the required container images for the affected services using Podman.
- `manage-services`:
    - `restart`: Restarts affected services and their systemd dependents, then performs health checks.
    - `status` (placeholder): Intended for checking service statuses.

## Development Setup

This project uses [Poetry](https://python-poetry.org/) for dependency management and packaging.

1.  **Install Poetry**: Follow the instructions on the [official Poetry website](https://python-poetry.org/docs/#installation).
2.  **Navigate to the tool's directory**:
    ```bash
    cd utils/release_tool
    ```
3.  **Install Dependencies**:
    ```bash
    poetry install
    ```
    This will create a virtual environment in the project directory (or elsewhere, depending on your Poetry configuration) and install all dependencies, including development dependencies like `pytest`.

## Running the Tool Locally

You can run the tool using `poetry run`:

```bash
poetry run release-tool --help
poetry run release-tool determine-changes --changed-files "services/my-app/some_file.py"
poetry run release-tool generate-units --affected-services "my-app" --services-dir "../../services" --output-dir "./test_output_units" --vars-json "{\"GLOBAL_VAR\":\"global_value\"}"
# etc.
```

Note: For commands that interact with Podman or systemd (`pull-images`, `manage-services`), running them locally requires Podman and a user systemd session to be correctly configured on your local machine. They are primarily designed to be run within the context of the Docker container on the deployment target.

## Available Commands

For a full list of commands and their options, run:
```bash
poetry run release-tool --help
```
And for subcommands:
```bash
poetry run release-tool manage-services --help
```

Key commands include:
- `determine-changes --changed-files "..." --assume-values-changed --services-dir "..."`: Determines affected services.
- `generate-units --affected-services "..." --services-dir "..." --output-dir "..." [--meta-target "..." --vars-json "..."]`: Generates systemd units.
- `pull-images --affected-services "..." --units-dir "..."`: Pulls container images.
- `manage-services restart --affected-services "..."`: Restarts services and their dependents.

## Building the Docker Image

A `Dockerfile` is provided to build a container image for this tool.

1.  **Navigate to the tool's directory**:
    ```bash
    cd utils/release_tool
    ```
2.  **Build the image**:
    ```bash
    docker build -t your-registry/your-org/release-tool:latest .
    ```
    (Replace `your-registry/your-org/release-tool:latest` with your desired image name and tag).

## Running Tests

Tests are written using `pytest`.

1.  **Ensure development dependencies are installed** (`poetry install`).
2.  **Navigate to the tool's directory**:
    ```bash
    cd utils/release_tool
    ```
3.  **Run tests**:
    ```bash
    poetry run pytest
    ```
    This will run all tests in the `tests/` directory and provide a coverage report.
    You can also run specific test files or tests:
    ```bash
    poetry run pytest tests/test_unit_generator.py
    poetry run pytest tests/test_service_manager.py -k "test_manage_services_restart_simple_success"
    ```

## How it's Used in CI/CD

The GitHub Actions workflow (`.github/workflows/release.yml`) uses this tool as part of a larger deployment process orchestrated on the remote host.

1.  **Build Docker Image**: A dedicated job in the GitHub Actions workflow is responsible for building this Python utility into a Docker image (e.g., `ghcr.io/your-org/your-repo/release-tool:latest`) and pushing it to a container registry. This typically happens if changes are detected in the `utils/release_tool/` directory.
2.  **Remote Host Orchestration**:
    *   On the target deployment server, a Bash script named `deploy_on_host.sh` (located in `.github/workflows/scripts/`) is executed via SSH by the `release.yml` workflow.
    *   This `deploy_on_host.sh` script manages the overall deployment sequence:
        *   It pulls the latest `release-tool` Docker image.
        *   It runs prerequisite host-level Bash scripts (e.g., for managing Podman secrets, creating `.env` files).
        *   **It then invokes this Python `release-tool` via `podman run` commands for its core tasks:**
            *   `generate-units`: To generate systemd unit files. Paths for service definitions and output unit files are volume-mounted into the container. Configuration like affected services, global variables (`VARS_JSON`), and meta-target names are passed as CLI arguments.
            *   `pull-images`: To pull necessary container images. The Podman socket and the directory containing generated unit files are mounted.
            *   `manage-services restart`: To restart services. The Podman socket and systemd user bus are mounted.
        *   Finally, `deploy_on_host.sh` may run other host-level commands (e.g., `quadlet --dryrun`, `podman auto-update`).

This containerized approach ensures that the Python tool runs in a consistent environment with all its dependencies, while `deploy_on_host.sh` handles the interaction with the specific host environment.
```
