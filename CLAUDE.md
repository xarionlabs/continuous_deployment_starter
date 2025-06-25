# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### General Repository Commands
- `docker-compose -f applications/[app_name]/docker-compose.yaml up --build` - Build and run an application locally
- `find applications -type d -exec test -e '{}'/Dockerfile \; -print` - Find all applications with Dockerfiles

### Application-Specific Commands

#### app.pxy6.com (Shopify Remix App)
- `npm run dev` - Start development server with Shopify CLI
- `npm run build` - Build for production
- `npm run setup` - Generate Prisma client and run migrations
- `npm run lint` - Run ESLint
- `npm run test` - Run Jest tests
- `npm run test:coverage` - Run tests with coverage
- `npm run typecheck` - TypeScript type checking
- `shopify app dev` - Start Shopify app development

#### pxy6.com (React/Vite App)
- `npm run dev` - Start development server with type checking
- `npm run build` - Build for production
- `npm run typecheck` - TypeScript type checking
- `npm run lint` - Run ESLint
- `npm run test` - Run Jest tests
- `npm run test:e2e` - Run Playwright e2e tests
- `npm run docker:build` - Build Docker image
- `npm run docker:run` - Run Docker container

#### app_1 (Python FastAPI/Streamlit)
- `pytest` - Run Python tests
- `python -m src.api.main` - Run FastAPI server
- `python -m src.app.main` - Run Streamlit app
- `alembic upgrade head` - Run database migrations

#### app_2 (Python Application)
- `pytest` - Run Python tests
- `python src/application.py` - Run the application

## Architecture

This is a containerized multi-application deployment system with automated CI/CD pipelines:

### Project Structure
- `applications/` - Individual containerized applications
- `services/` - Infrastructure service configurations (PostgreSQL, Nginx proxy)
- `utilities/` - Helper tools and automation scripts
- `.github/workflows/` - CI/CD pipeline definitions

### Application Types
1. **app.pxy6.com**: Shopify app built with Remix, TypeScript, Prisma ORM, and Polaris UI
2. **pxy6.com**: React/Vite frontend with Tailwind CSS, shadcn/ui components, and Supabase integration
3. **app_1**: Python backend with FastAPI API and Streamlit frontend, using SQLAlchemy and PostgreSQL
4. **app_2**: Simple Python application

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
- Services numbered for startup order (01_postgres, 02_app_1, 03_nginx-proxy)

### Database Migrations
- **app.pxy6.com**: Use `prisma migrate deploy` or `npm run setup`
- **app_1**: Use `alembic upgrade head` in the data/db/migrations directory

### Deployment Information
- **app.pxy6.com**: Releases automatically deploy staging and live Shopify configurations, overwriting any manual deployments