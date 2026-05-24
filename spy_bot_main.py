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
import asyncio
from typing import Optional
from spy_translations import get_user_language, translate, translate_reason
from utils.parse_ranking_file import parse_ranking_file

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

# Initialize bot - enable guilds, messages, and message content for interactive flows
intents = discord.Intents.none()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.members = True
intents.reactions = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Store owner ID in bot
bot.owner_id = OWNER_ID

# Data files
DATA_FILE = Path("data/spy_reports.json")
SHIELD_FILE = Path("data/shield_timers.json")
NOTIFICATIONS_FILE = Path("data/notifications.json")
USER_TIMEZONES_FILE = Path("data/user_timezones.json")
EVENTS_FILE = Path("data/events.json")
REACTION_MESSAGE_VERSION = 1
HEADER_VERSION = 1

CHANNEL_NAMES = {
    "bear": "🐻｜bear",
    "arena": "⚔️｜arena",
    "events": "🏆｜events",
    "reaction": "📜｜reaction-roles",
}

ROLE_NAMES = {
    "bear": "Bear",
    "arena": "Arena",
    "event": "Event",
}

REACTION_EMOJIS = {
    "bear": "🐻",
    "arena": "⚔️",
    "event": "🏆",
}

EVENT_NAME_CHOICES = [
    "Hall of Governors",
    "All Out Event",
    "Viking Vengeance",
    "Cesares Fury",
    "Cesares Fury Boss",
    "Swordland Showdown",
    "Kingdom vs Kingdom",
    "Santuary Battles",
    "Castle Battle",
]
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


def load_event_data():
    """Load scheduled events and reaction-role metadata."""
    if EVENTS_FILE.exists():
        try:
            with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "guilds" not in data:
                    data = {"guilds": {}}
                return data
        except Exception as e:
            print(f"Error loading events: {e}")
    return {"guilds": {}}


def save_event_data(data):
    """Persist scheduled events and reaction-role metadata."""
    try:
        with open(EVENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving events: {e}")


def ensure_guild_events(data, guild_id: int) -> dict:
    """Ensure guild bucket exists with defaults."""
    gid = str(guild_id)
    if gid not in data["guilds"]:
        data["guilds"][gid] = {
            "events": [],
            "configs": {
                "bear": {"reminders": [60, 10, 0]},
                "arena": {"reminders": [60, 10, 0]},
                "event": {"reminders": [60, 10, 0]},
            },
            "reaction_message_id": None,
            "reaction_channel_id": None,
            "reaction_version": 0,
            "headers": {},
        }
    return data["guilds"][gid]


def next_event_id(guild_data: dict) -> int:
    if not guild_data.get("events"):
        return 1
    return max(ev.get("id", 0) for ev in guild_data["events"]) + 1


def get_event_channel(guild: discord.Guild, event_type: str) -> Optional[discord.TextChannel]:
    if event_type == "bear":
        name = CHANNEL_NAMES["bear"]
    elif event_type == "arena":
        name = CHANNEL_NAMES["arena"]
    else:
        name = CHANNEL_NAMES["events"]
    return find_channel_by_name(guild, name)


def get_reminder_offsets(guild_data: dict, event_type: str) -> list[int]:
    configs = guild_data.get("configs", {})
    if event_type in configs:
        return configs[event_type].get("reminders", [60, 10, 0])
    return [60, 10, 0]


def build_reaction_embed() -> discord.Embed:
    embed = discord.Embed(
        title="📜 Choose Your Adventure!",
        description="React below to gain access to special event pings!",
        color=discord.Color.dark_gold()
    )
    embed.add_field(
        name="🐻 — Bear",
        value="Get notified before bear attacks",
        inline=False,
    )
    embed.add_field(
        name="⚔️ — Arena",
        value="Be there when the arena opens",
        inline=False,
    )
    embed.add_field(
        name="🏆 — Event",
        value="Stay in the loop for in game events!",
        inline=False,
    )
    embed.set_footer(text="👑 Kingshot Bot • Role Reactions • UTC")
    return embed


def role_key_from_emoji(emoji: str) -> Optional[str]:
    for key, emj in REACTION_EMOJIS.items():
        if emoji == emj:
            return key
    return None


def build_channel_header_embed(event_type: str) -> discord.Embed:
    title = "🏷️ Event Notifications"
    description = "This channel posts upcoming Event notifications!"
    embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
    embed.add_field(name="⏱️ Event Reminder", value="60 minutes before start", inline=False)
    embed.add_field(name="🔔 Final Call", value="10 minutes before start", inline=False)
    embed.add_field(name="🎯 Event Start", value="When the event begins", inline=False)
    if event_type == "bear":
        embed.add_field(name="🗓️ Bear Commands", value="/setbearping • /cancelbear", inline=False)
    elif event_type == "arena":
        embed.add_field(name="⚔️ Arena Commands", value="/setarenaping", inline=False)
    else:
        embed.add_field(name="🏆 Event Commands", value="/addevent • /cancelevent • /listevent • /seteventpings", inline=False)
    embed.add_field(name="⚙️ Settings", value="Use /seteventpings to adjust reminders (UTC)", inline=False)
    embed.set_footer(text="👑 Kingshot Bot • Event Alerts • UTC")
    return embed


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


def parse_date_time_utc(date_str: str, time_str: str) -> Optional[datetime]:
    """Parse date (YYYY-MM-DD) and time (HH:MM) to a UTC datetime."""
    try:
        y, m, d = [int(x) for x in date_str.split("-")]
        parsed = datetime(y, m, d)
    except Exception:
        return None
    parsed_time = parse_time(time_str)
    if not parsed_time:
        return None
    hh, mm = parsed_time
    try:
        dt = datetime(y, m, d, hh, mm, tzinfo=pytz.UTC)
        return dt
    except Exception:
        return None


def find_channel_by_name(guild: discord.Guild, target: str) -> Optional[discord.TextChannel]:
    for ch in guild.text_channels:
        if ch.name == target:
            return ch
    return None


def get_role_for_key(guild: discord.Guild, key: str) -> Optional[discord.Role]:
    role_name = ROLE_NAMES.get(key)
    if not role_name:
        return None
    return discord.utils.get(guild.roles, name=role_name)


def validate_coordinates(coords: str) -> tuple[bool, str, str]:
    """Validate coordinates format: x:### y:### (now allows up to 4 digits)"""
    coords = coords.lower().strip()
    # Allow 1-4 digits per axis (0-9999)
    pattern = r'x:\s*(\d{1,4})\s+y:\s*(\d{1,4})'
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


async def ensure_reaction_roles_for_guild(guild: discord.Guild):
    data = load_event_data()
    guild_data = ensure_guild_events(data, guild.id)
    channel = find_channel_by_name(guild, CHANNEL_NAMES["reaction"])
    if not channel:
        return
    existing_message = None
    if guild_data.get("reaction_message_id") and guild_data.get("reaction_channel_id") == channel.id:
        try:
            existing_message = await channel.fetch_message(guild_data["reaction_message_id"])
        except Exception:
            existing_message = None
    embed = build_reaction_embed()
    if existing_message and guild_data.get("reaction_version", 0) == REACTION_MESSAGE_VERSION:
        try:
            await existing_message.edit(embed=embed)
            message = existing_message
        except Exception:
            message = await channel.send(embed=embed)
    else:
        message = await channel.send(embed=embed)
        guild_data["reaction_message_id"] = message.id
        guild_data["reaction_channel_id"] = channel.id
        guild_data["reaction_version"] = REACTION_MESSAGE_VERSION
    for emoji in REACTION_EMOJIS.values():
        try:
            await message.add_reaction(emoji)
        except Exception:
            pass
    save_event_data(data)


async def ensure_channel_headers(guild: discord.Guild):
    data = load_event_data()
    guild_data = ensure_guild_events(data, guild.id)
    headers = guild_data.get("headers", {})
    for event_type in ["bear", "arena", "event"]:
        channel = get_event_channel(guild, event_type)
        if not channel:
            continue
        header_info = headers.get(event_type)
        existing = None
        if header_info and header_info.get("channel_id") == channel.id:
            try:
                existing = await channel.fetch_message(header_info.get("message_id"))
            except Exception:
                existing = None
        embed = build_channel_header_embed(event_type)
        if existing and header_info.get("version", 0) == HEADER_VERSION:
            try:
                await existing.edit(embed=embed)
                continue
            except Exception:
                pass
        sent = await channel.send(embed=embed)
        headers[event_type] = {
            "channel_id": channel.id,
            "message_id": sent.id,
            "version": HEADER_VERSION,
        }
    guild_data["headers"] = headers
    save_event_data(data)


async def send_event_ping(guild: discord.Guild, event: dict, offset: int):
    channel = None
    try:
        if event.get("channel_id"):
            channel = guild.get_channel(event["channel_id"])
    except Exception:
        channel = None
    if not channel:
        channel = get_event_channel(guild, event.get("type", "event"))
    if not channel:
        return
    role = get_role_for_key(guild, "bear" if event.get("type") == "bear" else ("arena" if event.get("type") == "arena" else "event"))
    role_mention = role.mention if role else ""
    start_dt = datetime.fromisoformat(event["start_time"])
    ts = int(start_dt.timestamp())
    when_text = f"<t:{ts}:F> (<t:{ts}:R>)"
    if offset == 0:
        title = "🎯 Event Starting Now"
    elif offset == 10:
        title = "🔔 Final Call"
    else:
        title = "⏱️ Event Reminder"
    embed = discord.Embed(
        title=title,
        description=f"{event.get('name','Event')}\nStart: {when_text}",
        color=discord.Color.gold()
    )
    embed.set_footer(text="UTC time • shown in your local time by Discord")
    content = role_mention if role_mention else None
    sent = await channel.send(content=content, embed=embed)
    return sent


async def delete_event_message(guild: discord.Guild, event: dict):
    if not event.get("message_id"):
        return
    channel = None
    if event.get("channel_id"):
        channel = guild.get_channel(event["channel_id"])
    if not channel:
        channel = get_event_channel(guild, event.get("type", "event"))
    if not channel:
        return
    try:
        msg = await channel.fetch_message(event["message_id"])
        await msg.delete()
    except Exception:
        return


def ensure_arena_event_entry(guild_data: dict) -> bool:
    now = datetime.now(pytz.UTC)
    today_midnight = datetime(now.year, now.month, now.day, 0, 0, tzinfo=pytz.UTC)
    if now >= today_midnight:
        target = today_midnight + timedelta(days=1)
    else:
        target = today_midnight
    upcoming = [e for e in guild_data.get("events", []) if e.get("type") == "arena"]
    for ev in upcoming:
        try:
            start_dt = datetime.fromisoformat(ev["start_time"])
        except Exception:
            continue
        if start_dt >= now:
            return False
    event_id = next_event_id(guild_data)
    guild_data["events"].append({
        "id": event_id,
        "type": "arena",
        "name": "Arena Battles",
        "start_time": target.isoformat(),
        "channel_id": None,
        "message_id": None,
        "reminder_offsets": get_reminder_offsets(guild_data, "arena"),
        "sent_offsets": [],
        "created_by": {"user_id": 0, "username": "system"},
        "created_at": now.isoformat(),
    })
    return True


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


@tasks.loop(minutes=1)
async def check_event_notifications():
    """Check scheduled events, send reminders, and clean up past events."""
    try:
        data = load_event_data()
        now = datetime.now(pytz.UTC)
        changed = False
        for guild in bot.guilds:
            guild_data = ensure_guild_events(data, guild.id)
            if ensure_arena_event_entry(guild_data):
                changed = True
            for ev in list(guild_data.get("events", [])):
                try:
                    start_dt = datetime.fromisoformat(ev["start_time"])
                except Exception:
                    continue
                offsets = ev.get("reminder_offsets") or get_reminder_offsets(guild_data, ev.get("type", "event"))
                for offset in offsets:
                    sent_offsets = ev.setdefault("sent_offsets", [])
                    if offset in sent_offsets:
                        continue
                    trigger_time = start_dt - timedelta(minutes=offset)
                    if trigger_time <= now < trigger_time + timedelta(minutes=1):
                        await send_event_ping(guild, ev, offset)
                        sent_offsets.append(offset)
                        changed = True
                if now > start_dt + timedelta(minutes=5):
                    await delete_event_message(guild, ev)
                    guild_data["events"] = [x for x in guild_data["events"] if x["id"] != ev["id"]]
                    changed = True
        if changed:
            save_event_data(data)
    except Exception as e:
        print(f"Error in event notification checker: {e}")


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
    if not check_event_notifications.is_running():
        check_event_notifications.start()
        print('\n🔔 Event notification checker started')
    
    # Temporarily disabled to test command sync
    # for guild in bot.guilds:
    #     try:
    #         await ensure_reaction_roles_for_guild(guild)
    #         await ensure_channel_headers(guild)
    #     except Exception as e:
    #         print(f"Error ensuring setup for guild {guild.id}: {e}")
    
    # Sync commands globally (available in all servers)
    print('\nSyncing commands to Discord...')
    try:
        synced = await bot.tree.sync()
        print(f'  ✓ Commands synced globally: {len(synced)} commands')
        for cmd in synced:
            print(f'    - /{cmd.name}: {cmd.description}')
        print('\n  ℹ️  Note: Global commands may take up to 1 hour to appear in all servers')
    except Exception as e:
        print(f'  ✗ Error syncing commands: {e}')
        import traceback
        traceback.print_exc()


@bot.event
async def on_guild_join(guild):
    """Event handler when bot joins a new server."""
    print(f'\n✅ Joined new server: {guild.name} (ID: {guild.id})')


@bot.event
async def on_guild_remove(guild):
    """Event handler when bot is removed from a server."""
    print(f'\n❌ Removed from server: {guild.name} (ID: {guild.id})')


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    data = load_event_data()
    guild_data = ensure_guild_events(data, payload.guild_id)
    if payload.message_id != guild_data.get("reaction_message_id"):
        return
    role_key = role_key_from_emoji(str(payload.emoji))
    if not role_key:
        return
    role = get_role_for_key(guild, role_key)
    if not role:
        return
    member = payload.member or guild.get_member(payload.user_id)
    if not member:
        try:
            member = await guild.fetch_member(payload.user_id)
        except Exception:
            return
    try:
        await member.add_roles(role, reason="Reaction role opt-in")
    except Exception as e:
        print(f"Error adding role {role.name} to {member}: {e}")


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    data = load_event_data()
    guild_data = ensure_guild_events(data, payload.guild_id)
    if payload.message_id != guild_data.get("reaction_message_id"):
        return
    role_key = role_key_from_emoji(str(payload.emoji))
    if not role_key:
        return
    role = get_role_for_key(guild, role_key)
    if not role:
        return
    member = guild.get_member(payload.user_id)
    if not member:
        try:
            member = await guild.fetch_member(payload.user_id)
        except Exception:
            return
    try:
        await member.remove_roles(role, reason="Reaction role opt-out")
    except Exception as e:
        print(f"Error removing role {role.name} from {member}: {e}")


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
    app_commands.Choice(name="�🇹 Português", value="pt"),
    app_commands.Choice(name="🇫🇷 Français", value="fr"),
    app_commands.Choice(name="🇩🇪 Deutsch", value="de"),
    app_commands.Choice(name="🇳🇱 Nederlands", value="nl"),
    app_commands.Choice(name="🇸🇦 العربية", value="ar")
])
async def language_command(
    interaction: discord.Interaction,
    language: str
):
    """Set your preferred language for all bot responses."""
    from cogs.translations import get_text
    
    # Save user language preference
    print(f"DEBUG /language: Saving language '{language}' for user {interaction.user.id}")
    save_user_language(interaction.user.id, language)
    print(f"DEBUG /language: After save, getting language...")
    saved_lang = get_user_language_saved(interaction.user.id)
    print(f"DEBUG /language: Retrieved language: {saved_lang}")
    
    # Language names
    lang_names = {
        "en": "English",
        "es": "Español",
        "pt": "Português",
        "fr": "Français",
        "de": "Deutsch",
        "nl": "Nederlands",
        "ar": "العربية"
    }
    
    lang_name = lang_names.get(language, language)
    
    embed = discord.Embed(
        title="🌐 Language Set",
        description=f"✅ Your language has been set to **{lang_name}**",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="ℹ️ Info",
        value="All bot responses will now be in your selected language.",
        inline=False
    )
    
    embed.set_footer(text="Bot by KnyCat")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)





# @bot.tree.command(name="setbearping")
# @app_commands.describe(
#     reminder1="Minutos antes (ej: 60)",
#     reminder2="Minutos antes (ej: 10)",
#     reminder3="Minutos antes (ej: 0)",
# )
async def _setbearping_command_disabled(
    interaction: discord.Interaction,
    reminder1: int = 60,
    reminder2: int = 10,
    reminder3: int = 0,
):
    """Configurar recordatorios para eventos de oso (UTC)."""
    data = load_event_data()
    guild_data = ensure_guild_events(data, interaction.guild.id)
    reminders = sorted({reminder1, reminder2, reminder3}, reverse=False)
    guild_data["configs"]["bear"]["reminders"] = reminders
    save_event_data(data)
    await interaction.response.send_message(
        f"✅ Recordatorios de oso establecidos a {reminders} minutos antes.",
        ephemeral=True,
    )


# @bot.tree.command(name="cancelbear")
# @app_commands.describe(event_id="ID del evento de oso")
async def _cancelbear_command_disabled(
    interaction: discord.Interaction,
    event_id: int
):
    """Cancelar un evento de oso programado."""
    data = load_event_data()
    guild_data = ensure_guild_events(data, interaction.guild.id)
    target = None
    for ev in guild_data.get("events", []):
        if ev.get("type") == "bear" and ev.get("id") == event_id:
            target = ev
            break
    if not target:
        await interaction.response.send_message("❌ No se encontró ese evento de oso.", ephemeral=True)
        return
    await delete_event_message(interaction.guild, target)
    guild_data["events"] = [e for e in guild_data["events"] if e.get("id") != event_id]
    save_event_data(data)
    await interaction.response.send_message(f"🗑️ Evento de oso #{event_id} cancelado.", ephemeral=True)


# @bot.tree.command(name="listbears")
async def _listbears_command_disabled(interaction: discord.Interaction):
    """Listar eventos de oso programados."""
    data = load_event_data()
    guild_data = ensure_guild_events(data, interaction.guild.id)
    events = [e for e in guild_data.get("events", []) if e.get("type") == "bear"]
    events.sort(key=lambda e: e.get("start_time", ""))
    if not events:
        await interaction.response.send_message("🐻 No hay osos programados.", ephemeral=True)
        return
    embed = discord.Embed(title="🐻 Osos programados", color=discord.Color.green())
    for ev in events[:10]:
        start_dt = datetime.fromisoformat(ev["start_time"])
        ts = int(start_dt.timestamp())
        reminders = ev.get("reminder_offsets") or []
        embed.add_field(
            name=f"#{ev['id']} — <t:{ts}:F>",
            value=f"Pings: {reminders} • <t:{ts}:R>",
            inline=False,
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# @bot.tree.command(name="setarenaping")
# @app_commands.describe(
#     reminder1="Minutos antes (ej: 60)",
#     reminder2="Minutos antes (ej: 10)",
#     reminder3="Minutos antes (ej: 0)",
# )
async def _setarenaping_command_disabled(
    interaction: discord.Interaction,
    reminder1: int = 60,
    reminder2: int = 10,
    reminder3: int = 0,
):
    """Configurar recordatorios para la arena (siempre 00:00 UTC)."""
    data = load_event_data()
    guild_data = ensure_guild_events(data, interaction.guild.id)
    reminders = sorted({reminder1, reminder2, reminder3}, reverse=False)
    guild_data["configs"]["arena"]["reminders"] = reminders
    save_event_data(data)
    await interaction.response.send_message(
        f"✅ Recordatorios de arena establecidos a {reminders} minutos antes de las 00:00 UTC.",
        ephemeral=True,
    )


# @bot.tree.command(name="addevent")
# @app_commands.describe(
#     event_name="Nombre del evento",
#     date="Fecha en formato YYYY-MM-DD (UTC)",
#     time="Hora en formato HH:MM (UTC)"
# )
# @app_commands.choices(event_name=[app_commands.Choice(name=name, value=name) for name in EVENT_NAME_CHOICES])
async def _addevent_command_disabled(
    interaction: discord.Interaction,
    event_name: app_commands.Choice[str],
    date: str,
    time: str
):
    """Programar un evento general en UTC."""
    if not interaction.guild:
        await interaction.response.send_message("❌ Este comando debe usarse en un servidor.", ephemeral=True)
        return
    start_dt = parse_date_time_utc(date, time)
    if not start_dt:
        await interaction.response.send_message("❌ Formato inválido. Usa YYYY-MM-DD y HH:MM en UTC.", ephemeral=True)
        return
    now = datetime.now(pytz.UTC)
    if start_dt <= now:
        await interaction.response.send_message("❌ La fecha debe ser futura (UTC).", ephemeral=True)
        return
    channel = get_event_channel(interaction.guild, "event")
    if not channel:
        await interaction.response.send_message("❌ No se encontró el canal 🏆｜events.", ephemeral=True)
        return
    data = load_event_data()
    guild_data = ensure_guild_events(data, interaction.guild.id)
    event_id = next_event_id(guild_data)
    event = {
        "id": event_id,
        "type": "event",
        "name": event_name.value,
        "start_time": start_dt.isoformat(),
        "channel_id": channel.id,
        "message_id": None,
        "reminder_offsets": get_reminder_offsets(guild_data, "event"),
        "sent_offsets": [],
        "created_by": {"user_id": interaction.user.id, "username": str(interaction.user)},
        "created_at": now.isoformat(),
    }
    guild_data["events"].append(event)
    save_event_data(data)
    role = get_role_for_key(interaction.guild, "event")
    role_mention = role.mention if role else ""
    ts = int(start_dt.timestamp())
    embed = discord.Embed(
        title="🏆 Evento programado",
        description=f"{event_name.value}\nInicio: <t:{ts}:F> (<t:{ts}:R>)",
        color=discord.Color.gold(),
    )
    embed.set_footer(text="UTC • Discord mostrará tu hora local")
    sent = await channel.send(content=role_mention if role_mention else None, embed=embed)
    event["message_id"] = sent.id
    save_event_data(data)
    await interaction.response.send_message(
        f"✅ Evento #{event_id} programado para <t:{ts}:F> en {channel.mention}",
        ephemeral=True,
    )


# @bot.tree.command(name="cancelevent")
# @app_commands.describe(event_id="ID del evento")
async def _cancelevent_command_disabled(
    interaction: discord.Interaction,
    event_id: int
):
    """Cancelar un evento general programado."""
    data = load_event_data()
    guild_data = ensure_guild_events(data, interaction.guild.id)
    target = None
    for ev in guild_data.get("events", []):
        if ev.get("type") == "event" and ev.get("id") == event_id:
            target = ev
            break
    if not target:
        await interaction.response.send_message("❌ No se encontró ese evento.", ephemeral=True)
        return
    await delete_event_message(interaction.guild, target)
    guild_data["events"] = [e for e in guild_data["events"] if e.get("id") != event_id]
    save_event_data(data)
    await interaction.response.send_message(f"🗑️ Evento #{event_id} cancelado.", ephemeral=True)


# @bot.tree.command(name="listevent")
async def _listevent_command_disabled(interaction: discord.Interaction):
    """Listar eventos generales programados."""
    data = load_event_data()
    guild_data = ensure_guild_events(data, interaction.guild.id)
    events = [e for e in guild_data.get("events", []) if e.get("type") == "event"]
    events.sort(key=lambda e: e.get("start_time", ""))
    if not events:
        await interaction.response.send_message("🏆 No hay eventos programados.", ephemeral=True)
        return
    embed = discord.Embed(title="🏆 Eventos programados", color=discord.Color.gold())
    for ev in events[:10]:
        start_dt = datetime.fromisoformat(ev["start_time"])
        ts = int(start_dt.timestamp())
        reminders = ev.get("reminder_offsets") or []
        embed.add_field(
            name=f"#{ev['id']} — {ev['name']}",
            value=f"<t:{ts}:F> (<t:{ts}:R>) • Pings: {reminders}",
            inline=False,
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# @bot.tree.command(name="seteventpings")
# @app_commands.describe(
#     reminder1="Minutos antes (ej: 60)",
#     reminder2="Minutos antes (ej: 10)",
#     reminder3="Minutos antes (ej: 0)",
# )
async def _seteventpings_command_disabled(
    interaction: discord.Interaction,
    reminder1: int = 60,
    reminder2: int = 10,
    reminder3: int = 0,
):
    """Configurar recordatorios para eventos generales (UTC)."""
    data = load_event_data()
    guild_data = ensure_guild_events(data, interaction.guild.id)
    reminders = sorted({reminder1, reminder2, reminder3}, reverse=False)
    guild_data["configs"]["event"]["reminders"] = reminders
    save_event_data(data)
    await interaction.response.send_message(
        f"✅ Recordatorios de eventos establecidos a {reminders} minutos antes.",
        ephemeral=True,
    )


@bot.tree.command(name="add")
@app_commands.describe(
    mode="Choose: 'auto' (screenshot) or 'manual' (interactive)",
)
@app_commands.choices(mode=[
    app_commands.Choice(name="📷 Auto (screenshot)", value="auto"),
    app_commands.Choice(name="⌨️ Manual (interactive)", value="manual")
])
async def spy_command(
    interaction: discord.Interaction,
    mode: app_commands.Choice[str]
):
    """Add a player to the spy list for tracking (auto OCR or interactive manual)."""
    try:
        mode_value = mode.value
        print(f"[DEBUG /add] invoked by {interaction.user} mode={mode_value}")
        if mode_value == "auto":
            await _add_auto_mode(interaction)
        else:
            await _add_manual_mode_interactive(interaction)
    except Exception as e:
        print(f"[ERROR /add] {e}")
        try:
            await interaction.response.send_message("❌ Error interno en /add. Intenta de nuevo.", ephemeral=True)
        except discord.errors.InteractionResponded:
            await interaction.followup.send("❌ Error interno en /add. Intenta de nuevo.", ephemeral=True)


async def _add_auto_mode(interaction: discord.Interaction):
    """Auto mode: ask for screenshot, OCR name/id/alliance, then ask coords + reason."""
    from utils.ocr_profile import extract_player_profile
    
    await interaction.response.send_message(
        "📷 **Auto Mode - Screenshot Required**\n\n"
        "Please upload a clear screenshot of the player's profile.\n"
        "The screenshot should show:\n"
        "• Player name\n"
        "• Player ID\n"
        "• Alliance tag\n\n"
        "⏳ Waiting for screenshot..."
    )
    
    def check(m):
        return (m.author.id == interaction.user.id and
                m.channel and m.channel.id == interaction.channel.id and
                len(m.attachments) > 0 and
                m.attachments[0].content_type and
                m.attachments[0].content_type.startswith('image/'))
    
    try:
        msg = await bot.wait_for('message', check=check, timeout=60.0)
    except TimeoutError:
        await interaction.followup.send("⏰ Timeout - No screenshot received. Please try `/add` again.")
        return
    
    # Download and process screenshot
    attachment = msg.attachments[0]
    image_bytes = await attachment.read()
    
    await interaction.followup.send("🔍 Analyzing screenshot...")
    
    # Extract player data using OCR
    profile_data = extract_player_profile(image_bytes)
    
    if not profile_data.get('success'):
        await interaction.followup.send(
            f"❌ **OCR Failed**\n\n{profile_data.get('error')}\n\n"
            "Please try again with a clearer screenshot, or use manual mode: `/add mode:Manual`"
        )
        return
    
    # Extract data
    suggested_name = profile_data.get('name')
    id_player = profile_data.get('player_id')
    alliance = profile_data.get('alliance', 'N/A')

    # Always ask user to type the player name (OCR fails often)
    await interaction.followup.send(
        "👤 Escribe el nombre exacto del jugador (una línea).\n"
        f"(Sugerido OCR: `{suggested_name}`)"
    )
    try:
        name_msg = await bot.wait_for(
            'message',
            check=lambda m: m.author.id == interaction.user.id and m.channel.id == interaction.channel.id,
            timeout=60.0
        )
        name = name_msg.content.strip()
        if len(name) < 2:
            await interaction.followup.send("❌ Nombre inválido. Usa `/add` de nuevo y escribe el nombre completo.")
            return
    except TimeoutError:
        await interaction.followup.send("⏰ Tiempo agotado esperando el nombre. Usa `/add` de nuevo.")
        return

    # If ID was not read, ask the user
    if not id_player:
        await interaction.followup.send("🆔 No pude leer el ID. Escribe el ID numérico (7-12 dígitos).")
        try:
            id_msg = await bot.wait_for(
                'message',
                check=lambda m: m.author.id == interaction.user.id and m.channel.id == interaction.channel.id,
                timeout=60.0
            )
            id_player = re.sub(r'\D', '', id_msg.content)
            if len(id_player) < 7 or len(id_player) > 12:
                await interaction.followup.send("❌ ID inválido. Usa `/add` de nuevo y escribe el ID completo.")
                return
        except TimeoutError:
            await interaction.followup.send("⏰ Tiempo agotado esperando el ID. Usa `/add` de nuevo.")
            return
    
    # Validate alliance format
    if alliance != 'N/A':
        is_valid_alliance, alliance_normalized = validate_alliance(alliance)
        if not is_valid_alliance:
            alliance = alliance[:3].upper()  # Force to 3 letters
        else:
            alliance = alliance_normalized
    
    # Ask for coordinates and reason together
    await interaction.followup.send(
        "✅ **Data Extracted:**\n"
        f"• Name: {name}\n"
        f"• ID: {id_player}\n"
        f"• Alliance: {alliance}\n\n"
        "📍 **Coordinates & Reason Required**\n"
        "Responde en dos líneas:\n"
        "Línea 1: `X Y` (ej: 123 456)\n"
        "Línea 2: razón de seguimiento\n\n"
        "⏳ Esperando coords + razón..."
    )

    def coords_reason_check(m):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply_msg = await bot.wait_for('message', check=coords_reason_check, timeout=90.0)
        lines = [ln.strip() for ln in reply_msg.content.splitlines() if ln.strip()]
        if len(lines) < 2:
            await interaction.followup.send("❌ Formato inválido. Usa dos líneas: `X Y` y luego la razón.")
            return
        coord_parts = lines[0].split()
        if len(coord_parts) != 2:
            await interaction.followup.send("❌ Coordenadas inválidas. Usa: `123 456`.")
            return
        x = int(coord_parts[0])
        y = int(coord_parts[1])
        reason = "\n".join(lines[1:]).strip()
    except (TimeoutError, ValueError):
        await interaction.followup.send("⏰ Timeout o entrada inválida. Intenta `/add` de nuevo.")
        return

    # Validate coordinates (allow 0-9999)
    if not (0 <= x <= 9999 and 0 <= y <= 9999):
        await interaction.followup.send(
            "❌ **Invalid Coordinates**\n"
            "Coordinates must be between 0 and 9999"
        )
        return

    # Validate reason
    if not reason:
        await interaction.followup.send("❌ Razón requerida. Intenta `/add` de nuevo.")
        return

    # Create report
    await _create_spy_report(interaction, alliance, name, id_player, x, y, reason)


async def _add_manual_mode_interactive(interaction: discord.Interaction):
    """Manual mode: prompt sequentially for all fields."""
    await interaction.response.send_message(
        "⌨️ **Manual Mode - Entrada Guiada**\n\n"
        "Responderás con texto en el chat.\n"
        "El bot pedirá: alianza (3 letras), nombre, ID, coords y razón."
    )

    def user_msg_check(m):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        await interaction.followup.send("🏰 Escribe la alianza (3 letras, ej: ABC)")
        alliance_msg = await bot.wait_for('message', check=user_msg_check, timeout=60.0)
        alliance_input = alliance_msg.content.strip()
        is_valid_alliance, alliance = validate_alliance(alliance_input)
        if not is_valid_alliance:
            await interaction.followup.send("❌ Alianza inválida. Usa 3 letras (ej: ABC).")
            return

        await interaction.followup.send("👤 Escribe el nombre del jugador")
        name_msg = await bot.wait_for('message', check=user_msg_check, timeout=60.0)
        name = name_msg.content.strip()
        if not name:
            await interaction.followup.send("❌ Nombre inválido. Intenta de nuevo con `/add`.")
            return

        await interaction.followup.send("🆔 Escribe el ID del jugador")
        id_msg = await bot.wait_for('message', check=user_msg_check, timeout=60.0)
        id_player = id_msg.content.strip()
        if not id_player:
            await interaction.followup.send("❌ ID inválido. Intenta de nuevo con `/add`.")
            return

        await interaction.followup.send(
            "📍 Escribe las coordenadas en formato `X Y` (0-9999). Ej: 1234 5678"
        )
        coords_msg = await bot.wait_for('message', check=user_msg_check, timeout=60.0)
        coord_parts = coords_msg.content.strip().split()
        if len(coord_parts) != 2:
            await interaction.followup.send("❌ Formato de coordenadas inválido. Usa `123 456`.")
            return
        x = int(coord_parts[0])
        y = int(coord_parts[1])
        if not (0 <= x <= 9999 and 0 <= y <= 9999):
            await interaction.followup.send("❌ Coordenadas fuera de rango (0-9999).")
            return

        await interaction.followup.send("📝 Escribe la razón de seguimiento (una línea)")
        reason_msg = await bot.wait_for('message', check=user_msg_check, timeout=90.0)
        reason = reason_msg.content.strip()
        if not reason:
            await interaction.followup.send("❌ Razón requerida. Intenta de nuevo con `/add`.")
            return

    except TimeoutError:
        await interaction.followup.send("⏰ Tiempo agotado. Vuelve a usar `/add`.")
        return
    except ValueError:
        await interaction.followup.send("❌ Coordenadas inválidas. Intenta `/add` de nuevo.")
        return

    await _create_spy_report(interaction, alliance, name, id_player, x, y, reason)


async def _create_spy_report(interaction: discord.Interaction, alliance: str, name: str, 
                             id_player: str, x: int, y: int, reason: Optional[str]):
    """Create and save spy report (shared by auto and manual modes)."""
    
    # Format coordinates with 4 digits
    x_str = str(x).zfill(4)
    y_str = str(y).zfill(4)
    
    # Normalize reason
    safe_reason = (reason or "No reason provided").strip()
    if not safe_reason:
        safe_reason = "No reason provided"

    # Load existing data
    data = load_spy_data()
    
    # Create new report
    report = {
        "id": len(data["reports"]) + 1,
        "alliance": alliance,
        "name": name,
        "player_id": id_player.strip(),
        "coordinates": {
            "x": x_str,
            "y": y_str
        },
        "reason": safe_reason,
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
    translated_reason = translate_reason(safe_reason, lang)
    
    # Create response embed
    embed = discord.Embed(
        title=translate('spy_added_title', lang),
        description=translate('player_added_desc', lang).format(name=name),
        color=discord.Color.green()
    )
    
    embed.add_field(name=f"🏰 {translate('alliance', lang)}", value=alliance, inline=True)
    embed.add_field(name=f"📍 {translate('coordinates', lang)}", value=f"x:{x_str} y:{y_str}", inline=True)
    embed.add_field(name="🆔 Report ID", value=f"#{report['id']}", inline=True)
    embed.add_field(name="👤 Player ID", value=id_player.strip(), inline=True)
    embed.add_field(name=f"📝 {translate('reason', lang)}", value=translated_reason, inline=False)
    embed.add_field(name=f"👤 {translate('added_by', lang)}", value=str(interaction.user), inline=True)
    embed.add_field(name=f"⏰ {translate('time', lang)}", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
    
    embed.set_footer(text=translate('bot_by', lang))
    
    # Send response (use followup if interaction already responded)
    try:
        await interaction.response.send_message(embed=embed)
    except discord.errors.InteractionResponded:
        await interaction.followup.send(embed=embed)


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


@bot.tree.command(name="ranking")
async def ranking_command(
    interaction: discord.Interaction,
):
    """Top-100 ranking: sube un archivo Excel/CSV con los datos del ranking. Agrupa por alianza y muestra resumen."""

    # Verificar permisos: solo owner del bot, owner del servidor, o admins
    is_owner = interaction.user.id == OWNER_ID
    is_guild_owner = interaction.guild and interaction.user.id == interaction.guild.owner_id
    is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
    
    if not (is_owner or is_guild_owner or is_admin):
        await interaction.response.send_message(
            "❌ This command is restricted to: bot owner, server owner, or administrators.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "📊 **Ranking: Sube un archivo Excel o CSV**\n\n"
        "**Formatos aceptados:** .xlsx, .xls, .csv\n"
        "**Columnas necesarias:**\n"
        "• Rank (o Ranking, Position)\n"
        "• Alliance (o Tag, Clan)\n"
        "• Name (opcional)\n"
        "• Score (opcional)\n\n"
        "Ejemplo CSV:\n"
        "```\nRank,Alliance,Name,Score\n1,HOF,Player1,850\n2,HSU,Player2,845```\n"
        "⏳ Esperando archivo (límite 2 minutos)..."
    )

    def file_check(m: discord.Message):
        return (
            m.author.id == interaction.user.id and
            m.channel and m.channel.id == interaction.channel.id and
            len(m.attachments) > 0
        )

    # Esperar archivo
    try:
        msg = await bot.wait_for('message', check=file_check, timeout=120.0)
        
        file_found = None
        for att in msg.attachments:
            filename = att.filename.lower()
            if filename.endswith(('.csv', '.xlsx', '.xls')):
                file_found = att
                break
        
        if not file_found:
            await interaction.followup.send("❌ No se encontró ningún archivo Excel/CSV. Intenta de nuevo con `/ranking`.")
            return
        
        await interaction.followup.send(f"📥 Recibido: `{file_found.filename}` ({file_found.size} bytes)\n🔍 Procesando...")
        
        # Descargar y parsear archivo
        file_bytes = await file_found.read()
        all_entries = parse_ranking_file(file_bytes, file_found.filename)
        
        if len(all_entries) == 0:
            await interaction.followup.send(
                "❌ No se pudieron extraer datos del archivo.\n\n"
                "**Verifica que:**\n"
                "• El archivo tenga columnas: Rank, Alliance (y opcionalmente Name, Score)\n"
                "• Los datos estén en la primera hoja (Excel)\n"
                "• No haya filas vacías al inicio"
            )
            return
        
        await interaction.followup.send(f"✅ Extraídas **{len(all_entries)}** entradas del archivo")
        
    except TimeoutError:
        await interaction.followup.send("⏱️ Tiempo agotado. No se recibió ningún archivo.")
        return
    except Exception as e:
        await interaction.followup.send(f"❌ Error procesando archivo: {e}")
        return

    # Procesar datos
    final_list = all_entries  # Ya vienen ordenados por rank

    # Alliance grouping
    alliance_counts: dict[str, list[dict]] = {}
    for e in final_list:
        tag = e.get('alliance') or 'UNKNOWN'
        alliance_counts.setdefault(tag, []).append(e)

    top_alliances = sorted(alliance_counts.items(), key=lambda kv: len(kv[1]), reverse=True)[:10]

    # Summary embed
    summary = discord.Embed(
        title="🏆 Top-100 Ranking",
        description=f"Entradas procesadas: **{len(final_list)}** / 100",
        color=discord.Color.gold()
    )
    
    if final_list:
        top10_lines = []
        for e in final_list[:10]:
            score_str = f" — {e['score']}" if e.get('score') else ""
            top10_lines.append(f"#{e['rank']} [{e.get('alliance','?')}] {e['name']}{score_str}")
        summary.add_field(name="🥇 Top 10", value="\n".join(top10_lines), inline=False)
    
    if top_alliances:
        alliance_lines = []
        for tag, members in top_alliances:
            ranks = ", ".join([f"#{m['rank']}" for m in sorted(members, key=lambda x: x['rank'])[:5]])
            count_str = f"{len(members)} {'jugador' if len(members) == 1 else 'jugadores'}"
            alliance_lines.append(f"**[{tag}]** — {count_str} ({ranks}{'...' if len(members) > 5 else ''})")
        summary.add_field(name="🛡️ Alianzas destacadas", value="\n".join(alliance_lines), inline=False)
    
    summary.set_footer(text=f"Archivo: {file_found.filename}")
    await interaction.followup.send(embed=summary)
    
    # Guardar datos del ranking para el comando /tops
    ranking_data = {
        'timestamp': datetime.now(pytz.UTC).isoformat(),
        'filename': file_found.filename,
        'entries': final_list,
        'alliances': {tag: [m for m in members] for tag, members in alliance_counts.items()}
    }
    ranking_file = Path('data/ranking_latest.json')
    ranking_file.parent.mkdir(exist_ok=True)
    with open(ranking_file, 'w', encoding='utf-8') as f:
        json.dump(ranking_data, f, indent=2, ensure_ascii=False)
    print(f"[Ranking] Datos guardados en {ranking_file}")

    # Detail pages: 9 per embed
    rank_map = {e['rank']: e for e in final_list}
    
    def page_embed(start_rank: int) -> discord.Embed:
        end_rank = min(start_rank + 8, 100)
        emb = discord.Embed(
            title=f"📋 Rangos {start_rank}–{end_rank}",
            color=discord.Color.blue()
        )
        lines = []
        for r in range(start_rank, end_rank+1):
            e = rank_map.get(r)
            if not e:
                lines.append(f"#{r} — (sin datos)")
            else:
                score_part = f" — {e['score']}" if e.get('score') is not None else ""
                lines.append(f"#{r} **[{e.get('alliance','?')}]** {e['name']}{score_part}")
        emb.description = "\n".join(lines)
        return emb

    for start in range(1, 101, 9):
        await interaction.followup.send(embed=page_embed(start))


@bot.tree.command(name="tops")
async def tops_command(
    interaction: discord.Interaction,
):
    """Shows a summary of all alliances with their best players from the latest processed ranking."""
    
    # Cargar datos del último ranking
    ranking_file = Path('data/ranking_latest.json')
    if not ranking_file.exists():
        await interaction.response.send_message(
            "❌ No ranking data available.\n"
            "First run `/ranking` to process a file.",
            ephemeral=True
        )
        return
    
    try:
        with open(ranking_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        alliances = data.get('alliances', {})
        timestamp = data.get('timestamp', 'Unknown')
        
        if not alliances:
            await interaction.response.send_message("❌ No alliance data available.", ephemeral=True)
            return
        
        # Ordenar alianzas por: 1) número de jugadores, 2) mejor rank
        alliance_list = []
        for tag, members in alliances.items():
            best_rank = min(m['rank'] for m in members)
            alliance_list.append({
                'tag': tag,
                'members': members,
                'count': len(members),
                'best_rank': best_rank
            })
        
        alliance_list.sort(key=lambda a: (-a['count'], a['best_rank']))
        
        # Crear embeds (máximo 25 alianzas por embed debido a límite de Discord)
        await interaction.response.defer()
        
        # Main embed
        main_embed = discord.Embed(
            title="🏆 TOPS - Alliances in Ranking",
            description=f"Summary of alliances present in Top-100\n*Updated: <t:{int(datetime.fromisoformat(timestamp).timestamp())}:R>*",
            color=discord.Color.gold()
        )
        
        # Añadir top 24 alianzas al embed principal (en columnas, 3 por fila)
        for alliance in alliance_list[:24]:
            tag = alliance['tag']
            members = sorted(alliance['members'], key=lambda m: m['rank'])
            
            # Todos los jugadores de la alianza
            all_players = "\n".join([f"#{m['rank']} {m['name']}" for m in members])
            
            # If value exceeds 1024 characters (Discord limit), truncate
            if len(all_players) > 900:  # Safety margin for header
                truncated = "\n".join([f"#{m['rank']} {m['name']}" for m in members[:20]])
                all_players = f"{truncated}\n*...and {len(members)-20} more*"
            
            field_value = f"**{alliance['count']} {'player' if alliance['count'] == 1 else 'players'}**\n{all_players}"
            
            main_embed.add_field(
                name=f"🛡️ [{tag}]",
                value=field_value,
                inline=True  # Display in columns
            )
        
        main_embed.set_footer(text=f"Showing {min(24, len(alliance_list))} of {len(alliance_list)} alliances")
        
        await interaction.followup.send(embed=main_embed)
        
        # If there are more than 24 alliances, create additional embeds
        if len(alliance_list) > 24:
            for i in range(24, len(alliance_list), 24):
                batch = alliance_list[i:i+24]
                extra_embed = discord.Embed(
                    title=f"🏆 TOPS - Alliances (page {i//24 + 1})",
                    color=discord.Color.blue()
                )
                
                for alliance in batch:
                    tag = alliance['tag']
                    members = sorted(alliance['members'], key=lambda m: m['rank'])
                    
                    # Todos los jugadores de la alianza
                    all_players = "\n".join([f"#{m['rank']} {m['name']}" for m in members])
                    
                    # If value exceeds 1024 characters (Discord limit), truncate
                    if len(all_players) > 900:
                        truncated = "\n".join([f"#{m['rank']} {m['name']}" for m in members[:20]])
                        all_players = f"{truncated}\n*...and {len(members)-20} more*"
                    
                    field_value = f"**{alliance['count']} {'player' if alliance['count'] == 1 else 'players'}**\n{all_players}"
                    
                    extra_embed.add_field(
                        name=f"🛡️ [{tag}]",
                        value=field_value,
                        inline=True  # Display in columns
                    )
                
                await interaction.followup.send(embed=extra_embed)
        
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error loading ranking data: {e}",
            ephemeral=True
        )
        import traceback
        traceback.print_exc()


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
            f"**Player ID:** {report.get('player_id', 'N/A')}\n"
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


@bot.tree.command(name="edit")
@app_commands.describe(
    report_id="Report ID to edit (from /list)",
    alliance="New alliance tag (3 letters, optional)",
    name="New player name (optional)",
    id_player="New player ID (optional)",
    x="New X coordinate (0-9999, optional)",
    y="New Y coordinate (0-9999, optional)",
    reason="New reason (optional)"
)
async def edit_command(
    interaction: discord.Interaction,
    report_id: int,
    alliance: str = None,
    name: str = None,
    id_player: str = None,
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
    
    # Update player ID if provided
    if id_player is not None:
        id_player = id_player.strip()
        old_values['player_id'] = report.get('player_id', 'N/A')
        report['player_id'] = id_player
        changes.append(f"Player ID: `{old_values['player_id']}` → `{id_player}`")
    
    # Update coordinates if provided
    if x is not None or y is not None:
        # If only one coordinate is provided, keep the other one
        new_x = x if x is not None else int(report['coordinates']['x'])
        new_y = y if y is not None else int(report['coordinates']['y'])
        
        # Validate coordinates
        if not (0 <= new_x <= 9999 and 0 <= new_y <= 9999):
            await interaction.response.send_message(
                "❌ **Invalid Coordinates**\n"
                "Coordinates must be between 0 and 9999",
                ephemeral=True
            )
            return
        
        old_coords = report['coordinates']
        old_values['coordinates'] = f"x:{old_coords['x']} y:{old_coords['y']}"
        
        # Format coordinates with 4 digits
        x_str = str(new_x).zfill(4)
        y_str = str(new_y).zfill(4)
        
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
    from cogs.translations import get_text
    
    lang = get_user_language_saved(interaction.user.id)
    print(f"DEBUG /help: User {interaction.user.id} has language: {lang}")
    
    embed = discord.Embed(
        title=get_text('spy_help_title', lang),
        description=get_text('spy_help_desc', lang),
        color=discord.Color.blue()
    )
    
    # Setup commands
    embed.add_field(
        name=get_text('spy_setup_title', lang),
        value=(
            get_text('spy_timezone_cmd', lang) + "\n\n"
            + get_text('spy_language_cmd', lang) + "\n\n"
            + get_text('spy_notifications_cmd', lang)
        ),
        inline=False
    )
    
    # Tracking commands
    embed.add_field(
        name=get_text('spy_tracking_title', lang),
        value=(
            get_text('spy_add_cmd', lang) + "\n\n"
            + get_text('spy_list_cmd', lang) + "\n\n"
            + get_text('spy_search_cmd', lang) + "\n\n"
            + get_text('spy_edit_cmd', lang) + "\n\n"
            + get_text('spy_remove_cmd', lang)
        ),
        inline=False
    )
    
    # Shield commands
    embed.add_field(
        name=get_text('spy_shield_title', lang),
        value=(
            get_text('spy_shield_cmd', lang) + "\n\n"
            + get_text('spy_shields_cmd', lang) + "\n\n"
            + get_text('spy_removeshield_cmd', lang) + "\n\n"
            + get_text('spy_listplayers_cmd', lang)
        ),
        inline=False
    )
    
    # Ranking and analysis commands
    embed.add_field(
        name=get_text('spy_ranking_title', lang),
        value=(
            get_text('spy_ranking_cmd', lang) + "\n\n"
            + get_text('spy_tops_cmd', lang) + "\n\n"
            + get_text('spy_bear_cmd', lang)
        ),
        inline=False
    )
    
    # Info commands
    embed.add_field(
        name=get_text('spy_info_title', lang),
        value=(
            get_text('spy_stats_cmd', lang) + "\n\n"
            + get_text('spy_help_cmd', lang)
        ),
        inline=False
    )
    
    # Quick start guide
    embed.add_field(
        name=get_text('spy_quick_start', lang),
        value=(
            get_text('spy_quick_steps', lang) + "\n\n"
            + get_text('spy_quick_tip', lang)
        ),
        inline=False
    )
    
    embed.set_footer(text=get_text('spy_help_footer', lang))
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="stats")
async def stats_command(interaction: discord.Interaction):
    """Show spy bot statistics."""
    
    data = load_spy_data()
    shield_data = load_shield_data()
    reports = data["reports"]
    
    if len(reports) == 0:
        await interaction.response.send_message(
            "📊 **No Data Yet**\n"
            "Use `/spy` to start tracking players.",
            ephemeral=True
        )
        return
    
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
              f"**Active Shields:** {active_shields}",
        inline=False
    )
    
    if top_alliances:
        alliance_list = "\n".join([f"**{alliance}**: {count} player(s)" for alliance, count in top_alliances])
        embed.add_field(
            name="🏆 Top Tracked Alliances",
            value=alliance_list,
            inline=False
        )
    
    embed.set_footer(text="Bot by KnyCat")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


def calculate_bear_composition(archers: int, marches_available: int, is_rally_leader: bool, march_capacity: int) -> dict:
    """
    Calculate bear hunting troop composition per march.
    
    Logic:
    1. Total marches = marches_available + (1 if rally leader else 0)
    2. Archers per march = total archers / total marches
    3. Infantry + Cavalry = march_capacity - archers per march
    4. Infantry and Cavalry split equally
    
    Args:
        archers: Total archer troops available
        marches_available: How many marches you can send simultaneously
        is_rally_leader: Whether user is rally leader (adds +1 march)
        march_capacity: Total march capacity in troops (90000)
    
    Returns:
        dict with infantry, cavalry, archers counts and percentages
    """
    try:
        # If rally leader, add +1 to total marches
        total_marches = marches_available + (1 if is_rally_leader else 0)
        
        # Calculate archers per march
        archers_per_march = int(archers / total_marches)
        
        # Maximum archers allowed (80% of march capacity)
        max_archers = int(march_capacity * 0.80)
        
        # Check if calculated archers exceed the 80% limit
        exceeds_limit = archers_per_march > max_archers
        
        if exceeds_limit:
            # Use standard composition: 10% infantry, 10% cavalry, 80% archers
            infantry_to_send = int(march_capacity * 0.10)
            cavalry_to_send = int(march_capacity * 0.10)
            archers_per_march = max_archers
        else:
            # Use calculated composition based on available archers
            # Limit archers per march to march capacity
            if archers_per_march > march_capacity:
                archers_per_march = march_capacity
            
            # Calculate remaining troops for infantry and cavalry
            remaining_troops = march_capacity - archers_per_march
            
            # Split remaining troops equally between infantry and cavalry
            infantry_to_send = int(remaining_troops / 2)
            cavalry_to_send = remaining_troops - infantry_to_send  # Ensures we use all remaining troops
        
        total_troops = infantry_to_send + cavalry_to_send + archers_per_march
        
        # Calculate percentages
        if total_troops > 0:
            infantry_pct = round((infantry_to_send / total_troops) * 100)
            cavalry_pct = round((cavalry_to_send / total_troops) * 100)
            archers_pct = round((archers_per_march / total_troops) * 100)
        else:
            infantry_pct = cavalry_pct = archers_pct = 0
        
        # Adjust for rounding errors to ensure percentages sum to 100
        total_pct = infantry_pct + cavalry_pct + archers_pct
        if total_pct != 100:
            diff = 100 - total_pct
            archers_pct += diff
        
        # Calculate total archers needed for all marches
        total_archers_needed = archers_per_march * total_marches
        has_excess_archers = archers > total_archers_needed
        
        return {
            "infantry": infantry_to_send,
            "cavalry": cavalry_to_send,
            "archers": archers_per_march,
            "infantry_pct": infantry_pct,
            "cavalry_pct": cavalry_pct,
            "archers_pct": archers_pct,
            "total_troops": total_troops,
            "total_marches": total_marches,
            "has_excess_archers": has_excess_archers,
            "exceeds_limit": exceeds_limit,
            "total_archers_needed": total_archers_needed
        }
    except Exception as e:
        print(f"Error calculating bear composition: {e}")
        return None


def validate_bear_input(user_input: str, input_type: str) -> Optional[int | bool]:
    """
    Validate user input for bear command.
    
    Args:
        user_input: Raw user input string
        input_type: 'archers', 'marches', 'capacity', or 'rally'
    
    Returns:
        int for archers/capacity, bool for rally, None if invalid
    """
    user_input = user_input.strip().lower()
    
    if input_type == 'rally':
        if user_input in ['yes', 'y', 'si', 's']:
            return True
        elif user_input in ['no', 'n']:
            return False
        else:
            return None
    
    else:  # numeric inputs: archers, marches, capacity
        try:
            value = int(user_input)
            if value < 0:
                return None
            if input_type == 'marches':
                if value == 0:
                    return None
                if value > 6:  # Maximum marches allowed in game
                    return None
            return value
        except ValueError:
            return None


@bot.tree.command(name="bear")
async def bear_command(interaction: discord.Interaction):
    """Calculate optimal troop composition for bear hunting event."""
    from cogs.translations import get_text
    
    lang = get_user_language_saved(interaction.user.id)
    
    # Send warning/instructions embed
    warning_embed = discord.Embed(
        title=get_text('bear_warning_title', lang),
        description=get_text('bear_warning_desc', lang),
        color=discord.Color.gold()
    )
    
    warning_embed.add_field(
        name=get_text('bear_time_limit', lang),
        value=get_text('bear_time_limit_text', lang),
        inline=False
    )
    
    warning_embed.add_field(
        name=get_text('bear_data_needed', lang),
        value=(
            get_text('bear_data_archers', lang) + "\n\n"
            + get_text('bear_data_marches', lang) + "\n\n"
            + get_text('bear_data_rally', lang)
        ),
        inline=False
    )
    
    warning_embed.add_field(
        name="💡 " + get_text('bear_tip', lang),
        value=get_text('bear_tip', lang),
        inline=False
    )
    
    warning_embed.set_footer(text="Type or paste your answers in the chat • Bot by KnyCat")
    
    await interaction.response.send_message(embed=warning_embed)
    
    # Helper function to check if message is from the user
    def user_check(m):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
    
    try:
        # ===== Question 1: Total Archers =====
        await interaction.followup.send(
            get_text('bear_q1_title', lang) + "\n"
            + get_text('bear_q1_text', lang)
        )
        
        archers = None
        while archers is None:
            try:
                msg1 = await bot.wait_for('message', check=user_check, timeout=60.0)
                archers = validate_bear_input(msg1.content, 'archers')
                if archers is None:
                    await interaction.followup.send(
                        get_text('bear_invalid_input', lang) + "\n"
                        + get_text('bear_invalid_example', lang)
                    )
            except asyncio.TimeoutError:
                await interaction.followup.send(get_text('bear_timeout', lang))
                return
        
        # ===== Question 2: Marches Available =====
        await interaction.followup.send(
            get_text('bear_q2_title', lang) + "\n"
            + get_text('bear_q2_text', lang)
        )
        
        marches_available = None
        while marches_available is None:
            try:
                msg2 = await bot.wait_for('message', check=user_check, timeout=60.0)
                marches_available = validate_bear_input(msg2.content, 'marches')
                if marches_available is None:
                    # Check if user entered a number > 6
                    try:
                        value = int(msg2.content.strip())
                        if value > 6:
                            await interaction.followup.send(
                                "❌ **Maximum marches exceeded!**\n"
                                "The maximum number of marches allowed in the game is **6**.\n"
                                "Please enter a number between 1 and 6."
                            )
                        else:
                            await interaction.followup.send(
                                get_text('bear_invalid_input', lang) + "\n"
                                + get_text('bear_invalid_example', lang)
                            )
                    except ValueError:
                        await interaction.followup.send(
                            get_text('bear_invalid_input', lang) + "\n"
                            + get_text('bear_invalid_example', lang)
                        )
            except asyncio.TimeoutError:
                await interaction.followup.send(get_text('bear_timeout', lang))
                return
        
        # ===== Question 3: Rally Leader Status =====
        await interaction.followup.send(
            get_text('bear_q3_title', lang) + "\n"
            + get_text('bear_q3_text', lang)
        )
        
        is_rally_leader = None
        while is_rally_leader is None:
            try:
                msg3 = await bot.wait_for('message', check=user_check, timeout=60.0)
                is_rally_leader = validate_bear_input(msg3.content, 'rally')
                if is_rally_leader is None:
                    await interaction.followup.send(get_text('bear_invalid_rally', lang))
            except asyncio.TimeoutError:
                await interaction.followup.send(get_text('bear_timeout', lang))
                return
        
        # ===== Use Fixed March Capacity =====
        march_capacity = 90000
        
        # ===== Calculate Results =====
        result = calculate_bear_composition(archers, marches_available, is_rally_leader, march_capacity)
        
        if result is None:
            await interaction.followup.send(get_text('bear_error', lang))
            return
        
        # ===== Display Results =====
        
        # Check if composition exceeds 80% archer limit
        if result.get('exceeds_limit'):
            max_archers_limit = int(march_capacity * 0.80)
            limit_msg = (
                f"⚠️ **Archer limit exceeded!**\n"
                f"With {archers:,} archers and {result['total_marches']} marches, you would have {int(archers / result['total_marches']):,} archers per march.\n"
                f"This exceeds the recommended maximum of {max_archers_limit:,} archers per march (80% limit).\n\n"
                f"**Using standard composition:** 10% Infantry, 10% Cavalry, 80% Archers\n"
                f"This ensures minimum infantry and cavalry for balanced effectiveness.\n"
            )
            await interaction.followup.send(limit_msg)
        
        result_embed = discord.Embed(
            title=get_text('bear_results_title', lang),
            description=get_text('bear_results_desc', lang),
            color=discord.Color.gold()
        )
        
        result_embed.add_field(
            name=get_text('bear_infantry_label', lang),
            value=f"{result['infantry']:,} troops",
            inline=True
        )
        
        result_embed.add_field(
            name=get_text('bear_cavalry_label', lang),
            value=f"{result['cavalry']:,} troops",
            inline=True
        )
        
        result_embed.add_field(
            name=get_text('bear_archers_label', lang),
            value=f"{result['archers']:,} troops",
            inline=True
        )
        
        result_embed.add_field(
            name=get_text('bear_composition_label', lang),
            value=f"**{result['infantry_pct']}%** Infantry\n"
                f"**{result['cavalry_pct']}%** Cavalry\n"
                f"**{result['archers_pct']}%** Archers",
            inline=False
        )
        
        result_embed.add_field(
            name=get_text('bear_total_label', lang),
            value=f"{result['total_troops']:,} troops",
            inline=False
        )
        
        result_embed.add_field(
            name=get_text('bear_summary_label', lang),
            value=f"{get_text('bear_rally_leader', lang)}: {get_text('bear_yes', lang) if is_rally_leader else get_text('bear_no', lang)}\n"
                  f"{get_text('bear_available_archers', lang)}: {archers:,}\n"
                  f"{get_text('bear_available_marches', lang)}: {marches_available:,}{' (+1 rally)' if is_rally_leader else ''}\n"
                  f"Total marches: {result['total_marches']}\n"
                  f"{get_text('bear_march_capacity', lang)}: {march_capacity:,} (fixed)",
            inline=False
        )
        
        result_embed.set_footer(text=get_text('bear_footer', lang))
        
        await interaction.followup.send(embed=result_embed)
        
    except Exception as e:
        print(f"Error in bear command: {e}")
        await interaction.followup.send(
            f"❌ {get_text('bear_error', lang)}\n"
            "Please try again or contact the bot owner."
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
