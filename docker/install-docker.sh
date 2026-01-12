#!/usr/bin/env bash
#
# MedFabric Docker Installation Script
# Installs Docker and Docker Compose on Linux systems
#
# Usage: bash docker/install-docker.sh
#

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Utility functions
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

# Check OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        print_error "Cannot detect OS. Exiting."
        exit 1
    fi
}

# Check if already installed
check_docker() {
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        print_success "Docker already installed: $DOCKER_VERSION"
        return 0
    fi
    return 1
}

check_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        DC_VERSION=$(docker-compose --version)
        print_success "Docker Compose already installed: $DC_VERSION"
        return 0
    fi
    return 1
}

# Install Docker on Ubuntu/Debian
install_docker_debian() {
    print_header "Installing Docker (Debian/Ubuntu)"
    
    print_info "Updating system packages..."
    sudo apt-get update -y
    
    print_info "Installing prerequisites..."
    sudo apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        apt-transport-https \
        software-properties-common
    
    print_info "Adding Docker GPG key..."
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    print_info "Adding Docker repository..."
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    print_info "Updating package index..."
    sudo apt-get update -y
    
    print_info "Installing Docker..."
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    print_success "Docker installation complete"
}

# Install Docker on Fedora/RHEL/CentOS
install_docker_fedora() {
    print_header "Installing Docker (Fedora/RHEL/CentOS)"
    
    print_info "Installing prerequisites..."
    sudo dnf install -y dnf-plugins-core
    
    print_info "Adding Docker repository..."
    sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
    
    print_info "Installing Docker..."
    sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    print_success "Docker installation complete"
}

# Install Docker Compose standalone
install_docker_compose_standalone() {
    print_header "Installing Docker Compose (standalone)"
    
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d'"' -f4)
    
    print_info "Latest Docker Compose version: $DOCKER_COMPOSE_VERSION"
    
    print_info "Downloading Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    
    print_info "Making it executable..."
    sudo chmod +x /usr/local/bin/docker-compose
    
    print_info "Creating symlink..."
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose || true
    
    print_success "Docker Compose installation complete"
}

# Post-install setup
post_install_setup() {
    print_header "Post-Installation Setup"
    
    print_info "Starting Docker daemon..."
    sudo systemctl start docker || true
    
    print_info "Enabling Docker service..."
    sudo systemctl enable docker || true
    
    print_info "Adding current user to docker group..."
    sudo usermod -aG docker "$USER" || true
    
    print_info "Verifying Docker installation..."
    docker --version
    docker-compose --version || docker compose --version
    
    print_success "Docker setup complete"
    echo -e "${YELLOW}Note: You may need to log out and log back in for group changes to take effect.${NC}"
    echo -e "${YELLOW}Or run: newgrp docker${NC}"
}

# Main installation flow
main() {
    print_header "MedFabric Docker Installation"
    
    detect_os
    print_info "Detected OS: $OS (version $VERSION)"
    
    # Check if already installed
    DOCKER_INSTALLED=false
    COMPOSE_INSTALLED=false
    
    if check_docker; then
        DOCKER_INSTALLED=true
    fi
    
    if check_docker_compose; then
        COMPOSE_INSTALLED=true
    fi
    
    # Install if needed
    if [ "$DOCKER_INSTALLED" = false ]; then
        case "$OS" in
            ubuntu|debian)
                install_docker_debian
                ;;
            fedora|rhel|centos)
                install_docker_fedora
                ;;
            *)
                print_error "Unsupported OS: $OS"
                exit 1
                ;;
        esac
    fi
    
    if [ "$COMPOSE_INSTALLED" = false ]; then
        install_docker_compose_standalone
    fi
    
    # Post-install setup
    post_install_setup
    
    print_header "Installation Complete!"
    echo -e "${GREEN}Docker and Docker Compose are ready to use.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Log out and log back in (or run: newgrp docker)"
    echo "2. Run: bash docker/setup-env.sh"
    echo "3. Run: bash docker/build.sh"
    echo "4. Run: bash docker/run-dev.sh"
}

# Run main function
main "$@"
