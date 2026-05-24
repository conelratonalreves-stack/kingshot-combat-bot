# 🔗 Configuración DNS en Cloudflare para www.facturacion.mkmagency.es

## 📋 Resumen Rápido

Tu panel de facturación estará disponible en:
- **Principal**: `https://www.facturacion.mkmagency.es` ⭐
- **Alias**: `https://facturacion.mkmagency.es`

---

## 🚀 Pasos en Cloudflare Dashboard

### 1. Abre Cloudflare

Ve a: https://dash.cloudflare.com

### 2. Selecciona tu Dominio

- Dominio: **MKMagency.es**

### 3. Ve a DNS Records

En el menú lateral: **DNS** → **Records**

### 4. Crea Primer CNAME Record (Principal)

Haz clic en **"+ Add record"**

| Campo | Valor |
|-------|-------|
| **Type** | CNAME |
| **Name** | `www.facturacion` |
| **Content** | `TUNNEL_UUID.cfargotunnel.com` |
| **TTL** | Auto |
| **Proxy status** | 🟠 **Proxied** (IMPORTANTE: naranja, no gris) |

**Ejemplo real** (si tu TUNNEL_UUID es `12345678-1234-1234-1234-123456789012`):
```
Name: www.facturacion
Content: 12345678-1234-1234-1234-123456789012.cfargotunnel.com
Proxy: Proxied 🟠
```

Haz clic en **Save**

### 5. Crea Segundo CNAME Record (Alias)

Haz clic nuevamente en **"+ Add record"**

| Campo | Valor |
|-------|-------|
| **Type** | CNAME |
| **Name** | `facturacion` |
| **Content** | `TUNNEL_UUID.cfargotunnel.com` |
| **TTL** | Auto |
| **Proxy status** | 🟠 **Proxied** |

Haz clic en **Save**

### 6. Verifica tu Configuración

Deberías ver en tu lista de DNS Records:

```
Type     Name                        Content                                    Proxy
CNAME    www.facturacion             12345678-1234-1234-1234-123456789012...   Proxied 🟠
CNAME    facturacion                 12345678-1234-1234-1234-123456789012...   Proxied 🟠
```

✅ **Ambas deben tener proxy status en naranja**

---

## ⚠️ Errores Comunes

### ❌ Proxy status está en gris (DNS only)
**Problema**: El túnel no funcionará
**Solución**: Haz clic en el record y cambia proxy status a 🟠 **Proxied**

### ❌ Type es "A" en lugar de "CNAME"
**Problema**: Cloudflare no lo reconocerá como túnel
**Solución**: Elimina el record y crea uno nuevo con Type = CNAME

### ❌ Content no coincide con el UUID del túnel
**Problema**: No funcionará la conexión
**Solución**: Copia exactamente el UUID que aparece en `sudo cloudflared tunnel list`

---

## 🧪 Pruebas Después de Configurar

### Test 1: DNS Resolution

Desde tu PC (PowerShell):
```powershell
nslookup www.facturacion.mkmagency.es
nslookup facturacion.mkmagency.es
```

Deberían retornar direcciones IP de Cloudflare (no errores).

### Test 2: Acceso HTTPS

Abre en tu navegador:
```
https://www.facturacion.mkmagency.es
```

Deberías ver el panel de facturación sin errores SSL.

### Test 3: Alias

Abre:
```
https://facturacion.mkmagency.es
```

También debe funcionar y redirigir al mismo panel.

---

## 📝 Información Necesaria

**Antes de empezar, necesitarás**:

1. **Tu TUNNEL_UUID** - Obtenlo ejecutando en RPi:
   ```bash
   ssh knycat@192.168.1.131
   sudo cloudflared tunnel list
   ```
   
   Busca la línea con `kingshot-billing-tunnel` y copia el UUID (primer campo)

2. **Acceso a Cloudflare Dashboard** con permisos de edición

---

## 🔄 Si Necesitas Cambiar Algo Después

### Editar un record existente
1. Ve a **DNS → Records**
2. Haz clic en el lápiz (edit) del record
3. Modifica lo que necesites
4. Haz clic en **Save**

### Eliminar un record
1. Ve a **DNS → Records**
2. Haz clic en la X (delete) del record
3. Confirma

### Añadir más subdominios
Repite los pasos anteriores con otros nombres, ej:
- `api.facturacion.mkmagency.es`
- `admin.facturacion.mkmagency.es`
- etc.

---

## 🛡️ Verificación de Seguridad

**Cloudflare proporciona automáticamente**:
- ✅ SSL/HTTPS certificado (gratis, renovación automática)
- ✅ DDoS protection
- ✅ Web Application Firewall (WAF)
- ✅ Cifrado end-to-end

No necesitas hacer nada más para seguridad básica. ✨

---

## 📞 Soporte Rápido

Si algo no funciona:

1. **Verifica DNS propaga correctamente**:
   ```
   https://www.whatsmydns.net/#CNAME/www.facturacion.mkmagency.es
   ```

2. **Verifica estado del túnel en RPi**:
   ```bash
   sudo systemctl status cloudflared
   sudo journalctl -u cloudflared -f
   ```

3. **Limpia caché del navegador**:
   - Windows: Ctrl+Shift+Del
   - Mac: Cmd+Shift+Del
   - Abre en modo privado/incógnito

4. **Espera 5-10 minutos** para que DNS se propague globalmente

---

## 🎯 Checklist Final

- [ ] TUNNEL_UUID obtenido de `sudo cloudflared tunnel list`
- [ ] CNAME record primario creado: `www.facturacion`
- [ ] CNAME record alias creado: `facturacion`
- [ ] Ambos tienen proxy status 🟠 **Proxied**
- [ ] DNS resolución funciona (`nslookup` retorna IPs)
- [ ] `https://www.facturacion.mkmagency.es` carga sin errores
- [ ] `https://facturacion.mkmagency.es` también funciona
- [ ] Panel de facturación visible en navegador

✅ **Si todos los checks están marcados, ¡estás listo!** 🚀
