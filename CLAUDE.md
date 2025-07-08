# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### General Repository Commands
- `docker-compose -f applications/[app_name]/docker-compose.yaml up --build` - Build and run an application locally
- `find applications -type d -exec test -e '{}'/Dockerfile \; -print` - Find all applications with Dockerfiles
- `./tools/automation/see_workflow_logs.sh` - Check latest GitHub Actions workflow status and logs

### Workflow Testing Commands
- `act` - Run GitHub Actions workflows locally using act
- `act -l` - List available workflows and jobs
- `act -j build-application` - Run specific job locally
- `act push` - Simulate push event to test build workflow
- `act workflow_call --input environment=staging` - Test release workflow with staging environment

### Commit Message Tags for CI/CD Control
- `[force-build]` - Force build all applications regardless of changes
- `[skip-build]` - Skip the entire workflow (no builds or releases)
- `[release-only]` - Skip builds but proceed with releases using latest images
- `[deploy-services: service1,service2,service3]` - Deploy only specified docker-compose service names
- `[deploy-services: all]` - Deploy all services from all docker-compose files

### Docker Testing Commands
- `./tools/development/test-docker-builds.sh` - Test all Dockerfile builds locally
- `docker build -t test-image applications/[app_name]/` - Test specific application Dockerfile
- `docker build -t test-image tools/[utility_name]/` - Test specific utility Dockerfile
- `docker build -t test-image tools/deployment/[tool_name]/` - Test specific release tool Dockerfile
- `docker run --rm test-image /app/entrypoints/entrypoint_test.sh` - Run tests in built image

### Containerized Tool Testing Commands
**IMPORTANT**: Always prefer using Docker containers for testing deployment scripts and tools instead of local installations. This ensures consistent environments and avoids dependency conflicts.

#### Deployment Manager CLI Tool
- `docker build -t deployment-manager-test tools/deployment/deployment-manager/` - Build deployment manager image
- `docker run --rm deployment-manager-test /app/entrypoints/entrypoint_test.sh` - Run tests in container
- `docker run --rm deployment-manager-test release-tool --help` - Show CLI help in container
- `docker run --rm -v $(pwd):/workspace deployment-manager-test release-tool [command]` - Run CLI commands with workspace access

#### General Tool Testing Pattern
- `docker build -t [tool-name]-test tools/[path-to-tool]/` - Build tool image for testing
- `docker run --rm [tool-name]-test /app/entrypoints/entrypoint_test.sh` - Run tool tests
- `docker run --rm -v $(pwd):/workspace [tool-name]-test [tool-command]` - Execute tool with workspace access

**Benefits of containerized testing**:
- No need for local Poetry, Python, or other language runtime installations
- Consistent testing environment across different machines
- Isolation from local system dependencies
- Same environment as CI/CD pipeline
- Easy cleanup after testing (no local dependency pollution)

### Application-Specific Commands

#### app.pxy6.com (Shopify Remix App)
- `cd applications/app.pxy6.com/src` - Navigate to application source
- `npm run dev` - Start development server with Shopify CLI
- `npm run build` - Build for production
- `npm run setup` - Generate Prisma client and run migrations
- `npm run lint` - Run ESLint
- `npm run test` - Run Jest tests
- `npm run test:coverage` - Run tests with coverage
- `npm run typecheck` - TypeScript type checking
- `shopify app dev` - Start Shopify app development and manage database migrations
- **Data Sync**: Use "Reload Data" button in app to trigger Airflow DAGs for Shopify data synchronization

#### pxy6.com (React/Vite App)
- `cd applications/pxy6.com/src` - Navigate to application source
- `npm run dev` - Start development server with type checking
- `npm run build` - Build for production
- `npm run typecheck` - TypeScript type checking
- `npm run lint` - Run ESLint
- `npm run test` - Run Jest tests
- `npm run test:e2e` - Run Playwright e2e tests
- `npm run docker:build` - Build Docker image
- `npm run docker:run` - Run Docker container

#### app_1 (Python FastAPI/Streamlit)
- `cd applications/app_1` - Navigate to application directory
- `pytest` - Run Python tests
- `python -m src.api.main` - Run FastAPI server
- `python -m src.app.main` - Run Streamlit app
- `cd src/data/db/migrations && alembic upgrade head` - Run database migrations

#### airflow_dags (Airflow DAGs Package)
- `cd applications/airflow_dags` - Navigate to DAGs directory
- `docker build -t airflow-dags .` - Build DAG container
- `docker run --rm airflow-dags` - Validate DAG imports and syntax
- `./validate_dags.sh` - Comprehensive DAG validation (Docker-based)
- `./quick_test.sh` - Quick validation for development
- `pytest tests/` - Run DAG tests (with mocked dependencies)
- `python -c "from dags.shopify_data_pipeline import dag"` - Validate main DAG import
- `docker exec airflow_dags-airflow-standalone-1 airflow dags list-import-errors` - Check DAG import errors in running Airflow container
- Note: Contains Shopify data integration DAGs that sync product, customer, and order data to PostgreSQL

#### Release Tool (Python CLI)
- `cd tools/deployment/deployment-manager` - Navigate to release tool directory
- `poetry install` - Install dependencies
- `poetry run pytest` - Run tests
- `poetry run release-tool --help` - Show CLI help

## Important: Local Development vs Services Deployment

**⚠️ CRITICAL: Do NOT run docker-compose commands locally in the services/ folder**

### Local Development
- **Use application-level docker-compose files**: Located in `applications/[app_name]/docker-compose.yaml`
- **Command**: `docker-compose -f applications/[app_name]/docker-compose.yaml up --build`
- **Purpose**: Local development, testing, and debugging individual applications
- **Environment**: Isolated, lightweight, development-focused configurations

### Services Deployment (Production Infrastructure)
- **Location**: `services/` folder contains infrastructure service configurations
- **Deployment Target**: Staging and live servers only
- **Management**: Automated deployment system using Podman with systemd
- **Services Include**: PostgreSQL, Nginx proxy, Airflow, and other infrastructure components
- **DO NOT**: Run these locally with docker-compose - they are production infrastructure configurations

### Why This Separation Matters
1. **Resource Usage**: Services configurations are designed for production servers with different resource requirements
2. **Network Configuration**: Production services use specific networking that may conflict with local development
3. **Data Persistence**: Production services manage persistent data that shouldn't be mixed with local development
4. **Security**: Production configurations include security settings not suitable for local development
5. **Dependencies**: Services may depend on external resources not available locally

### What to Use When
- **Developing/Testing Applications**: Use `applications/[app_name]/docker-compose.yaml`
- **Testing Infrastructure**: Use the deployment system on staging servers
- **Production Deployment**: Managed automatically by CI/CD pipeline

## Architecture

This is a containerized multi-application deployment system with automated CI/CD pipelines:

### Project Structure
- `applications/` - Individual containerized applications with docker-compose files for local development
- `services/` - Infrastructure service configurations deployed on staging/live servers (PostgreSQL, Nginx proxy, Airflow)
- `tools/` - Helper tools and automation scripts
- `.github/workflows/` - CI/CD pipeline definitions

**Note**: The `applications/airflow_dags/` directory contains DAG definitions that get packaged and deployed to the Airflow service defined in `services/06_airflow/`.

### Application Types
1. **app.pxy6.com**: Shopify app built with Remix, TypeScript, Prisma ORM, and Polaris UI
2. **pxy6.com**: React/Vite frontend with Tailwind CSS, shadcn/ui components, and analytics tracking
3. **app_1**: Python backend with FastAPI API and Streamlit frontend, using SQLAlchemy and PostgreSQL (has skipped-Dockerfile, not currently built)
4. **airflow_dags**: Apache Airflow DAGs package for comprehensive Shopify data integration - syncs products, customers, orders, and metadata using GraphQL API

### Utility Types
1. **user_management**: Python utility for managing users with Docker containerization
2. **deployment-manager**: Python CLI tool for managing selective service deployments (located in tools/deployment/deployment-manager)

### CI/CD Pipeline Flow
1. **Build Workflow**: Detects changed applications, builds Docker images, runs tests, pushes to GHCR
2. **Release Workflow**: Deploys to staging → runs e2e tests → deploys to production
3. **E2E Tests**: Runs end-to-end tests using application-specific entrypoints

### Key Technologies
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose for local development (use application-level docker-compose files), Podman with systemd for production (uses services/ configurations)
- **Registry**: GitHub Container Registry (ghcr.io)
- **Reverse Proxy**: Nginx for external access and SSL termination
- **Database**: PostgreSQL with migrations via Prisma (app.pxy6.com) and Alembic (app_1)
- **Workflow Orchestration**: Apache Airflow for data pipelines and Shopify integration
- **Testing**: Jest/Playwright for frontend, pytest for Python, containerized e2e tests

### Development Patterns
- Each application has standardized entrypoints: `entrypoint.sh`, `entrypoint_test.sh`, `entrypoint_e2e.sh`
- Environment variables managed through GitHub Actions secrets and `.env` files
- Version tagging uses timestamp format (YYYYMMDD-HHMMSS)
- Force build all applications with `[force-build]` in commit message
- Skip builds with `[skip-build]` in commit message
- Release-only mode with `[release-only]` in commit message - skips builds but proceeds with releases using latest images

### Service Communication
- Internal services communicate through Docker networks
- External access routed through Nginx reverse proxy
- Services numbered for startup order (01_postgres, 02_app_1, 03_nginx-proxy, 04_app_pxy6_com, 05_pxy6_web, 06_airflow)
- Airflow connects to PostgreSQL for metadata and main application database for Shopify data

### Database Migrations
- **app.pxy6.com**: Database migrations managed through `shopify app dev` command - SQLite for local development, PostgreSQL for production
- **app_1**: Use `alembic upgrade head` in the data/db/migrations directory
- **airflow_dags**: Uses pxy6_airflow database user to connect to app.pxy6.com's PostgreSQL database for data storage

### Airflow Integration
- **Service Location**: `services/06_airflow/` - Apache Airflow 3.0.2 infrastructure service
- **DAGs Location**: `applications/airflow_dags/` - Comprehensive Shopify data integration DAGs
- **Architecture**: Built with custom operators, hooks, and GraphQL client for Shopify API integration
- **Purpose**: Orchestrates complete Shopify data synchronization (products, customers, orders, metafields, collections)
- **Database**: Uses PostgreSQL for Airflow metadata; stores Shopify data in app.pxy6.com database using pxy6_airflow user
- **Components**: DAGs Deploy (one-shot deployment), Webserver (UI), Scheduler (task execution), Init (database setup)
- **API Integration**: DAGs can be triggered from app.pxy6.com via REST API endpoints
- **Data Pipeline**: 3 main DAGs - shopify_data_pipeline (orchestration), shopify_past_purchases (customer/orders), shopify_store_metadata (products/catalog)
- **Hot Deployment**: DAGs can be deployed independently without restarting Airflow services - Airflow automatically detects new DAG files

### Deployment Information
- **app.pxy6.com**: Releases automatically deploy staging and live Shopify configurations, overwriting any manual deployments

### Git Hooks
- `./tools/git-hooks/install-hooks.sh` - Install pre-commit hooks for the repository
- **Pre-commit hook**: Automatically runs quality checks when changes are committed
  - **app.pxy6.com checks** (when files in `applications/app.pxy6.com/` are modified):
    - TypeScript type checking (`npm run typecheck`)
    - ESLint linting (`npm run lint`)
    - Jest tests (`npm run test`)
    - Build process (`npm run build`)
  - **Docker build tests** (when any Dockerfile is modified):
    - Tests Docker build for each modified Dockerfile
    - Prevents commits if Docker builds fail
    - Helps catch Docker build issues early
  - **YAML validation** (when any .yaml/.yml file is modified):
    - Validates YAML syntax using Docker with mikefarah/yq
    - Prevents commits with invalid YAML syntax
    - Helps catch configuration errors early
    - No local dependencies required
- All checks must pass for commit to succeed

## Git Commit Best Practices

# Committing changes with git

When the user asks you to create a new git commit, follow these steps carefully:

1. You have the capability to call multiple tools in a single response. When multiple independent pieces of information are requested, batch your tool calls together for optimal performance. ALWAYS run the following bash commands in parallel, each using the Bash tool:
  - Run a git status command to see all untracked files.
  - Run a git diff command to see both staged and unstaged changes that will be committed.
  - Run a git log command to see recent commit messages, so that you can follow this repository's commit message style.
2. **Carefully review all changes** before committing:
  - Analyze each changed file to understand what was modified and why
  - Identify which changes are necessary for the task at hand
  - Identify any unintended or unnecessary changes that should be reverted
  - Check for any sensitive information that shouldn't be committed
  - For complex changes, consider checking the original state of files to understand what was removed or modified
3. **Clean up unnecessary changes** before committing:
  - If you find changes that are not necessary for the current task, revert them using git restore or manual edits
  - Only stage and commit the changes that are actually needed
  - Ensure all changes align with the original task requirements
4. **Draft and create the commit**:
  - Summarize the nature of the changes (eg. new feature, enhancement to an existing feature, bug fix, refactoring, test, docs, etc.). Ensure the message accurately reflects the changes and their purpose (i.e. "add" means a wholly new feature, "update" means an enhancement to an existing feature, "fix" means a bug fix, etc.).
  - Draft a concise (1-2 sentences) commit message that focuses on the "why" rather than the "what"
  - Ensure it accurately reflects the changes and their purpose
5. You have the capability to call multiple tools in a single response. When multiple independent pieces of information are requested, batch your tool calls together for optimal performance. ALWAYS run the following commands in parallel:
   - Add only the relevant and necessary files to the staging area.
   - Create the commit with a message ending with:
   🤖 Generated with [Claude Code](https://claude.ai/code)

   Co-Authored-By: Claude <noreply@anthropic.com>
   - Run git status to make sure the commit succeeded.
6. If the commit fails due to pre-commit hook changes, retry the commit ONCE to include these automated changes. If it fails again, it usually means a pre-commit hook is preventing the commit. If the commit succeeds but you notice that files were modified by the pre-commit hook, you MUST amend your commit to include them.

Important notes:
- NEVER update the git config
- NEVER run additional commands to read or explore code, besides git bash commands
- NEVER use the TodoWrite or Task tools
- DO NOT push to the remote repository unless the user explicitly asks you to do so
- IMPORTANT: Never use git commands with the -i flag (like git rebase -i or git add -i) since they require interactive input which is not supported.
- If there are no changes to commit (i.e., no untracked files and no modifications), do not create an empty commit
- **ALWAYS verify changes one by one** - don't blindly commit all changes without understanding what each change does
- **Remove or revert unnecessary changes** before committing to keep the commit clean and focused
- In order to ensure good formatting, ALWAYS pass the commit message via a HEREDOC, a la this example:
<example>
git commit -m "$(cat <<'EOF'
   Commit message here.

   🤖 Generated with [Claude Code](https://claude.ai/code)

   Co-Authored-By: Claude <noreply@anthropic.com>
   EOF
   )"
</example>