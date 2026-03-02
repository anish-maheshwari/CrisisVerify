#!/bin/bash
# =============================================================================
# CrisisVerify — EC2 Full-Stack Deployment Script
# Ubuntu 22.04 LTS | Docker + Apache2 Reverse Proxy
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
# =============================================================================
set -e

REPO_URL="https://github.com/anish-maheshwari/CrisisVerify"   # <-- update this
APP_DIR="/var/www/crisis"
APACHE_CONF="/etc/apache2/sites-available/crisis.conf"

echo ""
echo "============================================="
echo "  CrisisVerify EC2 Setup"
echo "============================================="

# ── 1. System update ──────────────────────────────────────────────────────────
echo "[1/6] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# ── 2. Install Docker ─────────────────────────────────────────────────────────
echo "[2/6] Installing Docker..."
if ! command -v docker &> /dev/null; then
    sudo apt-get install -y ca-certificates curl gnupg lsb-release
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo usermod -aG docker $USER
    echo "Docker installed."
else
    echo "Docker already installed, skipping."
fi

# Install docker-compose v2 standalone (for 'docker-compose' command)
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# ── 3. Install Apache2 ────────────────────────────────────────────────────────
echo "[3/6] Installing Apache2..."
sudo apt-get install -y apache2
sudo a2enmod proxy proxy_http proxy_wstunnel headers rewrite
sudo systemctl enable apache2

# ── 4. Pull code ──────────────────────────────────────────────────────────────
echo "[4/6] Cloning/updating repository..."
if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR"
    git pull origin main
    echo "Repository updated."
else
    sudo mkdir -p "$APP_DIR"
    sudo chown $USER:$USER "$APP_DIR"
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
    echo "Repository cloned."
fi

# ── 5. Set up .env ────────────────────────────────────────────────────────────
echo "[5/6] Checking .env file..."
if [ ! -f "$APP_DIR/backend/.env" ]; then
    echo ""
    echo "  ┌─────────────────────────────────────────────────┐"
    echo "  │  .env file NOT FOUND. Please enter API keys:   │"
    echo "  └─────────────────────────────────────────────────┘"
    read -p "  Enter GEMINI_API_KEY: " GEMINI_KEY
    read -p "  Enter SERPER_API_KEY: " SERPER_KEY
    cat > "$APP_DIR/backend/.env" <<EOF
GEMINI_API_KEY=${GEMINI_KEY}
SERPER_API_KEY=${SERPER_KEY}
EOF
    echo "  .env file created."
else
    echo "  .env already exists, skipping."
fi

# ── 6. Configure Apache2 reverse proxy ───────────────────────────────────────
echo "[6/6] Configuring Apache2 virtual host..."
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || hostname -I | awk '{print $1}')

sudo tee "$APACHE_CONF" > /dev/null <<'APACHECONF'
<VirtualHost *:80>
    ServerAdmin webmaster@localhost
    # Route /api/* → FastAPI backend
    ProxyPreserveHost On
    ProxyPass        /api  http://127.0.0.1:8000/api
    ProxyPassReverse /api  http://127.0.0.1:8000/api

    # Route /* → Next.js frontend
    ProxyPass        /     http://127.0.0.1:3000/
    ProxyPassReverse /     http://127.0.0.1:3000/

    # WebSocket support (Next.js HMR, optional)
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/?(.*) ws://127.0.0.1:3000/$1 [P,L]

    ErrorLog  ${APACHE_LOG_DIR}/crisis_error.log
    CustomLog ${APACHE_LOG_DIR}/crisis_access.log combined
</VirtualHost>
APACHECONF

sudo a2dissite 000-default.conf 2>/dev/null || true
sudo a2ensite crisis.conf
sudo apache2ctl configtest && sudo systemctl restart apache2
echo "Apache2 configured."

# ── 7. Start containers ────────────────────────────────────────────────────────
echo ""
echo "[7/7] Starting Docker containers..."
cd "$APP_DIR"
docker-compose down 2>/dev/null || true
docker-compose up --build -d
echo "Containers started."

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "============================================="
echo "  Deployment complete!"
echo "  App is accessible at: http://${PUBLIC_IP}"
echo "  Backend API at:       http://${PUBLIC_IP}/api/v1/analyze"
echo "============================================="
echo ""
echo "  Useful commands:"
echo "    docker-compose logs -f          # live logs"
echo "    docker-compose ps               # container status"
echo "    sudo systemctl status apache2   # apache status"
