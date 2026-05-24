# Bot Kingshot - Documentación Completa

## 📋 Resumen del Proyecto

Se ha creado un **bot de Discord especializado en cálculos de combate para Kingshot**, un juego móvil estratégico. El bot:

1. **Recibe del usuario**: Solo el número total de tropas disponibles (ej: 900450)
2. **Solicita un screenshot**: Del reporte de batalla mostrando estadísticas aliadas (izquierda) y enemigas (derecha)
3. **Extrae datos automáticamente** mediante OCR (Optical Character Recognition)
4. **Calcula y recomienda**:
   - Composición óptima de tropas (Infantry:Cavalry:Archers%)
   - Predicción de victoria/derrota
   - Número de combates necesarios si el enemigo es muy fuerte
   - Análisis detallado de estadísticas

---

## 🎮 Mecánicas de Kingshot Implementadas

El bot implementa correctamente el sistema de combate de Kingshot:

### Fórmula de Daño
```
Kills = √Tropas × (Ataque × Letalidad) / (Defensa × Salud) × SkillMod
```

### Orden de Ataque
- Infantry (Infantería) ataca primero
- Cavalry (Caballería) ataca segundo  
- Archers (Arqueros) ataca tercero
- Todos atacan simultáneamente dentro de su tipo

### Sistema de Contrapesos
```
Infantry > Cavalry > Archers > Infantry (ciclo de bonificadores)
```

---

## 🛠️ Estructura del Proyecto

```
Bot Composicion Discord/
│
├── main.py                    # Punto de entrada del bot
├── requirements.txt           # Dependencias Python
├── .env.example              # Plantilla de configuración
│
├── cogs/                      # Módulos de comandos
│   ├── __init__.py
│   ├── commands.py            # Comandos: /calculate, /help
│   └── battle_calculator.py   # Motor de cálculo de batallas
│
├── models/                    # Modelos de datos
│   ├── __init__.py
│   ├── troop.py              # Estructura de tropas
│   ├── hero.py               # Estructura de héroes
│   └── battle.py             # Simulador de batallas
│
├── data/                      # Datos estáticos
│   ├── __init__.py
│   ├── heroes.json           # Base de datos de héroes
│   └── formations.json       # Formaciones recomendadas
│
├── utils/                     # Utilidades
│   ├── __init__.py
│   ├── ocr_extractor.py      # Extracción OCR de imágenes
│   └── validators.py         # Validación de datos
│
├── install_rpi.sh            # Script de instalación para Raspberry Pi
├── deploy_rpi.sh             # Script de despliegue remoto
├── kingshot-bot.service      # Configuración systemd para auto-start
├── QUICKSTART.sh             # Guía de inicio rápido
└── README.md                 # Documentación completa
```

---

## 💻 Instalación y Uso

### Local (Windows/Mac/Linux)

```bash
# 1. Descargar el proyecto
cd Bot\ Composicion\ Discord

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Crear archivo .env
echo "DISCORD_TOKEN=tu_token_aqui" > .env

# 4. Ejecutar el bot
python main.py
```

### Raspberry Pi 5 (Producción 24/7)

```bash
# 1. SSH a la RPi
ssh knycat@192.168.1.141

# 2. Descargar el proyecto
git clone <repositorio> kingshot-bot
cd kingshot-bot

# 3. Ejecutar instalación automática
chmod +x install_rpi.sh
./install_rpi.sh

# 4. Configurar como servicio (auto-start)
sudo cp kingshot-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable kingshot-bot
sudo systemctl start kingshot-bot

# 5. Ver estado/logs
sudo systemctl status kingshot-bot
journalctl -u kingshot-bot -f
```

---

## 📱 Flujo de Uso del Bot

### 1️⃣ Usuario inicia cálculo
```
/calculate 900450
```
(Introductor: número total de tropas disponibles)

### 2️⃣ Bot solicita screenshot
```
Bot pide: "Sube un screenshot del reporte de batalla"
- LEFT (Izquierda): Tus stats (Ataque, Defensa, Letalidad, Salud)
- RIGHT (Derecha): Stats enemigos (mismo formato)
- Los 3 tipos: Infantería, Caballería, Arqueros
```

### 3️⃣ Usuario sube la imagen
```
Usuario: [Carga screenshot.png]
```

### 4️⃣ Bot analiza y responde
```
✅ Análisis Completo!

🛡️ Tus Tropas: 900,450
⚔️ Tropas Enemigas: [Stats extraídos]

📋 Recomendaciones:
   Formación Óptima: Infantry 50% | Cavalry 20% | Archers 30%
   Resultado Esperado: Victoria en 1 batalla
```

---

## 🔧 Características Implementadas

### ✅ Completadas

1. **OCR Extraction**
   - Extrae automáticamente stats de screenshots
   - Soporta español
   - Procesa múltiples tipos de tropas
   - Distingue entre aliados y enemigos

2. **Battle Simulator**
   - Simula combates turno por turno
   - Implementa fórmula exacta de Kingshot
   - Calcula bajas y supervivientes
   - Determina ganador

3. **Composition Optimizer**
   - Prueba diferentes composiciones
   - Calcula composición óptima
   - Minimiza bajas
   - Maximiza daño

4. **Discord Integration**
   - Comandos slash (`/calculate`, `/help`)
   - Embeds con información formateada
   - Listener para uploads de imágenes
   - Mensajes ephemeral para privacidad

5. **Raspberry Pi Optimization**
   - Dependencias minimalistas
   - Bajo consumo de memoria
   - Servicio systemd para 24/7
   - Scripts automatizados de instalación

---

## 📊 Datos Extraídos del Screenshot

### Del lado IZQUIERDO (Aliados):
```
Infantería:
  - Ataque: +550.0%
  - Defensa: +522.8%
  - Letalidad: +446.0%
  - Salud: +470.5%

Caballería:
  - Ataque: +500.1%
  - Defensa: +480.8%
  - Letalidad: +451.7%
  - Salud: +380.4%

Arqueros:
  - Ataque: +488.9%
  - Defensa: +467.3%
  - Letalidad: +485.9%
  - Salud: +412.1%
```

### Del lado DERECHO (Enemigos):
```
[Mismo formato pero con estadísticas diferentes]
```

---

## 🚀 Comandos Discord Disponibles

### `/calculate [tropas_totales]`
**Descripción**: Inicia un análisis de batalla

**Uso**:
```
/calculate 900450
```

**Parámetro**:
- `tropas_totales`: Número total de tropas disponibles (ej: 900450, 1080000)

**Respuesta**: 
- Bot solicita un screenshot
- Usuario sube la imagen
- Bot analiza y proporciona recomendaciones

---

### `/help`
**Descripción**: Muestra información de ayuda sobre el bot

**Respuesta**:
- Cómo usar `/calculate`
- Formato de screenshot requerido
- Mecánicas de juego implementadas

---

## 🔐 Configuración del Bot de Discord

### Crear el Bot en Discord Developer Portal

1. Ir a https://discord.com/developers/applications
2. Crear nueva aplicación
3. En "Bot", crear el bot
4. Copiar el **TOKEN** (mantener secreto!)
5. En "OAuth2" → "URL Generator":
   - Seleccionar scope: `bot`
   - Permisos:
     - `Send Messages`
     - `Embed Links`
     - `Read Messages/View Channels`
6. Usar la URL generada para añadir el bot al servidor

### Activar Intents Necesarios

En "Bot" → "Intents":
- ✅ `PRESENCE INTENT`
- ✅ `SERVER MEMBERS INTENT`
- ✅ `MESSAGE CONTENT INTENT` (CRÍTICO para procesar mensajes)

---

## 📦 Dependencias

```
discord.py==2.3.2              # API de Discord
python-dotenv==1.0.0          # Cargar variables de entorno
pillow==10.1.0                # Procesamiento de imágenes
numpy==1.24.3                 # Cálculos matemáticos
pytesseract==0.3.10           # Interfaz OCR
opencv-python-headless==4.8.1.78  # Procesamiento avanzado de imágenes
```

### Requisitos del Sistema
- **Tesseract OCR**: Debe estar instalado en el sistema
  - Windows: https://github.com/UB-Mannheim/tesseract/wiki
  - macOS: `brew install tesseract`
  - Linux: `sudo apt-get install tesseract-ocr`

---

## 🐍 Modelos de Datos

### TroopStats
Representa estadísticas de un tipo específico de tropa:
```python
- attack: float          # Ataque base
- lethality: float       # Letalidad/Critical
- defense: float         # Defensa
- health: float          # Salud por tropa
- count: int             # Cantidad de tropas
- troop_type: str        # "infantry", "cavalry", "archers"
```

### TroopComposition
Composición completa de tropas:
```python
- infantry: TroopStats
- cavalry: TroopStats
- archers: TroopStats
- Propiedades calculadas:
  - total_troops: int
  - infantry_ratio: float
  - cavalry_ratio: float
  - archers_ratio: float
```

### HeroStats
Estadísticas de un héroe:
```python
- name: str
- attack, lethality, defense, health: float
- troop_type: str        # Qué tipo de tropa afecta
```

### BattleHeroes
Héroes en una batalla:
```python
- main_heroes: List[HeroStats]      # 3 máximo
- joiner_heroes: List[JoinerHero]   # 0-4 máximo
- city_buffs: dict
- pet_skills: dict
- Métodos:
  - get_total_damage_boost()
  - get_total_defense_boost()
```

---

## 📈 Cálculo Detallado de Daño

El bot calcula el daño por turno para cada tipo de tropa:

### Paso 1: Extraer Stats
```
Del screenshot OCR:
- Infantry: Attack=550%, Defense=522%, Lethality=446%, Health=470%
- Cavalry: Attack=500%, Defense=480%, Lethality=451%, Health=380%
- Archers: Attack=488%, Defense=467%, Lethality=485%, Health=412%
```

### Paso 2: Distribuir Tropas
```
Total disponibles: 900,450
Composición óptima: 50% Infantry, 20% Cavalry, 30% Archers
- Infantry: 450,225
- Cavalry: 180,090
- Archers: 270,135
```

### Paso 3: Calcular Kills por Turno
```
Para Infantry atacando Infantry enemiga:
Kills = √450225 × (550 × 446) / (522 × 470) × SkillMod
      = 671 × 245300 / 245340 × 1.0
      ≈ 670 tropas Infantry enemigas muertas por turno
```

### Paso 4: Simular Batalla
```
Turno 1: Infantry ataca
  - Enemy Infantry: 670 muertas
Turno 1: Cavalry ataca
  - Enemy Cavalry: X muertas
Turno 1: Archers ataca
  - Enemy Archers: Y muertas
Turno 1: Enemy contraataca
  - Nuestras Infantry: A muertas
  - Nuestras Cavalry: B muertas
  - Nuestros Archers: C muertas
...continúa hasta que un bando sea eliminado
```

---

## 🔄 Flujo Multi-Combate

Si el enemigo es muy fuerte y no se puede ganar en un combate:

```
Combate 1: 
  - Daño: 50,000 tropas enemigas eliminadas
  - Nuestras pérdidas: 80,000

Combate 2: 
  - Enemy now has 50,000 fewer troops
  - Daño: 60,000 tropas enemigas
  - Nuestras pérdidas: 70,000

Combate 3:
  - Enemy defeated!
```

El bot calcula **cuántos combates necesitas** para ganar.

---

## 🎯 Próximas Mejoras (Futuro)

- [ ] Base de datos de heroes con stats reales
- [ ] Cálculo de SkillMod con joiner heroes
- [ ] Formaciones predefinidas por evento
- [ ] Sistema de almacenamiento de perfiles
- [ ] Estadísticas históricas de batallas
- [ ] Predicción de daño más precisa
- [ ] Soporte para diferentes eventos (Rally, Garrison, Bear Hunt)

---

## 🐛 Solución de Problemas

### El bot no responde en Discord
**Solución**:
1. Verificar que `DISCORD_TOKEN` sea correcto
2. Asegurar que el bot tiene `MESSAGE_CONTENT INTENT` activado
3. Verificar permisos del bot en el servidor
4. Ver logs: `python main.py` (modo debug)

### OCR no extrae bien las stats
**Solución**:
1. Asegurar que la imagen sea clara (mínimo 720p)
2. Verificar que ambos lados (aliado y enemigo) sean visibles
3. Instalar Tesseract OCR en el sistema
4. Intentar de nuevo con mejor resolución

### El bot usa mucha memoria en RPi
**Solución**:
1. OCR requiere ~50MB al iniciar (normal)
2. Asegurar no haya otros procesos pesados
3. Reiniciar el bot ocasionalmente

### Servicio systemd no inicia
**Solución**:
1. Verificar ruta correcta en kingshot-bot.service
2. Verificar usuario correcto (knycat)
3. Ver logs: `journalctl -u kingshot-bot -n 50`

---

## 📞 Soporte y Contacto

Para problemas, consulta:
1. README.md
2. Código comentado en los archivos
3. Logs del bot

---

**Proyecto completado**: Diciembre 6, 2025
**Version**: 1.0.0
**Estado**: Listo para producción en Raspberry Pi 5
