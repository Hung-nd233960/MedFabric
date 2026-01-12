#!/usr/bin/env bash
#
# MedFabric Docker Build Script
# Builds Docker image for the MedFabric application
#
# Usage: bash docker/build.sh [--force] [--no-cache]
#

set -euo pipefail

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_header() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}"
}

print_info() {
    echo -e "${YELLOW}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Parse arguments
NO_CACHE=""
FORCE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --force)
            FORCE="--force-rm"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: bash docker/build.sh [--force] [--no-cache]"
            exit 1
            ;;
    esac
done

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

print_header "MedFabric Docker Build"

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    print_error "Docker daemon is not running"
    echo "Start Docker with: sudo systemctl start docker"
    exit 1
fi

print_success "Docker daemon is running"

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    print_error ".env file not found"
    echo "Run: bash docker/setup-env.sh"
    exit 1
fi

print_success ".env file exists"

# Determine docker-compose command
if command -v docker-compose &> /dev/null; then
    DC_CMD="docker-compose"
else
    DC_CMD="docker compose"
fi

# Check Dockerfile
if [ ! -f "$PROJECT_ROOT/docker/app.Dockerfile" ]; then
    print_error "Dockerfile not found at docker/app.Dockerfile"
    exit 1
fi

print_success "Dockerfile found"

# Build image
print_header "Building Docker Image"

print_info "Building with: $DC_CMD build"
print_info "Build options: ${NO_CACHE:-(none)} ${FORCE:-(none)}"

if $DC_CMD build $NO_CACHE $FORCE --progress=plain; then
    print_success "Build completed successfully"
else
    print_error "Build failed"
    exit 1
fi

# Verify image
print_header "Verifying Image"

if docker images | grep -q "medfabric"; then
    print_success "MedFabric image exists"
    docker images | grep medfabric
else
    print_error "MedFabric image not found"
    exit 1
fi

print_header "Build Complete!"
echo ""
echo "Next steps:"
echo "1. Run development: bash docker/run-dev.sh"
echo "2. Or run production: bash docker/run-prod.sh"
echo ""
echo "To rebuild without cache:"
echo "  bash docker/build.sh --no-cache"
