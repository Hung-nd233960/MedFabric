#!/usr/bin/env bash
set -euo pipefail

### CONFIG ###
REPO_URL=""
REPO_DIR="$HOME/your-repo"

echo "[*] Updating system..."
sudo apt-get update -y && sudo apt-get upgrade -y

echo "[*] Installing essentials..."
sudo apt-get install -y git curl ca-certificates apt-transport-https software-properties-common

### --- Make Ubuntu Desktop behave like a server --- ###
echo "[*] Disabling GUI crash popups (apport)..."
echo "enabled=0" | sudo tee /etc/default/apport >/dev/null
sudo systemctl disable --now apport.service || true

echo "[*] Disabling daily apt update popups..."
sudo systemctl disable --now apt-daily.timer apt-daily-upgrade.timer || true

echo "[*] Preventing sleep/suspend/hibernate..."
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target

echo "[*] Disabling screen blanking..."
gsettings set org.gnome.desktop.session idle-delay 0 || true

echo "[*] Ensuring SSH is installed and enabled..."
sudo apt-get install -y openssh-server
sudo systemctl enable --now ssh

### --- Install Docker (newer official method) --- ###
echo "[*] Installing Docker..."
if ! command -v docker &>/dev/null; then
    # Remove old versions
    sudo apt-get remove -y docker docker-engine docker.io containerd runc || true

    # Add Docker’s official GPG key
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc

    # Add repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
      https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo ${UBUNTU_CODENAME:-$VERSION_CODENAME}) stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add user to docker group
    sudo usermod -aG docker "$USER"
    echo ">>> You must log out and back in for Docker group changes to take effect."
fi

### --- Clone Repo --- ###
echo "[*] Cloning repo..."
if [ ! -d "$REPO_DIR" ]; then
    git clone "$REPO_URL" "$REPO_DIR"
else
    echo "Repo already exists at $REPO_DIR, pulling latest..."
    git -C "$REPO_DIR" pull
fi

echo "[*] Setup complete. Reboot recommended."
