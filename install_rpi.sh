#!/bin/bash
# Kingshot Bot Deployment Script for Raspberry Pi 5
# This script installs and configures the bot on a Raspberry Pi

set -e

echo "================================"
echo "Kingshot Bot - RPi5 Installation"
echo "================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo -e "${YELLOW}Warning: This may not be a Raspberry Pi${NC}"
fi

# Step 1: Update system
echo -e "${GREEN}[1/5] Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Step 2: Install Python dependencies
echo -e "${GREEN}[2/5] Installing Python and pip...${NC}"
sudo apt-get install -y python3 python3-pip python3-venv

# Step 3: Create virtual environment
echo -e "${GREEN}[3/5] Creating Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Step 4: Activate venv and install dependencies
echo -e "${GREEN}[4/5] Installing Python packages...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Step 5: Setup .env file
echo -e "${GREEN}[5/5] Setting up configuration...${NC}"
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    read -p "Enter your Discord Bot Token: " TOKEN
    echo "DISCORD_TOKEN=$TOKEN" > .env
    echo -e "${GREEN}✓ .env file created${NC}"
else
    echo "✓ .env file already exists"
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Installation completed!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "To start the bot:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "To run the bot in the background (with systemd):"
echo "  sudo cp kingshot-bot.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable kingshot-bot"
echo "  sudo systemctl start kingshot-bot"
echo ""
echo "To view logs:"
echo "  journalctl -u kingshot-bot -f"
echo ""
