# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### General Repository Commands
- `docker-compose -f applications/[app_name]/docker-compose.yaml up --build` - Build and run an application locally
- `find applications -type d -exec test -e '{}'/Dockerfile \; -print` - Find all applications with Dockerfiles
- `./utilities/github-automation/see_workflow_logs.sh` - Check latest GitHub Actions workflow status and logs

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
- `shopify app dev` - Start Shopify app development

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
- `pytest tests/` - Run DAG tests
- `python -c "from dags.shopify_get_past_purchases_dag import dag"` - Validate DAG import
- Note: This packages DAGs and dependencies for the Airflow service in `services/06_airflow/`

#### Release Tool (Python CLI)
- `cd release-tooling/pytool` - Navigate to release tool directory
- `poetry install` - Install dependencies
- `poetry run pytest` - Run tests
- `poetry run release-tool --help` - Show CLI help

## Architecture

This is a containerized multi-application deployment system with automated CI/CD pipelines:

### Project Structure
- `applications/` - Individual containerized applications
- `services/` - Infrastructure service configurations (PostgreSQL, Nginx proxy, Airflow)
- `utilities/` - Helper tools and automation scripts
- `.github/workflows/` - CI/CD pipeline definitions

**Note**: The `applications/airflow_dags/` directory contains DAG definitions that get packaged and deployed to the Airflow service defined in `services/06_airflow/`.

### Application Types
1. **app.pxy6.com**: Shopify app built with Remix, TypeScript, Prisma ORM, and Polaris UI
2. **pxy6.com**: React/Vite frontend with Tailwind CSS, shadcn/ui components, and analytics tracking
3. **app_1**: Python backend with FastAPI API and Streamlit frontend, using SQLAlchemy and PostgreSQL (has skipped-Dockerfile, not currently built)
4. **airflow_dags**: Apache Airflow DAGs package for Shopify data integration, contains workflow definitions and dependencies that get deployed to the Airflow service

### Utility Types
1. **user_management**: Python utility for managing users with Docker containerization
2. **release-tooling**: Python CLI tool for managing selective service deployments

### CI/CD Pipeline Flow
1. **Build Workflow**: Detects changed applications, builds Docker images, runs tests, pushes to GHCR
2. **Release Workflow**: Deploys to staging → runs e2e tests → deploys to production
3. **E2E Tests**: Runs end-to-end tests using application-specific entrypoints

### Key Technologies
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose for local development, Podman with systemd for production
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

### Service Communication
- Internal services communicate through Docker networks
- External access routed through Nginx reverse proxy
- Services numbered for startup order (01_postgres, 02_app_1, 03_nginx-proxy, 04_app_pxy6_com, 05_pxy6_web, 06_airflow)
- Airflow connects to PostgreSQL for metadata and main application database for Shopify data

### Database Migrations
- **app.pxy6.com**: Use `prisma migrate deploy` or `npm run setup`
- **app_1**: Use `alembic upgrade head` in the data/db/migrations directory

### Airflow Integration
- **Service Location**: `services/06_airflow/` - Apache Airflow infrastructure service
- **DAGs Location**: `applications/airflow_dags/` - DAG definitions and Python dependencies
- **Architecture**: The service builds a custom Airflow image that incorporates DAGs from applications/airflow_dags
- **Purpose**: Orchestrates Shopify data integration workflows (past purchases, store metadata)
- **Database**: Uses PostgreSQL for Airflow metadata; connects to main application database for data storage
- **Components**: Webserver (UI), Scheduler (task execution), Init (database setup)

### Deployment Information
- **app.pxy6.com**: Releases automatically deploy staging and live Shopify configurations, overwriting any manual deployments

### Git Hooks
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
    - Validates YAML syntax using yq or python3
    - Prevents commits with invalid YAML syntax
    - Helps catch configuration errors early
- All checks must pass for commit to succeed