#!/bin/bash
# ============================================
# INSTALACIÓN EN RASPBERRY PI 5
# ============================================
# 
# Este script está configurado para:
# - Usuario: knycat
# - IP: 192.168.1.141
# - Directorio: /home/knycat/kingshot-bot
#
# ============================================

echo "Kingshot Bot - Instalación Raspberry Pi 5"
echo "========================================="
echo ""
echo "⚠️  IMPORTANTE: Este script debe ejecutarse EN LA RASPBERRY PI"
echo ""

# Configuración
REPO_URL="<REPLACE_WITH_YOUR_REPO>"
BOT_DIR="/home/knycat/kingshot-bot"
USER="knycat"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}[PASO 1] Actualizando sistema...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

echo -e "${BLUE}[PASO 2] Instalando dependencias del sistema...${NC}"
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    git \
    tesseract-ocr \
    libatlas-base-dev \
    libjasper-dev \
    libopenjp2-7 \
    python3-dev

echo -e "${BLUE}[PASO 3] Creando directorio del bot...${NC}"
mkdir -p $BOT_DIR
cd $BOT_DIR

echo -e "${BLUE}[PASO 4] Descargando código del bot...${NC}"
# Si usas git:
# git clone $REPO_URL .
# 
# O si copias manualmente:
echo "⚠️  Por favor, copia los archivos del proyecto a $BOT_DIR"
read -p "Presiona Enter cuando hayas copiado los archivos..."

echo -e "${BLUE}[PASO 5] Creando entorno virtual...${NC}"
python3 -m venv venv
source venv/bin/activate

echo -e "${BLUE}[PASO 6] Instalando paquetes Python...${NC}"
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo -e "${BLUE}[PASO 7] Configurando variables de entorno...${NC}"
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  Se necesita tu Discord Bot Token"
    read -p "Introduce tu DISCORD_TOKEN: " TOKEN
    echo "DISCORD_TOKEN=$TOKEN" > .env
    echo -e "${GREEN}✓ Archivo .env creado${NC}"
else
    echo -e "${YELLOW}✓ Archivo .env ya existe${NC}"
fi

echo -e "${BLUE}[PASO 8] Configurando servicio systemd...${NC}"
# Editar kingshot-bot.service si es necesario
echo "Verificando ruta en kingshot-bot.service..."
if grep -q "WorkingDirectory=$BOT_DIR" kingshot-bot.service; then
    echo -e "${GREEN}✓ Rutas correctas en service file${NC}"
else
    echo -e "${YELLOW}⚠️  Actualizando rutas en service file...${NC}"
    sed -i "s|WorkingDirectory=.*|WorkingDirectory=$BOT_DIR|g" kingshot-bot.service
    sed -i "s|ExecStart=.*|ExecStart=$BOT_DIR/venv/bin/python main.py|g" kingshot-bot.service
fi

sudo cp kingshot-bot.service /etc/systemd/system/

echo -e "${BLUE}[PASO 9] Habilitando servicio...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable kingshot-bot

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}✓ INSTALACIÓN COMPLETADA${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Próximos pasos:"
echo ""
echo "1. Iniciar el bot manualmente (para probar):"
echo "   cd $BOT_DIR"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "2. Iniciar el bot como servicio (producción):"
echo "   sudo systemctl start kingshot-bot"
echo ""
echo "3. Ver estado del servicio:"
echo "   sudo systemctl status kingshot-bot"
echo ""
echo "4. Ver logs en tiempo real:"
echo "   journalctl -u kingshot-bot -f"
echo ""
echo "5. Detener el servicio:"
echo "   sudo systemctl stop kingshot-bot"
echo ""
echo "6. Ver logs históricos:"
echo "   journalctl -u kingshot-bot -n 100"
echo ""
echo -e "${YELLOW}IMPORTANTE${NC}:"
echo "- El bot ahora se iniciará automáticamente al reiniciar la RPi"
echo "- Usa journalctl para ver logs si hay errores"
echo "- El TOKEN debe estar en .env"
echo ""
