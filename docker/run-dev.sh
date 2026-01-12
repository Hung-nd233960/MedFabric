#!/usr/bin/env bash
#
# MedFabric Docker Development Run Script
# Starts the application in development mode with hot-reloading
#
# Usage: bash docker/run-dev.sh
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

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

print_header "MedFabric Docker Development Environment"

# Determine docker-compose command
if command -v docker-compose &> /dev/null; then
    DC_CMD="docker-compose"
else
    DC_CMD="docker compose"
fi

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    print_error ".env file not found"
    echo "Run: bash docker/setup-env.sh"
    exit 1
fi

print_success ".env file exists"

# Check if image exists
print_info "Checking if image is built..."
if ! docker images | grep -q "medfabric"; then
    print_error "Docker image not found"
    echo "Run: bash docker/build.sh"
    exit 1
fi

print_success "Docker image found"

# Check if container is already running
if docker ps | grep -q "medfabric_app_dev"; then
    print_info "Container is already running"
    print_info "Stopping existing container..."
    $DC_CMD --profile dev down
fi

# Start in development mode
print_header "Starting Development Container"

print_info "Starting container with development profile..."
print_info "Access the application at: http://localhost:8501"
print_info "Press Ctrl+C to stop the container"
echo ""

# Run with interactive output
$DC_CMD --profile dev up --remove-orphans

print_header "Container Stopped"
