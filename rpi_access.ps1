#!/usr/bin/env pwsh
param(
    [ValidateSet("check", "ssh", "status", "logs", "deploy")]
    [string]$Action = "check"
)

$configPath = Join-Path $PSScriptRoot "rpi_config.json"
if (-not (Test-Path $configPath)) {
    Write-Host "ERROR: No existe rpi_config.json" -ForegroundColor Red
    exit 1
}

try {
    $config = Get-Content $configPath -Raw | ConvertFrom-Json
} catch {
    Write-Host "ERROR: rpi_config.json no es JSON valido" -ForegroundColor Red
    exit 1
}

$user = $config.rpi.user
$hostIp = $config.rpi.host
$port = [int]$config.rpi.port

if (-not $user -or -not $hostIp -or -not $port) {
    Write-Host "ERROR: Faltan rpi.user, rpi.host o rpi.port en rpi_config.json" -ForegroundColor Red
    exit 1
}

$target = "$user@$hostIp"

switch ($Action) {
    "check" {
        Write-Host "Comprobando red..." -ForegroundColor Cyan
        ping -n 1 $hostIp | Out-Host

        Write-Host "Comprobando SSH sin password..." -ForegroundColor Cyan
        ssh -o BatchMode=yes -o ConnectTimeout=8 -p $port $target "echo ACCESS_OK && hostname && whoami"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: SSH por clave no disponible" -ForegroundColor Red
            exit 1
        }

        Write-Host "OK: Acceso listo" -ForegroundColor Green
        exit 0
    }

    "ssh" {
        Write-Host "Abriendo sesion SSH a ${target}:$port" -ForegroundColor Cyan
        ssh -p $port $target
        exit $LASTEXITCODE
    }

    "status" {
        ssh -p $port $target "sudo systemctl is-active kingshot-bot; sudo systemctl is-active kingshot-bridge-bot; sudo systemctl is-active kingshot-notifications; sudo systemctl is-active kingshot-spy-bot"
        exit $LASTEXITCODE
    }

    "logs" {
        ssh -p $port $target "sudo journalctl -u kingshot-bridge-bot --no-pager -n 40"
        exit $LASTEXITCODE
    }

    "deploy" {
        & (Join-Path $PSScriptRoot "deploy_to_rpi_fixed.ps1")
        exit $LASTEXITCODE
    }
}
