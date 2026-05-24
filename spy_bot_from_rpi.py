"""Kingshot Player Spy Bot - Track and monitor players with shield timers."""

import os
import sys
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
from pathlib import Path
import re
import pytz
from typing import Optional
from spy_translations import get_user_language, translate, translate_reason

# Force unbuffered output for better logging
sys.stdout = open(sys.stdout.fileno(), mode='w', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', buffering=1)

print("=" * 60)
print("🚀 KINGSHOT SPY BOT STARTING...")
print("=" * 60)

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('SPY_BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', 0))

print(f"✓ Environment loaded - Owner ID: {OWNER_ID}")
print(f"✓ Token loaded: {'Yes' if DISCORD_TOKEN else 'No'}")

# Initialize bot - use only basic intents, no privileged ones
intents = discord.Intents.none()
intents.guilds = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Store owner ID in bot
bot.owner_id = OWNER_ID

# Data files
DATA_FILE = Path("data/spy_reports.json")
SHIELD_FILE = Path("data/shield_timers.json")
NOTIFICATIONS_FILE = Path("data/notifications.json")
USER_TIMEZONES_FILE = Path("data/user_timezones.json")
DATA_FILE.parent.mkdir(exist_ok=True)


def load_spy_data():
    """Load spy reports from JSON file."""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading spy data: {e}")
    return {"reports": []}


def save_spy_data(data):
    """Save spy reports to JSON file."""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving spy data: {e}")


def load_shield_data():
    """Load shield timers from JSON file."""
    if SHIELD_FILE.exists():
        try:
            with open(SHIELD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading shield data: {e}")
    return {"shields": []}


def save_shield_data(data):
    """Save shield timers to JSON file."""
    try:
        with open(SHIELD_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving shield data: {e}")


def load_notifications():
    """Load notification settings from JSON file."""
    if NOTIFICATIONS_FILE.exists():
        try:
            with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading notifications: {e}")
    return {"users": {}}


def save_notifications(data):
    """Save notification settings to JSON file."""
    try:
        with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving notifications: {e}")


def load_user_timezones():
    """Load user timezone preferences."""
    if USER_TIMEZONES_FILE.exists():
        try:
            with open(USER_TIMEZONES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading timezones: {e}")
    return {"timezones": {}}


def save_user_timezones(data):
    """Save user timezone preferences."""
    try:
        with open(USER_TIMEZONES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving timezones: {e}")


def get_user_timezone(user_id: int) -> pytz.timezone:
    """Get user's timezone or default to UTC."""
    tz_data = load_user_timezones()
    tz_str = tz_data["timezones"].get(str(user_id), "UTC")
    try:
        return pytz.timezone(tz_str)
    except:
        return pytz.UTC


def save_user_language(user_id: int, lang: str):
    """Save user's preferred language."""
    tz_data = load_user_timezones()
    if "languages" not in tz_data:
        tz_data["languages"] = {}
    tz_data["languages"][str(user_id)] = lang
    save_user_timezones(tz_data)


def get_user_language_saved(user_id: int) -> str:
    """Get user's saved language or default to English."""
    tz_data = load_user_timezones()
    return tz_data.get("languages", {}).get(str(user_id), "en")


def parse_time(time_str: str) -> Optional[tuple[int, int]]:
    """Parse time string in format HH:MM (24h format).
    
    Returns:
        (hours, minutes) or None if invalid
    """
    time_str = time_str.strip()
    
    # Pattern: HH:MM (24h format)
    pattern = r'^(\d{1,2}):(\d{2})$'
    match = re.match(pattern, time_str)
    
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            return hours, minutes
    
    return None


def validate_coordinates(coords: str) -> tuple[bool, str, str]:
    """Validate coordinates format: x:### y:###"""
    coords = coords.lower().strip()
    pattern = r'x:\s*(\d{3})\s+y:\s*(\d{3})'
    match = re.match(pattern, coords)
    
    if match:
        return True, match.group(1), match.group(2)
    return False, "", ""


def validate_alliance(alliance: str) -> tuple[bool, str]:
    """Validate alliance tag: exactly 3 letters. Case sensitive."""
    alliance = alliance.strip()
    if len(alliance) == 3 and alliance.isalpha():
        return True, alliance
    return False, ""


# Common timezones for quick selection
COMMON_TIMEZONES = [
    app_commands.Choice(name="UTC (GMT+0)", value="UTC"),
    app_commands.Choice(name="Europe/Madrid (GMT+1)", value="Europe/Madrid"),
    app_commands.Choice(name="Europe/London (GMT+0)", value="Europe/London"),
    app_commands.Choice(name="America/New_York (EST/EDT)", value="America/New_York"),
    app_commands.Choice(name="America/Los_Angeles (PST/PDT)", value="America/Los_Angeles"),
    app_commands.Choice(name="America/Chicago (CST/CDT)", value="America/Chicago"),
    app_commands.Choice(name="America/Mexico_City (CST)", value="America/Mexico_City"),
    app_commands.Choice(name="America/Sao_Paulo (BRT)", value="America/Sao_Paulo"),
    app_commands.Choice(name="Asia/Tokyo (JST)", value="Asia/Tokyo"),
    app_commands.Choice(name="Asia/Shanghai (CST)", value="Asia/Shanghai"),
    app_commands.Choice(name="Australia/Sydney (AEDT)", value="Australia/Sydney"),
]


@bot.event
async def on_ready():
    """Event handler for bot startup."""
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot user ID: {bot.user.id}')
    
    # Show server count
    guild_count = len(bot.guilds)
    print(f'\n📊 Connected to {guild_count} server(s):')
    for guild in bot.guilds:
        print(f'  - {guild.name} (ID: {guild.id})')
    
    # Start shield notification checker
    if not check_shield_notifications.is_running():
        check_shield_notifications.start()
        print('\n🔔 Shield notification checker started')
    
    # Sync commands
    print('\nSyncing commands to Discord...')
    try:
        synced = await bot.tree.sync()
        print(f'  ✓ Commands synced successfully! ({len(synced)} commands active)')
        for cmd in synced:
            print(f'    - /{cmd.name}: {cmd.description}')
    except Exception as e:
        print(f'  ✗ Error syncing commands: {e}')


@tasks.loop(minutes=1)
async def check_shield_notifications():
    """Check for shields expiring soon and send notifications."""
    try:
        shield_data = load_shield_data()
        notifications_data = load_notifications()
        
        now = datetime.now(pytz.UTC)
        
        for shield in shield_data["shields"]:
            expires_at = datetime.fromisoformat(shield["expires_at"])
            if expires_at.tzinfo is None:
                expires_at = pytz.UTC.localize(expires_at)
            
            time_until_expire = expires_at - now
            
            # Get user notification settings
            user_id = shield["added_by"]["user_id"]
            if str(user_id) not in notifications_data["users"]:
                continue
            
            if not notifications_data["users"][str(user_id)].get("enabled", False):
                continue
            
            # Check if shield expires in 10-11 minutes (WARNING notification)
            if timedelta(minutes=10) <= time_until_expire <= timedelta(minutes=11):
                # Check if warning notification already sent
                if shield.get("warning_sent", False):
                    continue
                
                # Send 10-minute warning
                try:
                    user = await bot.fetch_user(user_id)
                    user_tz = get_user_timezone(user_id)
                    user_lang = get_user_language_saved(user_id)
                    expires_local = expires_at.astimezone(user_tz)
                    
                    embed = discord.Embed(
                        title=translate('shield_expiring_soon', user_lang),
                        description=f"{translate('expires_in_10_min', user_lang)}",
                        color=discord.Color.orange()
                    )
                    
                    embed.add_field(name=f"👤 {translate('player', user_lang)}", value=shield['player_name'], inline=True)
                    embed.add_field(name=f"🏰 {translate('alliance', user_lang)}", value=shield['alliance'], inline=True)
                    coords = shield['coordinates']
                    embed.add_field(name=f"📍 {translate('coordinates', user_lang)}", value=f"x:{coords['x']} y:{coords['y']}", inline=True)
                    embed.add_field(
                        name=f"⏰ {translate('shield_expires', user_lang)}", 
                        value=f"{expires_local.strftime('%H:%M')} ({user_tz.zone})\n<t:{int(expires_at.timestamp())}:R>", 
                        inline=False
                    )
                    
                    embed.set_footer(text=translate('bot_by', user_lang))
                    
                    await user.send(embed=embed)
                    print(f"✉️ Sent 10-minute warning to {user} for {shield['player_name']}")
                    
                    # Mark warning as sent
                    shield["warning_sent"] = True
                    save_shield_data(shield_data)
                    
                except Exception as e:
                    print(f"Error sending warning to user {user_id}: {e}")
            
            # Check if shield just expired (0-1 minute past expiry) (EXPIRED notification)
            elif timedelta(minutes=-1) <= time_until_expire <= timedelta(minutes=0):
                # Check if expiry notification already sent
                if shield.get("expiry_sent", False):
                    continue
                
                # Send expiry notification
                try:
                    user = await bot.fetch_user(user_id)
                    user_tz = get_user_timezone(user_id)
                    user_lang = get_user_language_saved(user_id)
                    expires_local = expires_at.astimezone(user_tz)
                    
                    embed = discord.Embed(
                        title=translate('shield_expired', user_lang),
                        description=f"Shield for **{shield['player_name']}** has just expired!\n\n{translate('attack_now', user_lang)}",
                        color=discord.Color.red()
                    )
                    
                    embed.add_field(name=f"👤 {translate('player', user_lang)}", value=shield['player_name'], inline=True)
                    embed.add_field(name=f"🏰 {translate('alliance', user_lang)}", value=shield['alliance'], inline=True)
                    coords = shield['coordinates']
                    embed.add_field(name=f"📍 {translate('coordinates', user_lang)}", value=f"x:{coords['x']} y:{coords['y']}", inline=True)
                    embed.add_field(
                        name="🕐 Expired At", 
                        value=f"{expires_local.strftime('%H:%M')} ({user_tz.zone})\n<t:{int(expires_at.timestamp())}:R>", 
                        inline=False
                    )
                    
                    embed.set_footer(text=translate('bot_by', user_lang))
                    
                    await user.send(embed=embed)
                    print(f"🚨 Sent expiry alert to {user} for {shield['player_name']}")
                    
                    # Mark expiry notification as sent
                    shield["expiry_sent"] = True
                    save_shield_data(shield_data)
                    
                except Exception as e:
                    print(f"Error sending expiry alert to user {user_id}: {e}")
            
            # Remove expired shields (more than 2 minutes past expiry)
            elif time_until_expire < timedelta(minutes=-2):
                shield_data["shields"] = [s for s in shield_data["shields"] if s["id"] != shield["id"]]
                save_shield_data(shield_data)
                print(f"🗑️ Removed expired shield for {shield['player_name']}")
    
    except Exception as e:
        print(f"Error in shield notification checker: {e}")


@bot.event
async def on_guild_join(guild):
    """Event handler when bot joins a new server."""
    print(f'\n✅ Joined new server: {guild.name} (ID: {guild.id})')


@bot.event
async def on_guild_remove(guild):
    """Event handler when bot is removed from a server."""
    print(f'\n❌ Removed from server: {guild.name} (ID: {guild.id})')


@bot.tree.command(name="timezone")
@app_commands.describe(
    timezone="Select your timezone"
)
@app_commands.choices(timezone=COMMON_TIMEZONES)
async def timezone_command(
    interaction: discord.Interaction,
    timezone: str
):
    """Set your timezone for accurate shield timers."""
    
    try:
        tz = pytz.timezone(timezone)
        
        # Save user timezone
        tz_data = load_user_timezones()
        tz_data["timezones"][str(interaction.user.id)] = timezone
        save_user_timezones(tz_data)
        
        # Get current time in user's timezone
        now = datetime.now(pytz.UTC).astimezone(tz)
        
        embed = discord.Embed(
            title="🌍 Timezone Set",
            description=f"Your timezone has been set to **{timezone}**",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="⏰ Current Time",
            value=f"{now.strftime('%H:%M')} ({timezone})",
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ Info",
            value="This timezone will be used for:\n"
                  "• Shield timer calculations\n"
                  "• Notification times\n"
                  "• Display times in embeds",
            inline=False
        )
        
        embed.set_footer(text="Bot by KnyCat")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(
            f"❌ **Invalid Timezone**\n"
            f"Error: {str(e)}",
            ephemeral=True
        )


@bot.tree.command(name="language")
@app_commands.describe(
    language="Select your preferred language"
)
@app_commands.choices(language=[
    app_commands.Choice(name="🇬🇧 English", value="en"),
    app_commands.Choice(name="🇪🇸 Español", value="es"),
    app_commands.Choice(name="🇫🇷 Français", value="fr"),
    app_commands.Choice(name="🇩🇪 Deutsch", value="de"),
    app_commands.Choice(name="🇮🇹 Italiano", value="it"),
    app_commands.Choice(name="🇵🇹 Português", value="pt")
])
async def language_command(
    interaction: discord.Interaction,
    language: str
):
    """Set your preferred language for all bot responses."""
    from spy_translations import SUPPORTED_LANGUAGES
    
    # Save user language
    save_user_language(interaction.user.id, language)
    
    # Get language name
    lang_name = SUPPORTED_LANGUAGES.get(language, language)
    
    embed = discord.Embed(
        title=translate('language_set_title', language),
        description=f"{translate('language_set_desc', language)} **{lang_name}**",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="ℹ️ Info",
        value=translate('all_responses_in_language', language),
        inline=False
    )
    
    embed.set_footer(text=translate('bot_by', language))
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="spy")
@app_commands.describe(
    alliance="Alliance tag (3 letters, e.g., ABC)",
    name="Player name",
    x="X coordinate (0-999)",
    y="Y coordinate (0-999)",
    reason="Reason for tracking this player"
)
async def spy_command(
    interaction: discord.Interaction,
    alliance: str,
    name: str,
    x: int,
    y: int,
    reason: str
):
    """Add a player to the spy list for tracking."""
    
    # Validate alliance
    is_valid_alliance, alliance_normalized = validate_alliance(alliance)
    if not is_valid_alliance:
        await interaction.response.send_message(
            "❌ **Invalid Alliance Tag**\n"
            "Alliance must be exactly 3 letters (e.g., ABC, XYZ)",
            ephemeral=True
        )
        return
    
    # Validate coordinates
    if not (0 <= x <= 999 and 0 <= y <= 999):
        await interaction.response.send_message(
            "❌ **Invalid Coordinates**\n"
            "Coordinates must be between 0 and 999",
            ephemeral=True
        )
        return
    
    # Format coordinates with 3 digits
    x_str = str(x).zfill(3)
    y_str = str(y).zfill(3)
    
    # Validate name
    name = name.strip()
    if len(name) == 0:
        await interaction.response.send_message(
            "❌ **Invalid Player Name**\n"
            "Player name cannot be empty.",
            ephemeral=True
        )
        return
    
    # Validate reason
    reason = reason.strip()
    if len(reason) == 0:
        await interaction.response.send_message(
            "❌ **Invalid Reason**\n"
            "Reason cannot be empty.",
            ephemeral=True
        )
        return
    
    # Load existing data
    data = load_spy_data()
    
    # Create new report
    report = {
        "id": len(data["reports"]) + 1,
        "alliance": alliance_normalized,
        "name": name,
        "coordinates": {
            "x": x_str,
            "y": y_str
        },
        "reason": reason,
        "added_by": {
            "user_id": interaction.user.id,
            "username": str(interaction.user),
            "guild_id": interaction.guild_id if interaction.guild else None,
            "guild_name": interaction.guild.name if interaction.guild else "DM"
        },
        "timestamp": datetime.now(pytz.UTC).isoformat(),
        "last_updated": datetime.now(pytz.UTC).isoformat()
    }
    
    # Add to reports
    data["reports"].append(report)
    save_spy_data(data)
    
    # Get user's saved language (or default to English)
    lang = get_user_language_saved(interaction.user.id)
    
    # Translate reason to user's language
    translated_reason = translate_reason(reason, lang)
    
    # Create response embed
    embed = discord.Embed(
        title=translate('spy_added_title', lang),
        description=translate('player_added_desc', lang).format(name=name),
        color=discord.Color.green()
    )
    
    embed.add_field(name=f"🏰 {translate('alliance', lang)}", value=alliance_normalized, inline=True)
    embed.add_field(name=f"📍 {translate('coordinates', lang)}", value=f"x:{x_str} y:{y_str}", inline=True)
    embed.add_field(name="🆔 Report ID", value=f"#{report['id']}", inline=True)
    embed.add_field(name=f"📝 {translate('reason', lang)}", value=translated_reason, inline=False)
    embed.add_field(name=f"👤 {translate('added_by', lang)}", value=str(interaction.user), inline=True)
    embed.add_field(name=f"⏰ {translate('time', lang)}", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
    
    embed.set_footer(text=translate('bot_by', lang))
    
    await interaction.response.send_message(embed=embed)


async def player_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function for player names."""
    spy_data = load_spy_data()
    players = []
    
    for report in spy_data["reports"]:
        player_name = report["name"]
        # Filter by current input
        if current.lower() in player_name.lower():
            coords = report["coordinates"]
            # Show name with alliance and coords in the choice name
            display = f"{player_name} ({report['alliance']}) - x:{coords['x']} y:{coords['y']}"
            players.append(app_commands.Choice(name=display[:100], value=player_name))
    
    # Return max 25 choices (Discord limit)
    return players[:25]


@bot.tree.command(name="shield")
@app_commands.describe(
    player_name="Select a tracked player",
    start_time="Shield start time in 24h format (HH:MM, e.g., 14:30)",
    duration="Shield duration in hours"
)
@app_commands.autocomplete(player_name=player_autocomplete)
@app_commands.choices(duration=[
    app_commands.Choice(name="2 hours", value=2),
    app_commands.Choice(name="8 hours", value=8),
    app_commands.Choice(name="24 hours", value=24),
    app_commands.Choice(name="72 hours", value=72),
])
async def shield_command(
    interaction: discord.Interaction,
    player_name: str,
    start_time: str,
    duration: int
):
    """Add a shield timer for a tracked player with specific start time."""
    
    # Get user's timezone
    user_tz = get_user_timezone(interaction.user.id)
    
    # Parse start time
    parsed_time = parse_time(start_time)
    if not parsed_time:
        await interaction.response.send_message(
            "❌ **Invalid Time Format**\n"
            "Please use 24-hour format: `HH:MM`\n"
            "Examples: `14:30`, `09:00`, `23:45`",
            ephemeral=True
        )
        return
    
    hours, minutes = parsed_time
    
    # Find player in spy reports
    spy_data = load_spy_data()
    player_report = None
    
    for report in spy_data["reports"]:
        if report["name"].lower() == player_name.lower():
            player_report = report
            break
    
    if not player_report:
        await interaction.response.send_message(
            f"❌ **Player Not Found**\n"
            f"Player `{player_name}` is not in your tracked list.\n"
            f"Use `/spy` to add them first, or use `/list` to see tracked players.",
            ephemeral=True
        )
        return
    
    # Calculate shield start and end times
    now = datetime.now(pytz.UTC)
    now_user_tz = now.astimezone(user_tz)
    
    # Create datetime for today at specified time in user's timezone
    start_datetime = user_tz.localize(
        datetime(now_user_tz.year, now_user_tz.month, now_user_tz.day, hours, minutes)
    )
    
    # Check if time is in the past
    is_tomorrow = False
    if start_datetime < now_user_tz:
        time_diff = now_user_tz - start_datetime
        # If the time was in the last 12 hours, it's today (shield started recently)
        # If it's more than 12 hours ago, assume it's for tomorrow
        if time_diff.total_seconds() > 12 * 3600:  # More than 12 hours ago
            start_datetime += timedelta(days=1)
            is_tomorrow = True
        # else: it's today, shield started recently (keep as is)
    
    # Convert to UTC for storage
    start_datetime_utc = start_datetime.astimezone(pytz.UTC)
    expires_at_utc = start_datetime_utc + timedelta(hours=duration)
    
    # Create shield timer
    shield_data = load_shield_data()
    
    # Check if player already has an active shield
    existing_shield = None
    for shield in shield_data["shields"]:
        if (shield["player_name"].lower() == player_name.lower() and
            datetime.fromisoformat(shield["expires_at"]).replace(tzinfo=pytz.UTC) > now):
            existing_shield = shield
            break
    
    if existing_shield:
        # Update existing shield
        existing_shield["duration_hours"] = duration
        existing_shield["start_time"] = start_datetime_utc.isoformat()
        existing_shield["expires_at"] = expires_at_utc.isoformat()
        existing_shield["last_updated"] = now.isoformat()
        existing_shield["warning_sent"] = False
        existing_shield["expiry_sent"] = False
        existing_shield["timezone"] = str(user_tz)
        shield_id = existing_shield["id"]
        action = "updated"
    else:
        # Create new shield
        shield = {
            "id": len(shield_data["shields"]) + 1,
            "player_name": player_report["name"],
            "alliance": player_report["alliance"],
            "coordinates": player_report["coordinates"],
            "duration_hours": duration,
            "start_time": start_datetime_utc.isoformat(),
            "expires_at": expires_at_utc.isoformat(),
            "timezone": str(user_tz),
            "added_by": {
                "user_id": interaction.user.id,
                "username": str(interaction.user)
            },
            "warning_sent": False,
            "expiry_sent": False
        }
        shield_data["shields"].append(shield)
        shield_id = shield["id"]
        action = "added"
    
    save_shield_data(shield_data)
    
    # Convert times back to user's timezone for display
    start_display = start_datetime_utc.astimezone(user_tz)
    expires_display = expires_at_utc.astimezone(user_tz)
    
    # Get user's saved language
    lang = get_user_language_saved(interaction.user.id)
    
    # Create response embed
    action_translated = translate('added' if action == 'added' else 'updated', lang)
    embed = discord.Embed(
        title=translate('shield_added_title', lang),
        description=translate('shield_added_desc', lang).format(action=action_translated, name=player_report['name']),
        color=discord.Color.green() if action == "added" else discord.Color.blue()
    )
    
    embed.add_field(name=f"👤 {translate('player', lang)}", value=player_report['name'], inline=True)
    embed.add_field(name=f"🏰 {translate('alliance', lang)}", value=player_report['alliance'], inline=True)
    coords = player_report['coordinates']
    embed.add_field(name=f"📍 {translate('coordinates', lang)}", value=f"x:{coords['x']} y:{coords['y']}", inline=True)
    
    # Add warning if shield is scheduled for tomorrow
    start_note = ""
    if is_tomorrow:
        start_note = " ⚠️ **TOMORROW**"
    
    embed.add_field(
        name=f"🕐 {translate('shield_start', lang)}", 
        value=f"{start_display.strftime('%H:%M')} ({user_tz.zone}){start_note}\n<t:{int(start_datetime_utc.timestamp())}:R>",
        inline=True
    )
    embed.add_field(name=f"⏱️ {translate('duration', lang)}", value=f"{duration} {translate('hours', lang)}", inline=True)
    embed.add_field(
        name=f"⏰ {translate('shield_expires', lang)}", 
        value=f"{expires_display.strftime('%H:%M')} ({user_tz.zone})\n<t:{int(expires_at_utc.timestamp())}:R>",
        inline=True
    )
    
    embed.add_field(name="🆔 Shield ID", value=f"#{shield_id}", inline=True)
    
    embed.set_footer(text=f"{translate('notification_footer', lang)} • {translate('bot_by', lang)}")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="listplayers")
async def listplayers_command(interaction: discord.Interaction):
    """Show list of all tracked players (use before /shield command)."""
    
    spy_data = load_spy_data()
    
    if len(spy_data["reports"]) == 0:
        await interaction.response.send_message(
            "❌ **No Tracked Players**\n"
            "Use `/spy` to add players first.",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="👥 Tracked Players",
        description="Copy the exact player name to use with `/shield`",
        color=discord.Color.blue()
    )
    
    for report in spy_data["reports"][:25]:  # Show max 25
        coords = report["coordinates"]
        value = f"Alliance: {report['alliance']} | Coords: x:{coords['x']} y:{coords['y']}"
        embed.add_field(
            name=f"👤 {report['name']}",
            value=value,
            inline=False
        )
    
    if len(spy_data["reports"]) > 25:
        embed.set_footer(text=f"Showing first 25 of {len(spy_data['reports'])} players • Bot by KnyCat")
    else:
        embed.set_footer(text="Bot by KnyCat")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="notifications")
@app_commands.describe(
    enabled="Enable or disable shield expiry notifications"
)
@app_commands.choices(enabled=[
    app_commands.Choice(name="Enable", value=1),
    app_commands.Choice(name="Disable", value=0),
])
async def notifications_command(
    interaction: discord.Interaction,
    enabled: int
):
    """Enable or disable shield expiry notifications via DM."""
    
    notifications_data = load_notifications()
    user_id_str = str(interaction.user.id)
    
    if user_id_str not in notifications_data["users"]:
        notifications_data["users"][user_id_str] = {}
    
    notifications_data["users"][user_id_str]["enabled"] = bool(enabled)
    notifications_data["users"][user_id_str]["username"] = str(interaction.user)
    notifications_data["users"][user_id_str]["last_updated"] = datetime.now(pytz.UTC).isoformat()
    
    save_notifications(notifications_data)
    
    if enabled:
        embed = discord.Embed(
            title="🔔 Notifications Enabled",
            description="You will receive DM notifications 10 minutes before shields expire.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="ℹ️ Info",
            value="Make sure:\n"
                  "• You have DMs enabled\n"
                  "• The bot can send you messages\n"
                  "• You've set your timezone with `/timezone`\n"
                  "• You've added shield timers with `/shield`",
            inline=False
        )
    else:
        embed = discord.Embed(
            title="🔕 Notifications Disabled",
            description="You will no longer receive shield expiry notifications.",
            color=discord.Color.orange()
        )
    
    embed.set_footer(text="Bot by KnyCat")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="shields")
async def shields_command(interaction: discord.Interaction):
    """View all active shield timers."""
    
    shield_data = load_shield_data()
    now = datetime.now(pytz.UTC)
    user_tz = get_user_timezone(interaction.user.id)
    
    # Filter active shields
    active_shields = [
        s for s in shield_data["shields"]
        if datetime.fromisoformat(s["expires_at"]).replace(tzinfo=pytz.UTC) > now
    ]
    
    if len(active_shields) == 0:
        await interaction.response.send_message(
            "🛡️ **No Active Shields**\n"
            "Use `/shield` to add shield timers for tracked players.",
            ephemeral=True
        )
        return
    
    # Sort by expiry time
    active_shields.sort(key=lambda s: s["expires_at"])
    
    embed = discord.Embed(
        title="🛡️ Active Shield Timers",
        description=f"Showing {len(active_shields)} active shield(s)\nTimes shown in your timezone: {user_tz.zone}",
        color=discord.Color.blue()
    )
    
    for shield in active_shields[:10]:  # Show max 10
        expires_at = datetime.fromisoformat(shield["expires_at"]).replace(tzinfo=pytz.UTC)
        expires_local = expires_at.astimezone(user_tz)
        
        coords = shield['coordinates']
        time_remaining = expires_at - now
        hours_remaining = int(time_remaining.total_seconds() / 3600)
        minutes_remaining = int((time_remaining.total_seconds() % 3600) / 60)
        
        value = (
            f"**Alliance:** {shield['alliance']}\n"
            f"**Coordinates:** x:{coords['x']} y:{coords['y']}\n"
            f"**Duration:** {shield['duration_hours']}h\n"
            f"**Remaining:** {hours_remaining}h {minutes_remaining}m\n"
            f"**Expires:** {expires_local.strftime('%H:%M')} (<t:{int(expires_at.timestamp())}:R>)\n"
            f"**ID:** #{shield['id']}"
        )
        embed.add_field(
            name=f"👤 {shield['player_name']}",
            value=value,
            inline=False
        )
    
    if len(active_shields) > 10:
        embed.set_footer(text=f"Showing first 10 of {len(active_shields)} shields • Bot by KnyCat")
    else:
        embed.set_footer(text="Bot by KnyCat")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="removeshield")
@app_commands.describe(
    shield_id="Shield ID to remove (from /shields)"
)
async def removeshield_command(
    interaction: discord.Interaction,
    shield_id: int
):
    """Remove a shield timer."""
    
    shield_data = load_shield_data()
    
    # Find shield
    shield_to_remove = None
    for shield in shield_data["shields"]:
        if shield["id"] == shield_id:
            shield_to_remove = shield
            break
    
    if not shield_to_remove:
        await interaction.response.send_message(
            f"❌ **Shield Not Found**\n"
            f"No shield found with ID #{shield_id}",
            ephemeral=True
        )
        return
    
    # Remove shield
    shield_data["shields"] = [s for s in shield_data["shields"] if s["id"] != shield_id]
    save_shield_data(shield_data)
    
    embed = discord.Embed(
        title="🗑️ Shield Removed",
        description=f"Shield timer for **{shield_to_remove['player_name']}** has been removed.",
        color=discord.Color.orange()
    )
    
    embed.add_field(name="👤 Player", value=shield_to_remove['player_name'], inline=True)
    embed.add_field(name="🏰 Alliance", value=shield_to_remove['alliance'], inline=True)
    embed.set_footer(text="Bot by KnyCat")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="list")
@app_commands.describe(
    alliance="Filter by alliance (optional)",
    player="Filter by player name (optional)"
)
async def list_command(
    interaction: discord.Interaction,
    alliance: str = None,
    player: str = None
):
    """List all tracked players."""
    
    data = load_spy_data()
    reports = data["reports"]
    
    # Get user's language
    lang = get_user_language_saved(interaction.user.id)
    
    if len(reports) == 0:
        await interaction.response.send_message(
            translate('no_tracked_players', lang),
            ephemeral=True
        )
        return
    
    # Apply filters
    filtered_reports = reports
    
    if alliance:
        alliance_normalized = alliance.strip()
        filtered_reports = [r for r in filtered_reports if r["alliance"] == alliance_normalized]
    
    if player:
        player_lower = player.strip().lower()
        filtered_reports = [r for r in filtered_reports if player_lower in r["name"].lower()]
    
    if len(filtered_reports) == 0:
        await interaction.response.send_message(
            "❌ **No Matches Found**\n"
            f"No players found matching your filters.",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title=translate('tracked_players', lang),
        description=translate('showing_players', lang).format(count=len(filtered_reports)),
        color=discord.Color.blue()
    )
    
    for report in filtered_reports[:10]:  # Show max 10
        coords = report["coordinates"]
        # Translate the reason
        translated_reason = translate_reason(report['reason'], lang)
        value = (
            f"**{translate('alliance', lang)}:** {report['alliance']}\n"
            f"**{translate('coordinates', lang)}:** x:{coords['x']} y:{coords['y']}\n"
            f"**{translate('reason', lang)}:** {translated_reason}\n"
            f"**{translate('added_by', lang)}:** {report['added_by']['username']}\n"
            f"**ID:** #{report['id']}"
        )
        embed.add_field(
            name=f"👤 {report['name']}",
            value=value,
            inline=False
        )
    
    embed.set_footer(text=translate('bot_by', lang))
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="editspy")
@app_commands.describe(
    report_id="Report ID to edit (from /list)",
    alliance="New alliance tag (3 letters, optional)",
    name="New player name (optional)",
    x="New X coordinate (0-999, optional)",
    y="New Y coordinate (0-999, optional)",
    reason="New reason (optional)"
)
async def editspy_command(
    interaction: discord.Interaction,
    report_id: int,
    alliance: str = None,
    name: str = None,
    x: int = None,
    y: int = None,
    reason: str = None
):
    """Edit an existing spy report. Only provide the fields you want to change."""
    
    data = load_spy_data()
    reports = data["reports"]
    
    # Find report
    report = None
    for r in reports:
        if r["id"] == report_id:
            report = r
            break
    
    if not report:
        await interaction.response.send_message(
            f"❌ **Report Not Found**\n"
            f"No report found with ID #{report_id}",
            ephemeral=True
        )
        return
    
    # Track what was changed
    changes = []
    old_values = {}
    
    # Update alliance if provided
    if alliance is not None:
        is_valid_alliance, alliance_normalized = validate_alliance(alliance)
        if not is_valid_alliance:
            await interaction.response.send_message(
                "❌ **Invalid Alliance Tag**\n"
                "Alliance must be exactly 3 letters (e.g., ABC, XYZ)",
                ephemeral=True
            )
            return
        old_values['alliance'] = report['alliance']
        report['alliance'] = alliance_normalized
        changes.append(f"Alliance: `{old_values['alliance']}` → `{alliance_normalized}`")
    
    # Update name if provided
    if name is not None:
        name = name.strip()
        if len(name) == 0:
            await interaction.response.send_message(
                "❌ **Invalid Player Name**\n"
                "Player name cannot be empty.",
                ephemeral=True
            )
            return
        old_values['name'] = report['name']
        report['name'] = name
        changes.append(f"Name: `{old_values['name']}` → `{name}`")
    
    # Update coordinates if provided
    if x is not None or y is not None:
        # If only one coordinate is provided, keep the other one
        new_x = x if x is not None else int(report['coordinates']['x'])
        new_y = y if y is not None else int(report['coordinates']['y'])
        
        # Validate coordinates
        if not (0 <= new_x <= 999 and 0 <= new_y <= 999):
            await interaction.response.send_message(
                "❌ **Invalid Coordinates**\n"
                "Coordinates must be between 0 and 999",
                ephemeral=True
            )
            return
        
        old_coords = report['coordinates']
        old_values['coordinates'] = f"x:{old_coords['x']} y:{old_coords['y']}"
        
        # Format coordinates with 3 digits
        x_str = str(new_x).zfill(3)
        y_str = str(new_y).zfill(3)
        
        report['coordinates'] = {
            "x": x_str,
            "y": y_str
        }
        changes.append(f"Coordinates: `{old_values['coordinates']}` → `x:{x_str} y:{y_str}`")
    
    # Update reason if provided
    if reason is not None:
        reason = reason.strip()
        if len(reason) == 0:
            await interaction.response.send_message(
                "❌ **Invalid Reason**\n"
                "Reason cannot be empty.",
                ephemeral=True
            )
            return
        old_values['reason'] = report['reason']
        report['reason'] = reason
        changes.append(f"Reason: `{old_values['reason']}` → `{reason}`")
    
    # Check if any changes were made
    if len(changes) == 0:
        await interaction.response.send_message(
            "⚠️ **No Changes Made**\n"
            "You need to provide at least one field to update.",
            ephemeral=True
        )
        return
    
    # Update timestamp
    report['last_updated'] = datetime.now(pytz.UTC).isoformat()
    
    # Save changes
    save_spy_data(data)
    
    # Create response embed
    embed = discord.Embed(
        title="✏️ Spy Report Updated",
        description=f"Report **#{report_id}** has been updated successfully.",
        color=discord.Color.green()
    )
    
    # Show current values
    coords = report['coordinates']
    embed.add_field(name="👤 Player", value=report['name'], inline=True)
    embed.add_field(name="🏰 Alliance", value=report['alliance'], inline=True)
    embed.add_field(name="📍 Coordinates", value=f"x:{coords['x']} y:{coords['y']}", inline=True)
    embed.add_field(name="📝 Reason", value=report['reason'], inline=False)
    
    # Show what changed
    changes_text = "\n".join(changes)
    embed.add_field(name="📋 Changes Made", value=changes_text, inline=False)
    
    embed.add_field(name="👤 Edited by", value=str(interaction.user), inline=True)
    embed.add_field(name="⏰ Time", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
    
    embed.set_footer(text="Bot by KnyCat")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="remove")
@app_commands.describe(
    report_id="Report ID to remove (from /list)"
)
async def remove_command(
    interaction: discord.Interaction,
    report_id: int
):
    """Remove a player from the spy list."""
    
    data = load_spy_data()
    reports = data["reports"]
    
    # Find report
    report_to_remove = None
    for report in reports:
        if report["id"] == report_id:
            report_to_remove = report
            break
    
    if not report_to_remove:
        await interaction.response.send_message(
            f"❌ **Report Not Found**\n"
            f"No report found with ID #{report_id}",
            ephemeral=True
        )
        return
    
    # Remove report
    data["reports"] = [r for r in reports if r["id"] != report_id]
    save_spy_data(data)
    
    embed = discord.Embed(
        title="🗑️ Report Removed",
        description=f"Player **{report_to_remove['name']}** has been removed from the spy list.",
        color=discord.Color.orange()
    )
    
    embed.add_field(name="🏰 Alliance", value=report_to_remove['alliance'], inline=True)
    coords = report_to_remove['coordinates']
    embed.add_field(name="📍 Coordinates", value=f"x:{coords['x']} y:{coords['y']}", inline=True)
    embed.set_footer(text="Bot by KnyCat")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="search")
@app_commands.describe(
    query="Search by name, alliance, or coordinates"
)
async def search_command(
    interaction: discord.Interaction,
    query: str
):
    """Search for tracked players."""
    
    data = load_spy_data()
    reports = data["reports"]
    
    if len(reports) == 0:
        await interaction.response.send_message(
            "📋 **No Tracked Players**\n"
            "Use `/spy` to add players to track.",
            ephemeral=True
        )
        return
    
    query_lower = query.strip().lower()
    
    # Search in name, alliance, reason, and coordinates
    matches = []
    for report in reports:
        coords = report["coordinates"]
        coords_str = f"x:{coords['x']} y:{coords['y']}".lower()
        
        if (query_lower in report['name'].lower() or
            query_lower in report['alliance'].lower() or
            query_lower in report['reason'].lower() or
            query_lower in coords_str):
            matches.append(report)
    
    if len(matches) == 0:
        await interaction.response.send_message(
            f"❌ **No Matches Found**\n"
            f"No players found matching: `{query}`",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="🔍 Search Results",
        description=f"Found {len(matches)} match(es) for: `{query}`",
        color=discord.Color.blue()
    )
    
    for report in matches[:10]:  # Show max 10
        coords = report["coordinates"]
        value = (
            f"**Alliance:** {report['alliance']}\n"
            f"**Coordinates:** x:{coords['x']} y:{coords['y']}\n"
            f"**Reason:** {report['reason']}\n"
            f"**ID:** #{report['id']}"
        )
        embed.add_field(
            name=f"👤 {report['name']}",
            value=value,
            inline=False
        )
    
    if len(matches) > 10:
        embed.set_footer(text=f"Showing first 10 of {len(matches)} results • Bot by KnyCat")
    else:
        embed.set_footer(text="Bot by KnyCat")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="help")
async def help_command(interaction: discord.Interaction):
    """Show all available commands and how to use them."""
    
    embed = discord.Embed(
        title="📚 Kingshot Spy Bot - Help Guide",
        description="Here's everything you need to know to use this bot!",
        color=discord.Color.blue()
    )
    
    # Setup commands
    embed.add_field(
        name="⚙️ **Setup Commands** (Do this first!)",
        value=(
            "**`/timezone`** - Set your timezone\n"
            "└ Choose your timezone from the list\n"
            "└ Example: Select `Europe/Madrid`\n"
            "└ *This is important for shield timers!*\n\n"
            
            "**`/notifications`** - Turn notifications ON/OFF\n"
            "└ Choose: `Enable` or `Disable`\n"
            "└ *Get DM alerts 10 min before shields expire*"
        ),
        inline=False
    )
    
    # Tracking commands
    embed.add_field(
        name="🕵️ **Player Tracking Commands**",
        value=(
            "**`/spy`** - Add a player to track\n"
            "└ `alliance`: 3 letters (e.g., ABC)\n"
            "└ `name`: Player name\n"
            "└ `x`: X coordinate (0-999)\n"
            "└ `y`: Y coordinate (0-999)\n"
            "└ `reason`: Why are you tracking them?\n"
            "└ Example: `/spy alliance:ABC name:Enemy x:600 y:999 reason:Attacked me`\n\n"
            
            "**`/list`** - View all tracked players\n"
            "└ Optional: Filter by alliance or name\n"
            "└ Example: `/list alliance:ABC`\n\n"
            
            "**`/search`** - Search for a player\n"
            "└ `query`: Type any part of name, alliance, or coordinates\n"
            "└ Example: `/search query:Enemy`\n\n"
            
            "**`/editspy`** - Edit a tracked player\n"
            "└ `report_id`: The ID number (get it from `/list`)\n"
            "└ Only fill the fields you want to change\n"
            "└ Example: `/editspy report_id:5 x:700 y:800`\n\n"
            
            "**`/remove`** - Remove a tracked player\n"
            "└ `report_id`: The ID number (get it from `/list`)\n"
            "└ Example: `/remove report_id:5`"
        ),
        inline=False
    )
    
    # Shield commands
    embed.add_field(
        name="🛡️ **Shield Timer Commands**",
        value=(
            "**`/shield`** - Add a shield timer\n"
            "└ `player_name`: Start typing and select from list\n"
            "└ `start_time`: When shield starts (24h format: HH:MM)\n"
            "└ `duration`: Choose 2h, 8h, 24h, or 72h\n"
            "└ Example: `/shield player_name:Enemy start_time:14:30 duration:24 hours`\n"
            "└ *You'll get a DM 10 minutes before it expires!*\n\n"
            
            "**`/shields`** - View all active shields\n"
            "└ Shows time remaining for each shield\n\n"
            
            "**`/removeshield`** - Remove a shield timer\n"
            "└ `shield_id`: The ID number (get it from `/shields`)\n"
            "└ Example: `/removeshield shield_id:3`\n\n"
            
            "**`/listplayers`** - Quick list of tracked players\n"
            "└ Use this to see player names for `/shield` command"
        ),
        inline=False
    )
    
    # Info commands
    embed.add_field(
        name="📊 **Information Commands**",
        value=(
            "**`/stats`** - Bot statistics\n"
            "└ See total reports, alliances, and shields\n\n"
            
            "**`/help`** - Show this help message\n"
            "└ You're reading it right now! 😊"
        ),
        inline=False
    )
    
    # Quick start guide
    embed.add_field(
        name="🚀 **Quick Start Guide**",
        value=(
            "**1.** Set your timezone: `/timezone`\n"
            "**2.** Enable notifications: `/notifications`\n"
            "**3.** Add a player to track: `/spy`\n"
            "**4.** Add a shield timer: `/shield`\n"
            "**5.** View your shields: `/shields`\n\n"
            "**💡 Tip:** Use `/listplayers` to see all tracked players before using `/shield`"
        ),
        inline=False
    )
    
    embed.set_footer(text="Need more help? Contact the bot owner • Bot by KnyCat")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="stats")
async def stats_command(interaction: discord.Interaction):
    """Show spy bot statistics."""
    
    try:
        print(f"[STATS] Command called by user {interaction.user.id}")
        data = load_spy_data()
        shield_data = load_shield_data()
        reports = data["reports"]
        print(f"[STATS] Loaded {len(reports)} reports and {len(shield_data['shields'])} shields")
        
        if len(reports) == 0:
            await interaction.response.send_message(
                "📊 **No Data Yet**\n"
                "Use `/spy` to start tracking players.",
                ephemeral=True
            )
            return
        
        # Calculate user statistics
        user_stats = {}
            for report in reports:
            user_id = report['added_by']['user_id']
            username = report['added_by']['username']
            if user_id not in user_stats:
                user_stats[user_id] = {"name": username, "spy_count": 0, "shield_count": 0}
            user_stats[user_id]["spy_count"] += 1
    
        for shield in shield_data["shields"]:
            user_id = shield['user_id']
            username = shield['username']
            if user_id not in user_stats:
                user_stats[user_id] = {"name": username, "spy_count": 0, "shield_count": 0}
            user_stats[user_id]["shield_count"] += 1
    
        # Calculate total command count for each user
        for user_id in user_stats:
            user_stats[user_id]["total"] = user_stats[user_id]["spy_count"] + user_stats[user_id]["shield_count"]
    
        # Get top users
        top_users = sorted(user_stats.items(), key=lambda x: x[1]["total"], reverse=True)[:10]
    
        # Calculate alliance stats
        alliances = {}
        for report in reports:
            alliance = report['alliance']
            alliances[alliance] = alliances.get(alliance, 0) + 1
    
        # Count active shields
        now = datetime.now(pytz.UTC)
        active_shields = sum(1 for s in shield_data["shields"] if datetime.fromisoformat(s["expires_at"]).replace(tzinfo=pytz.UTC) > now)
    
        # Top alliances
        top_alliances = sorted(alliances.items(), key=lambda x: x[1], reverse=True)[:5]
    
        embed = discord.Embed(
            title="📊 Spy Bot Statistics",
            color=discord.Color.purple()
        )
    
        embed.add_field(
            name="📈 General",
            value=f"**Total Reports:** {len(reports)}\n"
                  f"**Unique Alliances:** {len(alliances)}\n"
                  f"**Active Shields:** {active_shields}\n"
                  f"**Active Users:** {len(user_stats)}",
            inline=False
        )
    
        if top_alliances:
            alliance_list = "\n".join([f"**{alliance}**: {count} player(s)" for alliance, count in top_alliances])
            embed.add_field(
                name="🏆 Top Tracked Alliances",
                value=alliance_list,
                inline=False
            )
    
        # Show top users only for owner
            if interaction.user.id == OWNER_ID and top_users:
                user_list = "\n".join([
                    f"**{data['name']}**: {data['total']} ({data['spy_count']} spy + {data['shield_count']} shield)"
                    for uid, data in top_users
                ])
                embed.add_field(
                    name="👥 Top Active Users",
                    value=user_list,
                    inline=False
                )
        
            embed.set_footer(text="Bot by KnyCat")
        
            print(f"[STATS] Sending embed response")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        print(f"[STATS] Response sent successfully")
    
    except Exception as e:
        print(f"[STATS ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        try:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
        except:
            await interaction.followup.send(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )


async def main():
    """Main function to start the bot."""
    print("\n🔐 Checking authentication...")
    if not DISCORD_TOKEN:
        print('❌ ERROR: SPY_BOT_TOKEN not found in .env file')
        print('Please add: SPY_BOT_TOKEN=your_token_here to .env')
        return
    
    print("✓ Token validated")
    print("\n🌐 Connecting to Discord...")
    try:
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    print("\n📦 Initializing async runtime...")
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Bot stopped by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
