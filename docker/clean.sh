#!/usr/bin/env bash
#
# MedFabric Docker Clean Script
# Removes containers, images, and volumes (for cleanup)
#
# Usage: bash docker/clean.sh [--all] [--confirm]
#

set -euo pipefail

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_header() {
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}$1${NC}"
    echo -e "${RED}========================================${NC}"
}

print_warning() {
    echo -e "${RED}[!]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

# Parse arguments
CLEAN_ALL=false
NO_CONFIRM=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            CLEAN_ALL=true
            shift
            ;;
        --confirm)
            NO_CONFIRM=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

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

print_header "MedFabric Docker Cleanup"

# Show what will be deleted
print_warning "This will delete MedFabric Docker resources"
echo ""

if [ "$CLEAN_ALL" = true ]; then
    echo "Will remove:"
    echo "  • All containers (dev, prod, tailscale)"
    echo "  • Images"
    echo "  • Volumes"
else
    echo "Will remove:"
    echo "  • Containers only"
    echo ""
    echo "Use --all to also remove images and volumes"
fi

echo ""

# Confirm
if [ "$NO_CONFIRM" = false ]; then
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cleanup cancelled"
        exit 0
    fi
fi

# Stop and remove containers
print_info "Removing containers..."
$DC_CMD down || true

if [ "$CLEAN_ALL" = true ]; then
    # Remove images
    print_info "Removing images..."
    docker rmi $(docker images | grep medfabric | awk '{print $3}') 2>/dev/null || true
    
    # Remove volumes
    print_info "Removing volumes..."
    docker volume rm $(docker volume ls | grep medfabric | awk '{print $2}') 2>/dev/null || true
    
    print_success "All MedFabric resources removed"
    echo ""
    echo "To reinstall, run:"
    echo "  bash docker/build.sh"
    echo "  bash docker/run-dev.sh"
else
    print_success "Containers removed"
    echo ""
    echo "Images and volumes still exist. To remove them too:"
    echo "  bash docker/clean.sh --all --confirm"
fi
