# Minecraft Forge Server on Raspberry Pi

This folder contains scripts to install a Minecraft Java Forge server on Raspberry Pi OS 64-bit.

## What this setup gives you

- Forge server with `systemd` auto-start.
- Initial performance tuning for Raspberry Pi.
- Mods support using the `mods/` folder.
- Optional remote deploy script from your PC.
- Guidance for fixed IP with DHCP reservation + port forwarding.

## Recommended baseline

- Raspberry Pi 5 (preferably 8GB RAM).
- Raspberry Pi OS 64-bit.
- Wired Ethernet connection.

## 1) Install directly on the Raspberry Pi

Copy this folder to the Raspberry Pi and run:

```bash
chmod +x install_minecraft_forge_rpi.sh
sudo ./install_minecraft_forge_rpi.sh
```

Optional custom version:

```bash
sudo MC_VERSION=26.1.2 FORGE_VERSION=64.0.4 SERVER_PORT=25565 ./install_minecraft_forge_rpi.sh
```

## 2) Start and monitor

```bash
sudo systemctl start minecraft-forge
sudo systemctl enable minecraft-forge
sudo systemctl status minecraft-forge
sudo journalctl -u minecraft-forge -f
```

## 3) Install mods

1. Stop the server.
2. Upload `.jar` mods to `/opt/minecraft-forge/mods`.
3. Start again and review logs.

```bash
sudo systemctl stop minecraft-forge
sudo systemctl start minecraft-forge
```

Important: every mod must match the same Minecraft and Forge version.

## 4) Fixed IP (recommended: DHCP reservation in router)

- Find Raspberry Pi MAC address:

```bash
ip link show
```

- In your router admin page:
1. Create DHCP reservation for that MAC.
2. Assign a fixed LAN IP (example `192.168.1.141`).
3. Reboot router or renew lease.

## 5) External access (friends outside your home)

- Port forwarding in router:
1. Protocol: `TCP`
2. External/Internal port: `25565`
3. Destination IP: your Raspberry fixed LAN IP

- Share your public IP (or DDNS hostname) with friends.

## 6) Security basics

- Keep `white-list=true` in `server.properties`.
- Use whitelist for known players only.
- Do not expose SSH with weak passwords.
- Keep OS and server updated.

## 7) Backups

The installer creates:

```bash
/usr/local/bin/backup-minecraft-forge.sh
```

Run manually:

```bash
sudo /usr/local/bin/backup-minecraft-forge.sh
```

The script keeps recent backups and auto-removes old ones (>7 days).
