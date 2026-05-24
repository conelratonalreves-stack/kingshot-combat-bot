#!/bin/bash
# Deploy minecraft_rpi folder to Raspberry Pi and run installer remotely.
# Usage: ./deploy_minecraft_to_rpi.sh

set -euo pipefail

REMOTE_USER="${REMOTE_USER:-knycat}"
REMOTE_HOST="${REMOTE_HOST:-192.168.1.141}"
REMOTE_BASE="${REMOTE_BASE:-/home/knycat}"
REMOTE_PATH="${REMOTE_BASE}/minecraft_rpi"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Deploy Minecraft Forge installer to Raspberry Pi${NC}"
echo "Target: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"

ssh "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p '${REMOTE_PATH}'"
scp -r ./minecraft_rpi/* "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/"

echo -e "${GREEN}Files uploaded.${NC}"
echo -e "${YELLOW}Running remote installer...${NC}"

ssh "${REMOTE_USER}@${REMOTE_HOST}" "cd '${REMOTE_PATH}' && chmod +x install_minecraft_forge_rpi.sh && sudo ./install_minecraft_forge_rpi.sh"

echo -e "${GREEN}Done. Server installed on Raspberry Pi.${NC}"
