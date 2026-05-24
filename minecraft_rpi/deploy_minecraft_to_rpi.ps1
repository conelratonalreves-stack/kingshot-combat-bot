# Deploy minecraft_rpi folder to Raspberry Pi and run installer remotely.
# Usage (PowerShell):
#   .\minecraft_rpi\deploy_minecraft_to_rpi.ps1

$RemoteUser = if ($env:REMOTE_USER) { $env:REMOTE_USER } else { "knycat" }
$RemoteHost = if ($env:REMOTE_HOST) { $env:REMOTE_HOST } else { "192.168.1.141" }
$RemoteBase = if ($env:REMOTE_BASE) { $env:REMOTE_BASE } else { "/home/knycat" }
$RemotePath = "$RemoteBase/minecraft_rpi"

Write-Host "Deploy Minecraft Forge installer to Raspberry Pi" -ForegroundColor Cyan
Write-Host "Target: $RemoteUser@$RemoteHost`:$RemotePath"

ssh "$RemoteUser@$RemoteHost" "mkdir -p '$RemotePath'"
scp -r "./minecraft_rpi/*" "$RemoteUser@$RemoteHost`:$RemotePath/"
if ($LASTEXITCODE -ne 0) {
	throw "SCP upload failed."
}

Write-Host "Files uploaded." -ForegroundColor Green
Write-Host "Running remote installer..." -ForegroundColor Yellow

ssh "$RemoteUser@$RemoteHost" "cd '$RemotePath' && chmod +x install_minecraft_forge_rpi.sh && sudo ./install_minecraft_forge_rpi.sh"
if ($LASTEXITCODE -ne 0) {
	throw "Remote installer failed."
}

Write-Host "Done. Server installed on Raspberry Pi." -ForegroundColor Green
