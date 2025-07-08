#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Health Check - Test Environment${NC}"

# Change to test environment directory
cd "$(dirname "$0")/.."

# Health check function
check_service() {
    local service_name="$1"
    local url="$2"
    local expected_status="$3"
    
    echo -n -e "${YELLOW}Checking $service_name...${NC}"
    
    if curl -f -s "$url" > /dev/null 2>&1; then
        echo -e " ${GREEN}✅ Healthy${NC}"
        return 0
    else
        echo -e " ${RED}❌ Unhealthy${NC}"
        return 1
    fi
}

# Check Docker services are running
echo -e "${BLUE}🐳 Docker Services Status:${NC}"
services=("test-postgres" "test-app1" "test-app2" "test-shopify-app" "test-nginx" "test-airflow" "test-registry")
for service in "${services[@]}"; do
    if docker-compose ps | grep -q "$service.*Up"; then
        echo -e "${GREEN}✅ $service is running${NC}"
    else
        echo -e "${RED}❌ $service is not running${NC}"
    fi
done

echo ""
echo -e "${BLUE}🌐 Service Health Checks:${NC}"

# Health check URLs
health_checks=(
    "App1 (FastAPI):http://localhost:8001/health"
    "App1 (Streamlit):http://localhost:8501"
    "App2 (React):http://localhost:3000/health"
    "Shopify App:http://localhost:3001/health"
    "Nginx Proxy:http://localhost:8080/health"
    "Registry:http://localhost:5000/v2/"
)

healthy_count=0
total_count=${#health_checks[@]}

for check in "${health_checks[@]}"; do
    IFS=':' read -r name url <<< "$check"
    if check_service "$name" "$url"; then
        ((healthy_count++))
    fi
done

# Database health check
echo -n -e "${YELLOW}Checking PostgreSQL...${NC}"
if docker-compose exec -T test-postgres pg_isready -U test_user -d test_db > /dev/null 2>&1; then
    echo -e " ${GREEN}✅ Healthy${NC}"
    ((healthy_count++))
    ((total_count++))
else
    echo -e " ${RED}❌ Unhealthy${NC}"
    ((total_count++))
fi

# Airflow health check (special case as it takes longer to start)
echo -n -e "${YELLOW}Checking Airflow...${NC}"
if curl -f -s "http://localhost:8082/health" > /dev/null 2>&1; then
    echo -e " ${GREEN}✅ Healthy${NC}"
    ((healthy_count++))
    ((total_count++))
else
    echo -e " ${RED}❌ Unhealthy (may still be starting)${NC}"
    ((total_count++))
fi

echo ""
echo -e "${BLUE}📊 Health Summary:${NC}"
echo -e "${GREEN}Healthy: $healthy_count/${total_count}${NC}"

if [ $healthy_count -eq $total_count ]; then
    echo -e "${GREEN}✅ All services are healthy!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some services are unhealthy${NC}"
    echo ""
    echo -e "${YELLOW}💡 Troubleshooting tips:${NC}"
    echo -e "${YELLOW}  • Check service logs: docker-compose logs <service_name>${NC}"
    echo -e "${YELLOW}  • Restart services: docker-compose restart <service_name>${NC}"
    echo -e "${YELLOW}  • View all logs: docker-compose logs${NC}"
    echo -e "${YELLOW}  • Rebuild services: docker-compose up -d --build${NC}"
    exit 1
fi