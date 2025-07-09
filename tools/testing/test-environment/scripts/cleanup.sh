#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧹 Cleaning up Test Environment${NC}"

# Change to test environment directory
cd "$(dirname "$0")/.."

# Stop and remove containers
echo -e "${YELLOW}⏹️ Stopping and removing containers...${NC}"
docker-compose down -v --remove-orphans

# Remove test images
echo -e "${YELLOW}🗑️ Removing test images...${NC}"
docker images --filter "reference=test-environment*" -q | xargs -r docker rmi -f

# Remove unused volumes
echo -e "${YELLOW}📦 Removing unused volumes...${NC}"
docker volume prune -f

# Remove unused networks
echo -e "${YELLOW}🌐 Removing unused networks...${NC}"
docker network prune -f

# Remove build cache
echo -e "${YELLOW}🗂️ Removing build cache...${NC}"
docker builder prune -f

# Clean up local directories
echo -e "${YELLOW}📁 Cleaning up local directories...${NC}"
rm -rf logs/
rm -rf test-results/

echo -e "${GREEN}✅ Test environment cleanup complete!${NC}"