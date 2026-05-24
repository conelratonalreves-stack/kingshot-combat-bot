#!/usr/bin/env pwsh
<#
.SYNOPSIS
Deploy Kingshot Bot to Raspberry Pi 5
.DESCRIPTION
Automatic transfer of the bot to Raspberry Pi via SSH/SCP
.EXAMPLE
./deploy_to_rpi_fixed.ps1
#>

# Configuration
$RemoteUser = "knycat"
$RemoteHost = "192.168.1.141"
$RemotePort = 22
$RemotePath = "/home/knycat/kingshot-bot"

# Load SSH config from rpi_config.json (if available)
$ConfigPath = Join-Path $PSScriptRoot "rpi_config.json"
if (Test-Path $ConfigPath) {
    try {
        $config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
        if ($config.rpi.user) { $RemoteUser = $config.rpi.user }
        if ($config.rpi.host) { $RemoteHost = $config.rpi.host }
        if ($config.rpi.port) { $RemotePort = [int]$config.rpi.port }
        if ($config.rpi.project_path) {
            $RemotePath = $config.rpi.project_path
        } elseif ($config.rpi.spy_project_path) {
            $RemotePath = $config.rpi.spy_project_path
        }
        Write-Host "Loaded SSH config from rpi_config.json" -ForegroundColor Green
    } catch {
        Write-Host "WARNING: Could not parse rpi_config.json, using defaults." -ForegroundColor Yellow
    }
}

$SshTarget = "${RemoteUser}@${RemoteHost}"

Write-Host ""
Write-Host "======================================"
Write-Host "Kingshot Bot - Deploy to Raspberry Pi"
Write-Host "======================================"
Write-Host ""
Write-Host "Target: ${SshTarget}:${RemotePath} (port ${RemotePort})"
Write-Host ""

# Step 1: Verify SSH/SCP
Write-Host "[1/5] Checking SSH availability..."
if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: SSH not available. Please install OpenSSH." -ForegroundColor Red
    exit 1
}
Write-Host "OK: SSH available" -ForegroundColor Green

# Step 2: Copy project files
Write-Host "[2/5] Transferring files (excluding venv and .git)..."

$ItemsToCopy = @(
    "main.py",
    "bridge_bot.py",
    "spy_bot_main.py",
    "events_bot_main.py",
    "notifications_bot.py",
    "run_billing_panel.py",
    "requirements.txt",
    ".env",
    "cogs",
    "models",
    "data",
    "utils",
    "billing_panel",
    "templates",
    "kingshot-bot.service",
    "kingshot-bridge-bot.service",
    "kingshot-spy-bot.service",
    "kingshot-notifications.service",
    "kingshot-billing-panel.service",
    "README.md"
)

try {
    Write-Host "Creating remote directory..."
    ssh -p $RemotePort "$SshTarget" "mkdir -p ${RemotePath}" 2>$null
    
    Write-Host "Transferring files via SCP..."
    
    foreach ($item in $ItemsToCopy) {
        if (Test-Path $item) {
            Write-Host "  -> $item"
            if ((Get-Item $item).PSIsContainer) {
                scp -P $RemotePort -r -o "StrictHostKeyChecking=no" "$item" "${SshTarget}:${RemotePath}/" 2>$null
            } else {
                scp -P $RemotePort -o "StrictHostKeyChecking=no" "$item" "${SshTarget}:${RemotePath}/" 2>$null
            }
        }
    }
    
    Write-Host "OK: Files transferred" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Transfer failed: $_" -ForegroundColor Red
}

# Step 3: Install dependencies on remote
Write-Host "[3/5] Installing dependencies and cleaning cache on Raspberry Pi..."

try {
    ssh -p $RemotePort -o "StrictHostKeyChecking=no" "$SshTarget" @"
cd ${RemotePath}

# Remove Python cache files
echo "Cleaning Python cache..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv and install
source venv/bin/activate
echo "Upgrading pip..."
pip install --upgrade pip --quiet 2>/dev/null
echo "Installing requirements..."
pip install -r requirements.txt --quiet 2>/dev/null

echo "OK: Installation completed"
"@ 2>$null
    
    Write-Host "OK: Dependencies installed and cache cleaned" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Installation error: $_" -ForegroundColor Yellow
}

# Step 4: Install tesseract for OCR
Write-Host "[4/5] Installing OCR dependencies (tesseract)..."

try {
    ssh -p $RemotePort -o "StrictHostKeyChecking=no" "$SshTarget" @"
sudo apt-get update -qq 2>/dev/null
sudo apt-get install -y -qq tesseract-ocr libtesseract-dev libleptonica-dev pkg-config 2>/dev/null
echo "OK: Tesseract installed"
"@ 2>$null
    
    Write-Host "OK: Tesseract installed" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Tesseract installation: $_" -ForegroundColor Yellow
}

# Step 5: Setup systemd service
Write-Host "[5/5] Setting up systemd services..."

try {
    ssh -p $RemotePort -o "StrictHostKeyChecking=no" "$SshTarget" @"
cd ${RemotePath}

# Copy service files
sudo cp kingshot-bot.service /etc/systemd/system/ 2>/dev/null
sudo cp kingshot-bridge-bot.service /etc/systemd/system/ 2>/dev/null
sudo cp kingshot-spy-bot.service /etc/systemd/system/ 2>/dev/null
sudo cp kingshot-notifications.service /etc/systemd/system/ 2>/dev/null
sudo cp kingshot-billing-panel.service /etc/systemd/system/ 2>/dev/null

# Reload daemon
sudo systemctl daemon-reload 2>/dev/null

# Restart services to apply new code
sudo systemctl restart kingshot-bot 2>/dev/null
sudo systemctl restart kingshot-bridge-bot 2>/dev/null
sudo systemctl restart kingshot-spy-bot 2>/dev/null
sudo systemctl restart kingshot-notifications 2>/dev/null
sudo systemctl restart kingshot-billing-panel 2>/dev/null

# Enable services
sudo systemctl enable kingshot-bot 2>/dev/null
sudo systemctl enable kingshot-bridge-bot 2>/dev/null
sudo systemctl enable kingshot-spy-bot 2>/dev/null
sudo systemctl enable kingshot-notifications 2>/dev/null
sudo systemctl enable kingshot-billing-panel 2>/dev/null

echo "Service states:"
for svc in kingshot-bot kingshot-bridge-bot kingshot-spy-bot kingshot-notifications kingshot-billing-panel; do
    active_state=$(sudo systemctl is-active "$svc" 2>/dev/null || true)
    enabled_state=$(sudo systemctl is-enabled "$svc" 2>/dev/null || true)
    echo "  - $svc: active=$active_state enabled=$enabled_state"
done

echo "OK: Services configured and restarted"
"@ 2>$null
    
    Write-Host "OK: Services installed and restarted" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Service setup: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "======================================"
Write-Host "DEPLOYMENT COMPLETED SUCCESSFULLY"
Write-Host "======================================"
Write-Host ""
Write-Host "Next steps:"
Write-Host ""
Write-Host "1. Check bot status:"
Write-Host "   ssh -p ${RemotePort} ${SshTarget}"
Write-Host "   sudo systemctl status kingshot-bot"
Write-Host "   sudo systemctl status kingshot-billing-panel"
Write-Host ""
Write-Host "2. View live logs:"
Write-Host "   ssh -p ${RemotePort} ${SshTarget}"
Write-Host "   sudo journalctl -u kingshot-bot -f"
Write-Host "   sudo journalctl -u kingshot-billing-panel -f"
Write-Host ""
Write-Host "3. Verify in Discord:"
Write-Host "   - Bot should appear online"
Write-Host "   - Test /help command"
Write-Host "   - Test /calculate [troop_count]"
Write-Host ""
Write-Host "IMPORTANT:"
Write-Host "- Verify bot is online in Discord"
Write-Host "- Check logs if there are problems"
Write-Host ""
