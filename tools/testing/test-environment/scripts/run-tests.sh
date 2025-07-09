#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Starting Test Environment...${NC}"

# Change to test environment directory
cd "$(dirname "$0")/.."

# Function to cleanup on exit
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up test environment...${NC}"
    docker-compose down -v --remove-orphans
    docker system prune -f
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Build and start services
echo -e "${GREEN}🏗️ Building and starting test services...${NC}"
docker-compose up -d --build

# Wait for services to be ready
echo -e "${GREEN}⏳ Waiting for services to be healthy...${NC}"
sleep 30

# Check service health
echo -e "${GREEN}🔍 Checking service health...${NC}"
services=("test-postgres" "test-app1" "test-app2" "test-shopify-app" "test-nginx" "test-registry")
for service in "${services[@]}"; do
    if docker-compose ps | grep -q "$service.*Up"; then
        echo -e "${GREEN}✅ $service is running${NC}"
    else
        echo -e "${RED}❌ $service is not running${NC}"
        docker-compose logs "$service"
        exit 1
    fi
done

# Run tests
echo -e "${GREEN}🧪 Running integration tests...${NC}"
docker-compose run --rm test-runner pytest -v --tb=short

# Optional: Run specific test categories
if [ "$1" == "services" ]; then
    echo -e "${GREEN}🔧 Running service tests only...${NC}"
    docker-compose run --rm test-runner pytest tests/test_services.py -v
elif [ "$1" == "workflow" ]; then
    echo -e "${GREEN}🔄 Running workflow tests only...${NC}"
    docker-compose run --rm test-runner pytest tests/test_release_workflow.py -v
elif [ "$1" == "all" ]; then
    echo -e "${GREEN}🧪 Running all tests...${NC}"
    docker-compose run --rm test-runner pytest -v --tb=short
fi

echo -e "${GREEN}✅ All tests completed successfully!${NC}"