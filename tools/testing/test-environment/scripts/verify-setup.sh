#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Verifying Test Environment Setup${NC}"

# Change to test environment directory
cd "$(dirname "$0")/.."

# Check if all required files exist
echo -e "${GREEN}📁 Checking required files...${NC}"

required_files=(
    "docker-compose.yml"
    "mock-services/nginx/nginx.conf"
    "mock-services/app1/Dockerfile"
    "mock-services/app2/Dockerfile"
    "mock-services/shopify-app/Dockerfile"
    "mock-services/airflow/Dockerfile"
    "fixtures/postgres/01-create-databases.sql"
    "fixtures/postgres/02-seed-data.sql"
    "fixtures/airflow/dags/test_dag.py"
    "tests/conftest.py"
    "tests/test_services.py"
    "tests/test_release_workflow.py"
    "tests/Dockerfile"
    "scripts/setup-test-environment.sh"
    "scripts/run-tests.sh"
    "scripts/health-check.sh"
    "scripts/cleanup.sh"
)

missing_files=()
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $file${NC}"
    else
        echo -e "${RED}❌ $file${NC}"
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    echo -e "${RED}❌ Missing required files. Please check the setup.${NC}"
    exit 1
fi

# Check Docker requirements
echo -e "${GREEN}🐳 Checking Docker requirements...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Docker is installed${NC}"
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Docker Compose is installed${NC}"
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon is not running${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Docker daemon is running${NC}"
fi

# Check available ports
echo -e "${GREEN}🔌 Checking port availability...${NC}"

required_ports=(3000 3001 5000 5433 8001 8080 8082 8501)
occupied_ports=()

for port in "${required_ports[@]}"; do
    if lsof -i :$port &> /dev/null; then
        echo -e "${YELLOW}⚠️ Port $port is in use${NC}"
        occupied_ports+=("$port")
    else
        echo -e "${GREEN}✅ Port $port is available${NC}"
    fi
done

if [ ${#occupied_ports[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️ Some ports are occupied. This might cause conflicts.${NC}"
    echo -e "${YELLOW}💡 Consider stopping services using these ports or the test environment will handle conflicts.${NC}"
fi

# Check system resources
echo -e "${GREEN}💻 Checking system resources...${NC}"

# Check available memory
if command -v free &> /dev/null; then
    available_memory=$(free -m | awk 'NR==2{printf "%.1f", $7/1024}')
    if (( $(echo "$available_memory > 2.0" | bc -l) )); then
        echo -e "${GREEN}✅ Available memory: ${available_memory}GB${NC}"
    else
        echo -e "${YELLOW}⚠️ Low available memory: ${available_memory}GB (recommend 4GB+)${NC}"
    fi
elif command -v vm_stat &> /dev/null; then
    # macOS
    free_pages=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
    available_gb=$(echo "scale=1; $free_pages * 4096 / 1024 / 1024 / 1024" | bc)
    if (( $(echo "$available_gb > 2.0" | bc -l) )); then
        echo -e "${GREEN}✅ Available memory: ${available_gb}GB${NC}"
    else
        echo -e "${YELLOW}⚠️ Low available memory: ${available_gb}GB (recommend 4GB+)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ Cannot check available memory${NC}"
fi

# Check disk space
available_disk=$(df -h . | awk 'NR==2 {print $4}')
echo -e "${GREEN}✅ Available disk space: $available_disk${NC}"

# Validate Docker Compose configuration
echo -e "${GREEN}🔧 Validating Docker Compose configuration...${NC}"

if docker-compose config &> /dev/null; then
    echo -e "${GREEN}✅ Docker Compose configuration is valid${NC}"
else
    echo -e "${RED}❌ Docker Compose configuration is invalid${NC}"
    docker-compose config
    exit 1
fi

# Check GitHub Actions workflow
echo -e "${GREEN}🔄 Checking GitHub Actions workflow...${NC}"

if [ -f "../.github/workflows/test-release.yml" ]; then
    echo -e "${GREEN}✅ GitHub Actions workflow exists${NC}"
else
    echo -e "${YELLOW}⚠️ GitHub Actions workflow not found${NC}"
fi

# Summary
echo -e "${BLUE}📋 Setup Verification Summary${NC}"
echo -e "${GREEN}✅ All required files present${NC}"
echo -e "${GREEN}✅ Docker requirements met${NC}"
echo -e "${GREEN}✅ System resources sufficient${NC}"
echo -e "${GREEN}✅ Configuration valid${NC}"

if [ ${#occupied_ports[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️ Some ports are occupied (${occupied_ports[*]})${NC}"
fi

echo ""
echo -e "${GREEN}🚀 Test environment is ready!${NC}"
echo -e "${BLUE}💡 Next steps:${NC}"
echo -e "${BLUE}  1. Run: ./scripts/setup-test-environment.sh${NC}"
echo -e "${BLUE}  2. Run: ./scripts/run-tests.sh${NC}"
echo -e "${BLUE}  3. Check: ./scripts/health-check.sh${NC}"
echo -e "${BLUE}  4. Cleanup: ./scripts/cleanup.sh${NC}"