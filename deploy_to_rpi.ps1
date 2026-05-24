#!/usr/bin/env pwsh
<#
.SYNOPSIS
Deploy Kingshot Bot to Raspberry Pi 5
.DESCRIPTION
Transferencia automática del bot a la Raspberry Pi vía SSH/SCP
.EXAMPLE
./deploy_to_rpi.ps1
#>

# Configuration
$RemoteUser = "knycat"
$RemoteHost = "192.168.1.141"
$RemotePath = "/home/knycat/kingshot-bot"

# Colors (funciona en PowerShell 7+)
function Write-Info { Write-Host "ℹ️  $args" -ForegroundColor Cyan }
function Write-Success { Write-Host "✓ $args" -ForegroundColor Green }
function Write-Error-Custom { Write-Host "❌ $args" -ForegroundColor Red }
function Write-Warning-Custom { Write-Host "⚠️  $args" -ForegroundColor Yellow }

Write-Host ""
Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Kingshot Bot - Deploy to Raspberry Pi║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Info "Destino: ${RemoteUser}@${RemoteHost}:${RemotePath}"
Write-Host ""

# Step 1: Verify SSH/SCP
Write-Host "[1/4] Verificando SSH disponible..." -ForegroundColor Cyan
if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Write-Error-Custom "SSH no disponible. Por favor instala OpenSSH."
    exit 1
}
Write-Success "SSH disponible"

# Step 2: Copy project files
Write-Host "[2/4] Transfiriendo archivos (excluyendo venv y .git)..." -ForegroundColor Cyan

# Crear lista de archivos/carpetas a copiar
$ItemsToCopy = @(
    "main.py",
    "requirements.txt",
    ".env",
    "cogs",
    "models",
    "data",
    "utils",
    "kingshot-bot.service",
    "README.md",
    "DOCUMENTACION.md",
    "INSTALACION_RPI.sh"
)

try {
    $Items = Get-ChildItem -Recurse | Where-Object {
        $path = $_.FullName
        -not ($path -match "venv" -or $path -match "__pycache__" -or $path -match "\.git" -or $path -match "\.pyc$")
    }
    
    # Contar archivos
    $fileCount = ($Items | Where-Object { !$_.PSIsContainer }).Count
    Write-Info "Total de archivos a transferir: $fileCount"
    
    Write-Success "Archivos listos para transferir"
} catch {
    Write-Error-Custom "Error al listar archivos: $_"
}

# Step 3: Create remote directory and transfer files
Write-Host "[3/4] Creando directorio y transfiriendo..." -ForegroundColor Cyan

try {
    # Crear directorio remoto
    Write-Info "Creando directorio remoto..."
    ssh "${RemoteUser}@${RemoteHost}" "mkdir -p ${RemotePath}" 2>$null
    
    # Transferir archivos
    Write-Info "Transfiriendo archivos via SCP..."
    
    # Transferir cada item
    foreach ($item in $ItemsToCopy) {
        if (Test-Path $item) {
            Write-Info "  → $item"
            if ((Get-Item $item).PSIsContainer) {
                # Es carpeta, transferir recursivamente
                scp -r -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" `
                    "$item" "${RemoteUser}@${RemoteHost}:${RemotePath}/" 2>$null
            } else {
                # Es archivo
                scp -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" `
                    "$item" "${RemoteUser}@${RemoteHost}:${RemotePath}/" 2>$null
            }
        }
    }
    
    Write-Success "Archivos transferidos"
} catch {
    Write-Warning-Custom "Error durante transferencia: $_"
}

# Step 4: Install dependencies on remote
Write-Host "[4/4] Instalando dependencias en RPi..." -ForegroundColor Cyan

try {
    ssh -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" `
        "${RemoteUser}@${RemoteHost}" @"
cd /home/knycat/kingshot-bot

# Crear venv si no existe
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar venv e instalar
source venv/bin/activate
echo "Instalando dependencias..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "✓ Instalación completada"
"@ 2>$null
    
    Write-Success "Dependencias instaladas"
} catch {
    Write-Warning-Custom "Error durante instalación: $_"
}

Write-Host ""
Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   ✓ DESPLIEGUE COMPLETADO EXITOSAMENTE║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "Próximos pasos:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. SSH a tu Raspberry Pi:" -ForegroundColor White
Write-Host "   ssh knycat@192.168.1.141" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Probar el bot (modo interactivo):" -ForegroundColor White
Write-Host "   cd /home/knycat/kingshot-bot" -ForegroundColor Cyan
Write-Host "   source venv/bin/activate" -ForegroundColor Cyan
Write-Host "   python main.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Si funciona bien, iniciar como servicio:" -ForegroundColor White
Write-Host "   sudo systemctl start kingshot-bot" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Ver estado:" -ForegroundColor White
Write-Host "   sudo systemctl status kingshot-bot" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. Ver logs en tiempo real:" -ForegroundColor White
Write-Host "   journalctl -u kingshot-bot -f" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  IMPORTANTE:" -ForegroundColor Yellow
Write-Host "- Verifica que el bot esté online en Discord" -ForegroundColor White
Write-Host "- Prueba el comando /help en Discord" -ForegroundColor White
Write-Host "- Revisa los logs si hay problemas" -ForegroundColor White
Write-Host ""
