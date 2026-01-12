#!/usr/bin/env bash
#
# MedFabric Docker Stop Script
# Stops running containers
#
# Usage: bash docker/stop.sh [dev|prod]
#

set -euo pipefail

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() {
    echo -e "${YELLOW}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

# Parse arguments
PROFILE="${1:-dev}"

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

case $PROFILE in
    dev)
        print_info "Stopping development container..."
        $DC_CMD --profile dev down
        print_success "Development container stopped"
        ;;
    prod)
        print_info "Stopping production container..."
        $DC_CMD --profile prod down
        print_success "Production container stopped"
        ;;
    all)
        print_info "Stopping all containers..."
        $DC_CMD down
        print_success "All containers stopped"
        ;;
    *)
        echo "Usage: bash docker/stop.sh [dev|prod|all]"
        exit 1
        ;;
esac
