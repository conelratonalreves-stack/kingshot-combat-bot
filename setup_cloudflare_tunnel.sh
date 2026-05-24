#!/bin/bash
# Cloudflare Tunnel setup for billing panel on Raspberry Pi
# Domain: mkmagency.es
# Hostnames:
#   - www.facturacion.mkmagency.es (primary)
#   - facturacion.mkmagency.es (alias)
# Local service: http://localhost:8085

set -euo pipefail

echo "=========================================="
echo "Cloudflare Tunnel Setup (Raspberry Pi)"
echo "=========================================="
echo

echo "[1/7] Installing cloudflared..."
ARCHIVE="cloudflared-linux-arm64.tgz"
wget -q "https://github.com/cloudflare/cloudflared/releases/latest/download/${ARCHIVE}" -O "$ARCHIVE"
tar -xzf "$ARCHIVE"
sudo mv cloudflared /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared
rm -f "$ARCHIVE"
echo "OK: cloudflared installed"
echo

echo "[2/7] Authenticating Cloudflare (login)..."
echo "A browser URL will be printed. Complete login in your browser."
cloudflared tunnel login

echo "[3/7] Checking cert.pem..."
CERT_PATH="$HOME/.cloudflared/cert.pem"
if [ ! -f "$CERT_PATH" ]; then
  echo "ERROR: cert.pem not found at $CERT_PATH"
  echo "If Cloudflare downloaded it to your PC, copy it to Raspberry with:"
  echo "  scp <path_to_cert.pem> knycat@192.168.1.131:/home/knycat/.cloudflared/cert.pem"
  exit 1
fi
echo "OK: cert.pem found"
echo

echo "[4/7] Creating tunnel..."
TUNNEL_NAME="kingshot-billing-tunnel"
if cloudflared tunnel list | awk '{print $2}' | grep -qx "$TUNNEL_NAME"; then
  echo "Tunnel already exists, reusing it..."
else
  cloudflared tunnel create "$TUNNEL_NAME"
fi

TUNNEL_UUID=$(cloudflared tunnel list | awk -v name="$TUNNEL_NAME" '$2==name {print $1}')
if [ -z "$TUNNEL_UUID" ]; then
  echo "ERROR: Could not resolve tunnel UUID"
  exit 1
fi
echo "OK: tunnel UUID = $TUNNEL_UUID"
echo

echo "[5/7] Configuring tunnel routes and config file..."
cloudflared tunnel route dns "$TUNNEL_NAME" "www.facturacion.mkmagency.es" || true
cloudflared tunnel route dns "$TUNNEL_NAME" "facturacion.mkmagency.es" || true

mkdir -p "$HOME/.cloudflared"
cat > "$HOME/.cloudflared/config.yml" <<EOF
tunnel: $TUNNEL_UUID
credentials-file: $HOME/.cloudflared/$TUNNEL_UUID.json

ingress:
  - hostname: www.facturacion.mkmagency.es
    service: http://localhost:8085
  - hostname: facturacion.mkmagency.es
    service: http://localhost:8085
  - service: http_status:404
EOF

echo "OK: config.yml written"
echo

echo "[6/7] Creating systemd service..."
sudo tee /etc/systemd/system/cloudflared.service > /dev/null <<EOF
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=knycat
ExecStart=/usr/local/bin/cloudflared tunnel --config /home/knycat/.cloudflared/config.yml run
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable cloudflared
sudo systemctl restart cloudflared

echo "[7/7] Verifying service..."
sudo systemctl --no-pager --full status cloudflared | head -n 12 || true
echo

echo "=========================================="
echo "Setup finished"
echo "=========================================="
echo "Local panel:  http://192.168.1.131:8085"
echo "Remote panel: https://www.facturacion.mkmagency.es"
echo "Alias panel:  https://facturacion.mkmagency.es"
echo
