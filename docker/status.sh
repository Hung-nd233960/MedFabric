#!/usr/bin/env bash
#
# MedFabric Docker Status Script
# Shows status of containers and images
#
# Usage: bash docker/status.sh
#

set -euo pipefail

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}"
}

print_section() {
    echo -e "${BLUE}$1${NC}"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Determine docker-compose command
if command -v docker-compose &> /dev/null; then
    DC_CMD="docker-compose"
else
    DC_CMD="docker compose"
fi

print_header "MedFabric Docker Status"

# Check Docker daemon
print_section "Docker Daemon Status:"
if docker ps > /dev/null 2>&1; then
    echo "  ✓ Docker is running"
else
    echo "  ✗ Docker is not running"
    exit 1
fi

# Show Docker version
print_section "Docker Version:"
docker --version
$DC_CMD --version

# Show MedFabric images
print_section "MedFabric Images:"
docker images | grep -i medfabric || echo "  No images found"

# Show running containers
print_section "Running Containers:"
docker ps --filter "name=medfabric" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "  No containers running"

# Show all containers (including stopped)
print_section "All MedFabric Containers:"
docker ps -a --filter "name=medfabric" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "  No containers found"

# Show volumes
print_section "MedFabric Volumes:"
docker volume ls | grep -i medfabric || echo "  No volumes found"

# Show docker-compose config
print_section "Docker Compose Configuration:"
echo "  Project root: $PROJECT_ROOT"
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "  ✓ .env file exists"
else
    echo "  ✗ .env file missing"
fi

if [ -f "$PROJECT_ROOT/docker-compose.yaml" ]; then
    echo "  ✓ docker-compose.yaml exists"
else
    echo "  ✗ docker-compose.yaml missing"
fi

# Validate docker-compose
print_section "Configuration Validation:"
if $DC_CMD config > /dev/null 2>&1; then
    echo "  ✓ docker-compose.yaml is valid"
else
    echo "  ✗ docker-compose.yaml has errors"
fi

print_header "Status Check Complete"
