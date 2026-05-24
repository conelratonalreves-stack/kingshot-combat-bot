# Script PowerShell para configurar Cloudflare Tunnel en Raspberry Pi
# Uso: .\setup_cloudflare_tunnel.ps1

param(
    [string]$RpiHost = "192.168.1.131",
    [string]$RpiUser = "knycat",
    [string]$TunnelName = "kingshot-billing-tunnel",
    [string]$Domain = "mkmagency.es"
)

$ErrorActionPreference = "Stop"

function Assert-LastCommand {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Fallo en paso: $Step (exit code $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cloudflare Tunnel Configurator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar PuTTY/SSH
$sshPath = Get-Command ssh -ErrorAction SilentlyContinue
if (-not $sshPath) {
    Write-Host "ERROR: SSH no encontrado. Instala Git Bash o SSH de Windows." -ForegroundColor Red
    exit 1
}

Write-Host "OK: SSH disponible" -ForegroundColor Green
Write-Host ""

# Paso 1: Transferir script
Write-Host "[1/6] Transfiriendo script de instalación a RPi..." -ForegroundColor Yellow
$setupScript = "setup_cloudflare_tunnel.sh"
$scpCmd = "scp '$setupScript' ${RpiUser}@${RpiHost}:~/"
Write-Host "Ejecutando: $scpCmd" -ForegroundColor Gray
Invoke-Expression $scpCmd
Assert-LastCommand "Transferir script a RPi"
Write-Host "OK: Script transferido" -ForegroundColor Green
Write-Host ""

# Paso 2: Conectar y preparar
Write-Host "[2/6] Preparando permisos en RPi..." -ForegroundColor Yellow
$prepareCmd = "ssh ${RpiUser}@${RpiHost} 'chmod +x ~/$setupScript'"
Invoke-Expression $prepareCmd
Assert-LastCommand "Dar permisos al script en RPi"
Write-Host "OK: Permisos configurados" -ForegroundColor Green
Write-Host ""

# Paso 3: Ejecutar instalación
Write-Host "[3/6] Ejecutando instalación de Cloudflare Tunnel..." -ForegroundColor Yellow
Write-Host "ADVERTENCIA: Se abrira una conexion SSH interactiva. Sigue las instrucciones del script." -ForegroundColor Yellow
Write-Host ""

$installCmd = "ssh -t ${RpiUser}@${RpiHost} 'cd ~/ && sudo bash $setupScript'"
Invoke-Expression $installCmd
Assert-LastCommand "Ejecutar instalador en RPi"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CONFIGURACION COMPLETADA" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "URLs de acceso:" -ForegroundColor Green
Write-Host "   - Local: http://192.168.1.131:8085" -ForegroundColor Cyan
Write-Host "   - Remoto: https://www.facturacion.$Domain" -ForegroundColor Cyan
Write-Host ""

Write-Host "Verificar estado desde ahora:" -ForegroundColor Green
Write-Host 'ssh ${RpiUser}@${RpiHost} "sudo systemctl status cloudflared"' -ForegroundColor Gray
Write-Host ""

Write-Host "Ver logs en tiempo real:" -ForegroundColor Green
Write-Host 'ssh ${RpiUser}@${RpiHost} "sudo journalctl -u cloudflared -f"' -ForegroundColor Gray
Write-Host ""

# Nota: no se borra el script local porque forma parte del repositorio.
Write-Host "[6/6] Finalizado" -ForegroundColor Yellow
Write-Host "OK: Completado" -ForegroundColor Green
Write-Host ""
