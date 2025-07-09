#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏗️ Setting up Test Environment${NC}"

# Change to test environment directory
cd "$(dirname "$0")/.."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo -e "${RED}❌ docker-compose is not installed. Please install docker-compose first.${NC}"
    exit 1
fi

# Clean up any existing test environment
echo -e "${YELLOW}🧹 Cleaning up existing test environment...${NC}"
docker-compose down -v --remove-orphans || true
docker system prune -f || true

# Create necessary directories
echo -e "${GREEN}📁 Creating necessary directories...${NC}"
mkdir -p logs
mkdir -p test-results

# Build Docker images
echo -e "${GREEN}🏗️ Building Docker images...${NC}"
docker-compose build --no-cache

# Start infrastructure services first
echo -e "${GREEN}🗄️ Starting infrastructure services...${NC}"
docker-compose up -d test-postgres test-registry

# Wait for database to be ready
echo -e "${GREEN}⏳ Waiting for database to be ready...${NC}"
timeout=60
counter=0
while ! docker-compose exec -T test-postgres pg_isready -U test_user -d test_db > /dev/null 2>&1; do
    if [ $counter -ge $timeout ]; then
        echo -e "${RED}❌ Database failed to start within ${timeout} seconds${NC}"
        docker-compose logs test-postgres
        exit 1
    fi
    echo -e "${YELLOW}Waiting for database... (${counter}/${timeout})${NC}"
    sleep 1
    ((counter++))
done

echo -e "${GREEN}✅ Database is ready${NC}"

# Start application services
echo -e "${GREEN}🚀 Starting application services...${NC}"
docker-compose up -d test-app1 test-app2 test-shopify-app

# Wait for applications to be ready
echo -e "${GREEN}⏳ Waiting for applications to be ready...${NC}"
sleep 20

# Start proxy services
echo -e "${GREEN}🔄 Starting proxy services...${NC}"
docker-compose up -d test-nginx

# Start Airflow (takes longer to initialize)
echo -e "${GREEN}🌪️ Starting Airflow service...${NC}"
docker-compose up -d test-airflow

# Wait for all services to be healthy
echo -e "${GREEN}🔍 Checking service health...${NC}"
services=("test-postgres" "test-app1" "test-app2" "test-shopify-app" "test-nginx" "test-registry")
for service in "${services[@]}"; do
    timeout=120
    counter=0
    while ! docker-compose ps | grep -q "$service.*Up"; do
        if [ $counter -ge $timeout ]; then
            echo -e "${RED}❌ $service failed to start within ${timeout} seconds${NC}"
            docker-compose logs "$service"
            exit 1
        fi
        echo -e "${YELLOW}Waiting for $service... (${counter}/${timeout})${NC}"
        sleep 1
        ((counter++))
    done
    echo -e "${GREEN}✅ $service is running${NC}"
done

# Display service URLs
echo -e "${BLUE}🌐 Service URLs:${NC}"
echo -e "${GREEN}  • App1 (FastAPI): http://localhost:8001${NC}"
echo -e "${GREEN}  • App1 (Streamlit): http://localhost:8501${NC}"
echo -e "${GREEN}  • App2 (React): http://localhost:3000${NC}"
echo -e "${GREEN}  • Shopify App: http://localhost:3001${NC}"
echo -e "${GREEN}  • Nginx Proxy: http://localhost:8080${NC}"
echo -e "${GREEN}  • Airflow: http://localhost:8082 (admin/admin)${NC}"
echo -e "${GREEN}  • Registry: http://localhost:5000${NC}"
echo -e "${GREEN}  • PostgreSQL: localhost:5433 (test_user/test_password)${NC}"

# Run initial health check
echo -e "${GREEN}🔍 Running initial health check...${NC}"
./scripts/health-check.sh

echo -e "${GREEN}✅ Test environment setup complete!${NC}"
echo -e "${BLUE}💡 Run './scripts/run-tests.sh' to execute tests${NC}"
echo -e "${BLUE}💡 Run './scripts/health-check.sh' to check service health${NC}"
echo -e "${BLUE}💡 Run 'docker-compose logs <service>' to view logs${NC}"