# Kingshot Combat Calculator Bot

A Discord bot for calculating optimal troop compositions and battle strategies in the Kingshot mobile game. Optimized to run 24/7 on Raspberry Pi 5.

## Features

- **Screenshot Analysis**: Upload a single screenshot with allied (left) and enemy (right) stats
- **OCR Extraction**: Automatically extracts troop stats from Kingshot battle reports
- **Combat Simulator**: Calculates damage output based on actual Kingshot mechanics
- **Composition Optimizer**: Recommends optimal Infantry:Cavalry:Archers ratio to maximize damage
- **Multi-Battle Strategy**: Calculates how many battles are needed to defeat stronger enemies
- **Lightweight**: Optimized for Raspberry Pi 5 (< 100MB memory with OCR)

## How to Use

### Basic Command Flow

1. **Start calculation**:
   ```
   /calculate 900450
   ```
   (Enter your total available troops)

2. **Upload screenshot**:
   - Take a screenshot from the Kingshot battle report
   - Must show **LEFT side**: Your troop stats (Ataque, Defensa, Letalidad, Salud)
   - Must show **RIGHT side**: Enemy troop stats (same format)
   - Must include all three types: Infantería, Caballería, Arquero

3. **Get analysis**:
   - Bot extracts stats via OCR
   - Displays recommended troop composition
   - Shows win/loss prediction
   - Estimates battles needed if enemy is strong

### Example Usage

```
User: /calculate 900450
Bot: [Asks for screenshot]

User: [Uploads screenshot of battle report]
Bot: ✅ Analysis Complete!
     🛡️ Your Troops: Total 900,450
     ⚔️ Enemy Troops: [Extracted stats]
     📋 Recommendations:
        Optimal Formation: Infantry 50% | Cavalry 20% | Archers 30%
        Expected Result: Victory (1 battle needed)
```

## Installation

### Option 1: Local Installation (Windows/Mac/Linux)

#### Prerequisites
- Python 3.10+
- Discord Bot Token
- Tesseract OCR (optional, for screenshot analysis)

#### Setup

1. Clone or download this repository:
   ```bash
   git clone <repository> kingshot-bot
   cd kingshot-bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Tesseract OCR (Optional but recommended):
   - **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - **Mac**: `brew install tesseract`
   - **Linux**: `sudo apt-get install tesseract-ocr`

4. Create a `.env` file with your Discord bot token:
   ```
   DISCORD_TOKEN=your_bot_token_here
   ```

5. Run the bot:
   ```bash
   python main.py
   ```

### Option 2: Raspberry Pi 5 Installation (Recommended for 24/7)

#### Prerequisites
- Raspberry Pi 5 with Raspberry Pi OS (Bullseye or later)
- SSH access to your Pi
- Discord Bot Token

#### Automated Setup

1. SSH into your Raspberry Pi:
   ```bash
   ssh knycat@192.168.1.141
   ```

2. Download the project:
   ```bash
   git clone <repository> kingshot-bot
   cd kingshot-bot
   chmod +x install_rpi.sh
   ```

3. Run the installation script:
   ```bash
   ./install_rpi.sh
   ```

4. When prompted, enter your Discord Bot Token

5. Start the bot:
   ```bash
   source venv/bin/activate
   python main.py
   ```

#### Running as a Systemd Service (24/7 Auto-start)

To run the bot automatically on startup:

1. Copy the service file (from your PC):
   ```bash
   scp kingshot-bot.service knycat@192.168.1.141:~/kingshot-bot/
   ```

2. SSH into Pi and setup the service:
   ```bash
   ssh knycat@192.168.1.141
   cd ~/kingshot-bot
   sudo cp kingshot-bot.service /etc/systemd/system/
   ```

3. Edit the service file to match your setup:
   ```bash
   sudo nano /etc/systemd/system/kingshot-bot.service
   ```
   - Verify `User=knycat` (your username)
   - Verify `WorkingDirectory=/home/knycat/kingshot-bot` (your path)

4. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable kingshot-bot
   sudo systemctl start kingshot-bot
   ```

5. Check status:
   ```bash
   sudo systemctl status kingshot-bot
   ```

6. View logs in real-time:
   ```bash
   journalctl -u kingshot-bot -f
   ```

## File Structure

```
kingshot-bot/
├── main.py                    # Bot entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Template for environment variables
├── install_rpi.sh            # Installation script for Raspberry Pi
├── deploy_rpi.sh             # Remote deployment script
├── kingshot-bot.service      # Systemd service file for auto-start
├── cogs/
│   ├── commands.py           # Discord commands
│   └── battle_calculator.py  # Battle simulation logic
├── models/
│   ├── troop.py              # Troop data models
│   ├── hero.py               # Hero data models
│   └── battle.py             # Battle calculation engine
├── data/
│   ├── heroes.json           # Hero stats database
│   └── formations.json       # Recommended formations
├── utils/
│   ├── ocr_extractor.py      # Screenshot OCR processing
│   └── validators.py         # Data validation utilities
└── README.md
```

## Game Mechanics Implemented

The bot implements Kingshot's battle system accurately:

- **Damage Formula**: `Kills = √Troops × (Attack × Lethality) / (Defense × Health) × SkillMod`
- **Attack Order**: Infantry → Cavalry → Archers (sequential, simultaneous within type)
- **Counter System**: Infantry > Cavalry > Archers > Infantry (damage bonuses)
- **SkillMod Calculation**: Based on hero damage bonuses and city buffs
- **Turn-based Simulation**: Each turn cycles through all troop types for both sides

## Discord Commands

- `/calculate [tropas_totales]` - Start a battle analysis (enter total troops available)
- `/help` - Display help information about the bot

## Troubleshooting

### OCR not extracting stats correctly
- Ensure screenshot is clear and at least 720p resolution
- Make sure both allied (left) and enemy (right) sides are visible
- Check that Spanish language pack is installed on system

### Bot not responding on Discord
- Verify `DISCORD_TOKEN` is correct in `.env` file
- Check bot has MESSAGE_CONTENT intent enabled in Discord Developer Portal
- Ensure bot has permissions to read messages in the channel

### Raspberry Pi memory usage high
- OCR uses ~50MB on startup. This is normal
- If memory runs out, ensure no other heavy processes are running
- Consider disabling OCR if RPi is very constrained (though not recommended)

## Bot Permissions

The bot requires the following Discord permissions:
- Send Messages
- Embed Links
- Read Message History
- Read Messages/View Channels

## License

MIT

## Contributing

Suggestions and improvements welcome!


## Commands

- `/calculate` - Main command to analyze enemy troops and get composition recommendations
- `/help` - Display help information

## Discord Telegram Bridge

A new service can mirror selected Discord channels with Telegram chats in both directions.

### Required environment variables

Add these in `.env`:

- `DISCORD_TOKEN` (Discord bot token)
- `TELEGRAM_BOT_TOKEN` (Telegram bot token from BotFather)
- `OWNER_ID` (optional owner user ID for admin commands)

### Bridge commands (Discord slash commands)

- `/bridge_add channel telegram_chat_id [telegram_thread_id]`
- `/bridge_remove channel`
- `/bridge_list`
- `/bridge_enable channel`
- `/bridge_disable channel`

## Billing Panel

The repository now includes an internal web panel for month-end billing sync from ClickUp to Google Sheets.

### What it does

- Shows the ClickUp hierarchy as client -> month folder -> task list.
- Lets you select the clients or months you want to close.
- Runs a manual sync only when you press the button.
- Returns a per-task result with synced items, skipped items, and failures.
- **Settings page**: Configure your ClickUp token directly from the web interface without SSH or code editing.
- **Google Sheets info**: Shows structure and column mappings; provides shareable link for clients.

### Integration with Google Sheets

The panel uses **Google Sheets API** (not just a URL) for secure, automated synchronization:

1. **API-based** - Service account credentials authenticate programmatically
2. **Automatic column mapping** - Data syncs to the correct columns you configure
3. **Client-friendly** - Share the Google Sheets URL with clients; they see live invoices without accessing the API
4. **Customizable fields** - Map ClickUp custom fields (quantity, price) to any sheet columns

**How it works:**
```
Your ClickUp workspace
  ├─ Client (Space)
  │  └─ Month (Folder)
  │     └─ Tasks (List) → extracted via API
  ↓
Panel selects client/month, clicks "Sincronizar"
  ↓
Data validated (quantity + unit price required)
  ↓
Rows appended to Google Sheets via API
  ↓
Share sheet URL with client
  ↓
Client views invoices (read-only or editable, your choice)
```

### Run locally

1. Create `.env` with Google credentials (ClickUp token can be configured in the UI):
   ```
   GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
   GOOGLE_SHEETS_SPREADSHEET_ID=your_sheet_id
   GOOGLE_SHEETS_TAB_NAME=Facturas
   ```

2. Start the panel:
   ```bash
   python run_billing_panel.py
   ```

3. Open the browser at `http://localhost:8085`

4. **First time setup**: 
   - Click on "⚙️ Ajustes" (Settings) to add your ClickUp API token
   - Click on "📊 Google Sheets" to see column structure and share the link with clients
   - Your token and sync history are saved locally in JSON format

### Optional field mapping

You can customize how ClickUp custom fields map to the sheet and how rows are built:

- `CLICKUP_QUANTITY_FIELD_NAMES`
- `CLICKUP_UNIT_PRICE_FIELD_NAMES`
- `CLICKUP_REQUIRED_STATUS_NAME`
- `GOOGLE_SHEETS_COLUMNS`
- `/bridge_backfill channel [limit]`
- `/bridge_help`

### Bridge service on Raspberry Pi

- Python entry point: `bridge_bot.py`
- Systemd unit: `kingshot-bridge-bot.service`
- Deploy script support: `deploy_to_rpi_fixed.ps1` now copies and restarts this service.

Note: Telegram bots do not receive a standard realtime delete event for all user deletions, so Telegram -> Discord delete mirroring may not always be available.

## File Structure

```
├── main.py                    # Bot entry point
├── cogs/
│   ├── battle_calculator.py  # Battle simulation and calculation logic
│   └── commands.py            # Discord commands
├── models/
│   ├── troop.py              # Troop data models
│   ├── hero.py               # Hero data models
│   └── battle.py             # Battle calculation models
├── data/
│   ├── heroes.json           # Hero stats database
│   └── formations.json       # Recommended formations
├── utils/
│   ├── ocr_extractor.py      # Image OCR extraction
│   └── validators.py          # Data validation
├── requirements.txt
├── .env.example
└── README.md
```

## Game Mechanics

The bot implements Kingshot's battle system:

- **Damage Formula**: Kills = √Troops × (Attack × Lethality) / (Defense × Health) × SkillMod
- **Attack Order**: Infantry → Cavalry → Archers (sequential per turn)
- **Counter System**: Infantry > Cavalry > Archers > Infantry
- **SkillMod**: Calculated from hero damage bonuses and enemy defense reductions

## License

MIT
