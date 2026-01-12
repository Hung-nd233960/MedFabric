#!/usr/bin/env bash
#
# MedFabric Docker Logs Script
# View logs from running containers
#
# Usage: bash docker/logs.sh [dev|prod] [-f]
#

set -euo pipefail

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${YELLOW}[*]${NC} $1"
}

# Parse arguments
PROFILE="${1:-dev}"
FOLLOW=""

if [[ "$2" == "-f" ]]; then
    FOLLOW="-f"
fi

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
        print_info "Showing logs for development container..."
        $DC_CMD --profile dev logs $FOLLOW app-dev
        ;;
    prod)
        print_info "Showing logs for production container..."
        $DC_CMD --profile prod logs $FOLLOW app-prod
        ;;
    *)
        echo "Usage: bash docker/logs.sh [dev|prod] [-f]"
        echo ""
        echo "Examples:"
        echo "  bash docker/logs.sh dev         # Show dev logs"
        echo "  bash docker/logs.sh dev -f      # Follow dev logs"
        echo "  bash docker/logs.sh prod        # Show prod logs"
        echo "  bash docker/logs.sh prod -f     # Follow prod logs"
        exit 1
        ;;
esac
