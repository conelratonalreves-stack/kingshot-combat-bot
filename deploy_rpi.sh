#!/bin/bash
# Deploy Kingshot bot to Raspberry Pi
# Usage: ./deploy_rpi.sh

REMOTE_USER="knycat"
REMOTE_HOST="192.168.1.141"
REMOTE_PATH="/home/knycat/kingshot-bot"
SSH_KEY=""  # Leave empty to use password auth

echo "================================"
echo "Deploying to Raspberry Pi"
echo "================================"
echo "Remote: $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH"
echo ""

# Check if SSH is available
if ! command -v ssh &> /dev/null; then
    echo "❌ SSH not found. Please install OpenSSH."
    exit 1
fi

# Create remote directory if it doesn't exist
echo "[1/4] Creating remote directory..."
ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_PATH"

# Copy project files
echo "[2/4] Copying project files..."
scp -r . "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/"

# Run installation script
echo "[3/4] Running installation script..."
ssh "$REMOTE_USER@$REMOTE_HOST" "cd $REMOTE_PATH && chmod +x install_rpi.sh && ./install_rpi.sh"

# Setup systemd service
echo "[4/4] Setting up systemd service..."
ssh "$REMOTE_USER@$REMOTE_HOST" "sudo cp $REMOTE_PATH/kingshot-bot.service /etc/systemd/system/ && sudo systemctl daemon-reload"

echo ""
echo "✓ Deployment completed!"
echo ""
echo "Next steps:"
echo "1. SSH into the Pi: ssh $REMOTE_USER@$REMOTE_HOST"
echo "2. Add your Discord token to .env file in $REMOTE_PATH"
echo "3. Start the bot with: sudo systemctl start kingshot-bot"
echo "4. Check status with: sudo systemctl status kingshot-bot"
echo ""
