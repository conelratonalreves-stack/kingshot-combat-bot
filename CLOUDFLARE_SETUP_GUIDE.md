# 🌐 Guía Completa: Acceso Remoto al Panel de Facturación vía Cloudflare

## 📋 Resumen

Vas a exponer tu panel de facturación (puerto 8085 en RPi) de forma segura a través de Cloudflare Tunnel:

```
Internet
  ↓
www.facturacion.mkmagency.es (Cloudflare)
  ↓
Cloudflare Tunnel (seguro, sin puertos abiertos)
  ↓
Raspberry Pi (192.168.1.131:8085)
```

## ✅ Requisitos Previos

- ✅ Dominio MKMagency.es registrado en Cloudflare
- ✅ Acceso a dashboard de Cloudflare
- ✅ SSH a Raspberry Pi (`ssh knycat@192.168.1.131`)
- ✅ Panel de facturación corriendo en puerto 8085

## 🚀 Instalación Paso a Paso

### Opción A: Instalación Automática (RECOMENDADA)

1. **Descarga el script desde tu PC**:
   ```powershell
   # En tu PC local
   scp setup_cloudflare_tunnel.sh knycat@192.168.1.131:~/
   ```

2. **Ejecuta en la Raspberry Pi**:
   ```bash
   ssh knycat@192.168.1.131
   chmod +x setup_cloudflare_tunnel.sh
   ./setup_cloudflare_tunnel.sh
   ```

3. **Sigue las instrucciones del script** (autenticación, creación de DNS)

### Opción B: Instalación Manual

#### 1️⃣ Instalar cloudflared

```bash
# SSH a RPi
ssh knycat@192.168.1.131

# Descargar la versión ARM64
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.tgz

# Extraer e instalar
tar -xzf cloudflared-linux-arm64.tgz
sudo mv cloudflared /usr/local/bin/
sudo chmod +x /usr/local/bin/cloudflared
rm cloudflared-linux-arm64.tgz

# Verificar instalación
cloudflared --version
```

#### 2️⃣ Autenticar cloudflared

```bash
# Este comando abre una URL para autenticar
sudo cloudflared tunnel login

# Copia el enlace que aparece en tu navegador de escritorio
# Completa la autenticación en Cloudflare
# Se guardará un certificado en: /root/.cloudflared/
```

#### 3️⃣ Crear el Túnel

```bash
# Crear el túnel
sudo cloudflared tunnel create kingshot-billing-tunnel

# Obtener el UUID (lo necesitarás para DNS)
sudo cloudflared tunnel list
```

Salida esperada:
```
ID                                NAME                           CREATED              CONNECTIONS
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  kingshot-billing-tunnel      2026-05-20T10:00:00Z  0/0
```

#### 4️⃣ Crear Archivo de Configuración

```bash
# Editar configuración
sudo nano /etc/cloudflared/config.yml
```

**Contenido del archivo** (reemplaza `TUNNEL_UUID` con tu UUID):
```yaml
tunnel: TUNNEL_UUID
credentials-file: /root/.cloudflared/TUNNEL_UUID.json

ingress:
  - hostname: www.facturacion.mkmagency.es
    service: http://localhost:8085
  - hostname: facturacion.mkmagency.es
    service: http://localhost:8085
  - service: http_status:404
```

Ejemplo real:
```yaml
tunnel: 12345678-1234-1234-1234-123456789012
credentials-file: /root/.cloudflared/12345678-1234-1234-1234-123456789012.json

ingress:
  - hostname: www.facturacion.mkmagency.es
    service: http://localhost:8085
  - hostname: facturacion.mkmagency.es
    service: http://localhost:8085
  - service: http_status:404
```

Guardar: `Ctrl+O` → `Enter` → `Ctrl+X`

#### 5️⃣ Configurar DNS en Cloudflare Dashboard

1. **Abre**: https://dash.cloudflare.com
2. **Selecciona dominio**: MKMagency.es
3. **Ve a**: DNS → Records
4. **Crea CNAME record primario**:
   - **Name**: `www.facturacion`
   - **Content**: `TUNNEL_UUID.cfargotunnel.com` (ej: 12345678-1234-1234-1234-123456789012.cfargotunnel.com)
   - **TTL**: Auto
   - **Proxy status**: 🟠 Proxied (IMPORTANTE: naranja, no gris)

5. **Crea CNAME record alias**:
   - **Name**: `facturacion`
   - **Content**: `TUNNEL_UUID.cfargotunnel.com`
   - **Proxy status**: 🟠 Proxied

   Resultado:
   - `www.facturacion.mkmagency.es` → panel principal
   - `facturacion.mkmagency.es` → alias

#### 6️⃣ Crear Servicio systemd

```bash
sudo nano /etc/systemd/system/cloudflared.service
```

**Contenido**:
```ini
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/.cloudflared
ExecStart=/usr/local/bin/cloudflared tunnel --config /etc/cloudflared/config.yml run
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Guardar: `Ctrl+O` → `Enter` → `Ctrl+X`

#### 7️⃣ Habilitar y Iniciar Servicio

```bash
# Recargar systemd
sudo systemctl daemon-reload

# Habilitar para inicio automático
sudo systemctl enable cloudflared

# Iniciar servicio
sudo systemctl start cloudflared

# Verificar estado
sudo systemctl status cloudflared
```

## ✅ Verificación

### 1. Estado del servicio en RPi

```bash
sudo systemctl status cloudflared
```

Debe mostrar: `Active: active (running)`

### 2. Ver logs en tiempo real

```bash
sudo journalctl -u cloudflared -f
```

Busca líneas como:
```
Tunnel registered with connection ID: <id>
```

### 3. Acceso local (desde RPi)

```bash
curl http://localhost:8085/
```

Debe retornar HTTP 200 con HTML del panel.

### 4. Acceso remoto

Desde cualquier navegador:
```
https://www.facturacion.mkmagency.es
```

Debe cargar el panel de facturación de forma segura.

## 🔧 Troubleshooting

### El tunnel no se conecta

```bash
# Ver logs detallados
sudo journalctl -u cloudflared -f --lines=50

# Reiniciar servicio
sudo systemctl restart cloudflared

# Verificar que panel está en puerto 8085
curl http://localhost:8085/
```

### No puedo acceder a panel.mkmagency.es

1. Verifica DNS en Cloudflare:
   - Debe ser **CNAME** (no A)
   - Proxy status debe ser **🟠 Proxied** (no gris)

2. Espera 5-10 minutos para que DNS se propague

3. Limpia caché del navegador (Ctrl+Shift+Del)

4. Prueba en navegador privado

### SSL/HTTPS no funciona

Cloudflare lo proporciona automáticamente:
- ✅ Certificado gratis
- ✅ HTTPS siempre activado
- ✅ Recarga automática si accedes por HTTP

## 📊 URLs de Acceso

| Acceso | URL | Ubicación |
|--------|-----|-----------|
| 🏠 Local | `http://192.168.1.131:8085` | Red interna |
| 🌐 Remoto | `https://www.facturacion.mkmagency.es` | Desde Internet |
| 📋 Alias | `https://facturacion.mkmagency.es` | Desde Internet |

## 🔐 Seguridad

- ✅ No necesitas abrir puertos en router
- ✅ Cloudflare maneja SSL/HTTPS
- ✅ Túnel cifrado Cloudflare-RPi
- ✅ Firewall de Cloudflare integrado

## 📝 Próximos Pasos

1. **Autenticación (opcional)**:
   - Añadir HTTP Basic Auth
   - Usar Cloudflare Access para OAuth

2. **Monitoreo**:
   - Configurar alertas en caso de fallo
   - Verificar logs periódicamente

3. **Escalabilidad**:
   - Si necesitas múltiples servicios, crea más `ingress` rules
   - Ejemplo: `panel.mkmagency.es` → puerto 8085, `bot.mkmagency.es` → puerto 3000, etc.

## 🆘 Soporte

- Documentación Cloudflare: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- Issues de cloudflared: https://github.com/cloudflare/cloudflared
