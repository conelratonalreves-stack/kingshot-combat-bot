# 🚀 Referencia Rápida: Comandos de Cloudflare Tunnel

## 📌 Comandos Esenciales en RPi

### Estado y Logs

```bash
# Ver estado del servicio
sudo systemctl status cloudflared

# Ver logs en tiempo real (últimas líneas)
sudo journalctl -u cloudflared -f

# Ver últimas 100 líneas
sudo journalctl -u cloudflared -n 100

# Ver logs de hoy
sudo journalctl -u cloudflared --since today
```

### Reiniciar/Recargar

```bash
# Reiniciar servicio
sudo systemctl restart cloudflared

# Recargar configuración sin reiniciar (si cambiaste config.yml)
sudo systemctl reload cloudflared

# Detener servicio
sudo systemctl stop cloudflared

# Iniciar servicio
sudo systemctl start cloudflared
```

### Listar Túneles

```bash
# Listar todos los túneles
sudo cloudflared tunnel list

# Ver detalles de un túnel específico
sudo cloudflared tunnel info kingshot-billing-tunnel

# Ver conexiones activas
sudo cloudflared tunnel info kingshot-billing-tunnel --connections
```

### Editar Configuración

```bash
# Editar archivo config.yml
sudo nano /etc/cloudflared/config.yml

# Validar configuración (si hay syntax errors)
sudo cloudflared tunnel validate --config /etc/cloudflared/config.yml
```

### Credenciales y Autenticación

```bash
# Ver token guardado
ls -la /root/.cloudflared/

# Revocar autenticación (para volver a autenticar)
rm /root/.cloudflared/cert.pem
sudo cloudflared tunnel login
```

## 🐛 Troubleshooting Rápido

### Tunnel no se conecta

```bash
# 1. Ver logs detallados
sudo journalctl -u cloudflared -f

# 2. Reiniciar
sudo systemctl restart cloudflared

# 3. Verificar que panel está en puerto 8085
curl http://localhost:8085/
curl -v http://localhost:8085/
```

### DNS no funciona

```bash
# Desde tu PC, prueba resolve
nslookup www.facturacion.mkmagency.es
nslookup facturacion.mkmagency.es

# Si no resuelve, revisa:
# 1. Cloudflare Dashboard > DNS Records
# 2. Verifica que sean CNAME, no A
# 3. Verifica que proxy status sea naranja (Proxied)
```

### HTTPS da error

```bash
# Cloudflare genera SSL automáticamente
# Si hay error, prueba:

# 1. Limpiar caché DNS
ipconfig /flushdns  # Windows
sudo dscacheutil -flushcache  # Mac
sudo systemctl restart systemd-resolved  # Linux

# 2. Usar navegador privado
# 3. Esperar 5-10 minutos

# 4. Verificar certificado en Cloudflare
# Dashboard > SSL/TLS > Edge Certificates
```

### El tunnel se desconecta constantemente

```bash
# Ver si hay errores de conexión
sudo journalctl -u cloudflared -f

# Tipicamente por:
# 1. Internet inestable en RPi
# 2. Firewall de red bloqueando
# 3. ISP bloqueando puertos

# Soluciones:
# - Reiniciar router RPi
# - Verificar firewall local (ufw status)
# - Contactar ISP si persiste
```

## 📊 Monitoreo

### Verificar conexión desde tu PC

```powershell
# PowerShell - Verificar que el dominio está siendo servido
$url = "https://www.facturacion.mkmagency.es"
$response = Invoke-WebRequest -Uri $url -SkipHttpsValidation

$response.StatusCode        # Debe ser 200
$response.Content.Length    # Debe ser > 0
```

### Ver tráfico del túnel

```bash
# Estadísticas de conexión
sudo cloudflared tunnel info kingshot-billing-tunnel

# Monitoreo en tiempo real (si tienes jq instalado)
watch -n 2 'sudo cloudflared tunnel info kingshot-billing-tunnel'
```

## 🔄 Actualizar cloudflared

```bash
# Verificar versión actual
cloudflared --version

# Descargar latest
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.tgz

# Actualizar
tar -xzf cloudflared-linux-arm64.tgz
sudo mv cloudflared /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared
sudo systemctl restart cloudflared

# Verificar nueva versión
cloudflared --version
```

## 🛡️ Seguridad: Habilitar Access (OAuth)

### Añadir autenticación OAuth a www.facturacion.mkmagency.es

1. **En Cloudflare Dashboard**:
   - Selecciona MKMagency.es
   - Ve a Access > Applications
   - Click "Create an application"
   - Selecciona tipo: "SaaS"
   - URL: `https://www.facturacion.mkmagency.es`
   - Selecciona proveedor: Google, GitHub, etc.

2. **Editar config.yml en RPi**:

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

Quedará igual, pero Cloudflare manejará la autenticación de forma automática.

## 📝 Checklist de Configuración

- [ ] cloudflared instalado y funcionando
- [ ] Túnel creado: `kingshot-billing-tunnel`
- [ ] Archivo config.yml en `/etc/cloudflared/`
- [ ] DNS CNAME creado: `panel.mkmagency.es`
- [ ] Proxy status en naranja (Proxied)
- [ ] Servicio systemd habilitado
- [ ] Servicio systemd iniciado
- [ ] Acceso local funciona: `http://192.168.1.131:8085`
- [ ] Acceso remoto funciona: `https://panel.mkmagency.es`
- [ ] Logs no muestran errores

## 🎯 URLs de Referencia

- Documentación oficial: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- Cloudflare Dashboard: https://dash.cloudflare.com
- GitHub cloudflared: https://github.com/cloudflare/cloudflared
- Releases: https://github.com/cloudflare/cloudflared/releases
