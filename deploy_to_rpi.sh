#!/bin/bash
# Deploy script para transferir el bot a Raspberry Pi
# Uso: ./deploy_to_rpi.sh

set -e

# Configuration
REMOTE_USER="knycat"
REMOTE_HOST="192.168.1.141"
REMOTE_PATH="/home/knycat/kingshot-bot"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Kingshot Bot - Deploy to Raspberry Pi║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "Destino: ${YELLOW}${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}${NC}"
echo ""

# Check if SSH is available
if ! command -v ssh &> /dev/null; then
    echo -e "${RED}❌ SSH no está disponible. Por favor instala OpenSSH.${NC}"
    exit 1
fi

# Check if scp is available
if ! command -v scp &> /dev/null; then
    echo -e "${RED}❌ SCP no está disponible.${NC}"
    exit 1
fi

# Step 1: Create remote directory
echo -e "${BLUE}[1/5] Creando directorio remoto...${NC}"
ssh "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p ${REMOTE_PATH}" 2>/dev/null || {
    echo -e "${YELLOW}⚠️  Espera para reconectar...${NC}"
    sleep 2
}

# Step 2: Copy project files
echo -e "${BLUE}[2/5] Transfiriendo archivos del proyecto...${NC}"
# Excluir .env original, venv, y archivos de sistema
scp -r \
    -o ConnectTimeout=10 \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='.env' \
    . "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Archivos transferidos${NC}"
else
    echo -e "${YELLOW}⚠️  Algunos archivos pueden no haber sido transferidos. Continuando...${NC}"
fi

# Step 3: Copy .env file separately (más seguro)
echo -e "${BLUE}[3/5] Configurando token en servidor remoto...${NC}"
if [ -f ".env" ]; then
    scp -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        .env "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/.env" 2>/dev/null
    echo -e "${GREEN}✓ Token configurado${NC}"
else
    echo -e "${YELLOW}⚠️  Archivo .env no encontrado localmente${NC}"
fi

# Step 4: Run installation script on remote
echo -e "${BLUE}[4/5] Ejecutando script de instalación en RPi...${NC}"
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    "${REMOTE_USER}@${REMOTE_HOST}" << 'EOF'
cd /home/knycat/kingshot-bot

# Crear venv si no existe
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activar venv e instalar dependencias
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "✓ Instalación completada"
EOF

# Step 5: Setup systemd service
echo -e "${BLUE}[5/5] Configurando servicio systemd...${NC}"
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    "${REMOTE_USER}@${REMOTE_HOST}" << 'EOF'
cd /home/knycat/kingshot-bot

# Copiar service file
sudo cp kingshot-bot.service /etc/systemd/system/

# Recargar systemd
sudo systemctl daemon-reload

# Habilitar pero no iniciar (para que el usuario elija)
sudo systemctl enable kingshot-bot

echo "✓ Servicio systemd configurado"
EOF

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✓ DESPLIEGUE COMPLETADO EXITOSAMENTE║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Próximos pasos:${NC}"
echo ""
echo "1. SSH a tu Raspberry Pi:"
echo -e "   ${BLUE}ssh knycat@192.168.1.141${NC}"
echo ""
echo "2. Probar el bot (modo interactivo):"
echo -e "   ${BLUE}cd /home/knycat/kingshot-bot${NC}"
echo -e "   ${BLUE}source venv/bin/activate${NC}"
echo -e "   ${BLUE}python main.py${NC}"
echo ""
echo "3. Si funciona bien, iniciar como servicio:"
echo -e "   ${BLUE}sudo systemctl start kingshot-bot${NC}"
echo ""
echo "4. Ver estado del servicio:"
echo -e "   ${BLUE}sudo systemctl status kingshot-bot${NC}"
echo ""
echo "5. Ver logs en tiempo real:"
echo -e "   ${BLUE}journalctl -u kingshot-bot -f${NC}"
echo ""
echo -e "${YELLOW}IMPORTANTE:${NC}"
echo "- El servicio está habilitado (auto-inicia en reboot)"
echo "- Accede a Discord y prueba /help"
echo "- Verifica que el bot esté online en tu servidor"
echo ""
