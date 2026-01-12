#!/usr/bin/env bash
#
# MedFabric Docker Production Run Script
# Starts the application in production mode with Tailscale networking
#
# Usage: bash docker/run-prod.sh
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

print_header "MedFabric Docker Production Environment"

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

# Check if TS_AUTH_KEY is set
if ! grep -q "TS_AUTH_KEY=" "$PROJECT_ROOT/.env" || grep "TS_AUTH_KEY=$" "$PROJECT_ROOT/.env" > /dev/null; then
    print_error "Tailscale Auth Key (TS_AUTH_KEY) not configured"
    echo "Edit .env file and add: TS_AUTH_KEY=<your-tailscale-key>"
    echo "Get your key from: https://login.tailscale.com/admin/authkeys"
    exit 1
fi

print_success "Tailscale Auth Key configured"

# Check if image exists
print_info "Checking if image is built..."
if ! docker images | grep -q "medfabric"; then
    print_error "Docker image not found"
    echo "Run: bash docker/build.sh"
    exit 1
fi

print_success "Docker image found"

# Check if container is already running
if docker ps | grep -q "medfabric_app_prod"; then
    print_info "Container is already running"
    read -p "Restart container? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Stopping existing container..."
        $DC_CMD --profile prod down
    else
        echo "Use: bash docker/logs-prod.sh to view logs"
        exit 0
    fi
fi

# Check for required capabilities
print_info "Checking system capabilities..."
if ! grep -q "CAP_NET_ADMIN" /proc/sys/kernel/ns_last_pid; then
    print_info "Note: Running without CAP_NET_ADMIN, Tailscale may have limited functionality"
fi

# Start in production mode
print_header "Starting Production Container"

print_info "Starting container with production profile..."
print_info "Container name: medfabric_app_prod"
print_info "Networking: Tailscale VPN"
echo ""

# Run in detached mode
$DC_CMD --profile prod up -d

print_header "Container Started"

# Wait for container to be ready
print_info "Waiting for container to be healthy..."
sleep 10

if docker ps | grep -q "medfabric_app_prod"; then
    print_success "Production container is running"
    echo ""
    echo "Container information:"
    docker ps | grep medfabric_app_prod
    echo ""
    echo "Useful commands:"
    echo "  View logs: bash docker/logs-prod.sh"
    echo "  Stop: bash docker/stop-prod.sh"
    echo "  Restart: bash docker/restart-prod.sh"
else
    print_error "Container failed to start"
    echo "View logs with: bash docker/logs-prod.sh"
    exit 1
fi
