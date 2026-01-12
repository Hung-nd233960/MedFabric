#!/usr/bin/env bash
#
# MedFabric Docker Environment Setup Script
# Configures environment variables and validates setup
#
# Usage: bash docker/setup-env.sh
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

print_header "MedFabric Docker Environment Setup"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Run: bash docker/install-docker.sh"
    exit 1
fi

print_success "Docker is installed"

# Check if .env exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    print_info ".env file already exists"
    read -p "Do you want to reconfigure? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Skipping .env configuration"
    else
        create_env=true
    fi
else
    create_env=true
fi

if [ "${create_env:-false}" = true ]; then
    print_info "Creating .env file from example..."
    cp "$PROJECT_ROOT/examples/example.env" "$PROJECT_ROOT/.env"
    
    print_info "Configuring environment variables..."
    
    # Configure DATABASE_URL
    read -p "Enter DATABASE_URL [sqlite:///./medfabric.db]: " DATABASE_URL
    DATABASE_URL=${DATABASE_URL:-"sqlite:///./medfabric.db"}
    
    # Configure Tailscale (optional for development)
    read -p "Enter Tailscale Auth Key (optional, leave empty for dev): " TS_AUTH_KEY
    TS_AUTH_KEY=${TS_AUTH_KEY:-""}
    
    # Update .env file
    sed -i "s|DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|g" "$PROJECT_ROOT/.env"
    if [ -n "$TS_AUTH_KEY" ]; then
        sed -i "s|TS_AUTH_KEY=.*|TS_AUTH_KEY=$TS_AUTH_KEY|g" "$PROJECT_ROOT/.env"
    fi
    
    print_success ".env file created/updated"
fi

# Display configuration
print_header "Current Configuration"
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "=== .env Configuration ==="
    cat "$PROJECT_ROOT/.env" | grep -v "^#" | grep -v "^$"
    echo ""
fi

# Check data_sets directory
if [ ! -d "$PROJECT_ROOT/data_sets" ]; then
    print_info "Creating data_sets directory..."
    mkdir -p "$PROJECT_ROOT/data_sets"
    print_success "data_sets directory created"
else
    print_success "data_sets directory exists"
fi

# Check .streamlit directory
if [ ! -d "$PROJECT_ROOT/.streamlit" ]; then
    print_info "Creating .streamlit directory..."
    mkdir -p "$PROJECT_ROOT/.streamlit"
fi

# Create Streamlit config if missing
if [ ! -f "$PROJECT_ROOT/.streamlit/config.toml" ]; then
    print_info "Creating Streamlit configuration..."
    cat > "$PROJECT_ROOT/.streamlit/config.toml" << 'EOF'
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"

[client]
showErrorDetails = true

[logger]
level = "info"

[server]
headless = true
runOnSave = true
maxUploadSize = 200
EOF
    print_success "Streamlit configuration created"
else
    print_success "Streamlit configuration exists"
fi

# Verify Docker daemon
print_header "Docker Verification"
print_info "Testing Docker daemon..."
if docker ps > /dev/null 2>&1; then
    print_success "Docker daemon is running"
else
    print_error "Docker daemon is not running. Start it with: sudo systemctl start docker"
    exit 1
fi

# Check Docker Compose
if command -v docker-compose &> /dev/null; then
    DC_CMD="docker-compose"
else
    DC_CMD="docker compose"
fi

print_success "Using: $DC_CMD"

# Validate docker-compose file
print_info "Validating docker-compose configuration..."
if $DC_CMD config > /dev/null 2>&1; then
    print_success "docker-compose.yaml is valid"
else
    print_error "docker-compose.yaml has errors"
    $DC_CMD config
    exit 1
fi

print_header "Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Verify data_sets folder contains CT scan data"
echo "2. Run: bash docker/build.sh"
echo "3. Run: bash docker/run-dev.sh"
echo ""
echo "For production with Tailscale networking:"
echo "  bash docker/run-prod.sh"
