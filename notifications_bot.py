"""Kingshot Notifications Bot - Event scheduling and role management."""

import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
import json
import re
import zipfile
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
import pytz
import asyncio
from typing import Optional
import xml.etree.ElementTree as ET

print("=" * 60)
print("🚀 KINGSHOT NOTIFICATIONS BOT STARTING...")
print("=" * 60)

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('NOTIFICATIONS_BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', 0))

if not DISCORD_TOKEN:
    print("ERROR: NOTIFICATIONS_BOT_TOKEN not found in .env file")
    exit(1)

print(f"?� Token loaded (length: {len(DISCORD_TOKEN)}, starts with: {DISCORD_TOKEN[:20]}...)")
print(f"?� Owner ID: {OWNER_ID}")

# Initialize bot with required intents
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Data files
DATA_DIR = Path("data/notifications")
DATA_DIR.mkdir(parents=True, exist_ok=True)
EVENTS_FILE = DATA_DIR / "events.json"
CONFIG_FILE = DATA_DIR / "guild_config.json"
ETERNITY_IMAGE_PATH = Path("assets/eternity_reach.png")
ETERNITY_IMAGE_URL = "https://static.wikia.nocookie.net/kingshot/images/d/d8/Skills.webp"

# Constants
HEADER_VERSION = 2
REACTION_MESSAGE_VERSION = 1

DEFAULT_CHANNEL_NAMES = {
    "bear": "bear",
    "bear_log": "bear-log",
    "arena": "arena",
    "events": "events",
    "reaction": "notification-settings",
}

NOTIFICATION_MENTION = ""

REACTION_ROLE_NAMES = {
    "bear1": "Bear Trap 1",
    "bear2": "Bear Trap 2",
    "arena": "Arena",
    "event": "Event",
}

REACTION_EMOJIS = {
    "bear1": "🐻",
    "bear2": "🐼",
    "arena": "⚔️",
    "event": "🏆",
}

SIMPLE_EVENT_TYPES = [
    "Castle Battle",
    "Fortress Battle",
    "Sanctuary Battle",
    "Outpost Battle",
    "Viking Vengeance",
    "Cesares Fury Boss",
    "KVK PVP Zone",
]

LEGION_EVENT_TYPES = [
    "Swordland Showdown (Legion 1 / Legion 2)",
    "Tri Alliance Clash (Legion 1 / Legion 2)",
]

EVENT_TYPES = SIMPLE_EVENT_TYPES + LEGION_EVENT_TYPES

# Avoid re-posting the daily arena embed if persistence is temporarily unavailable.
ARENA_SCHEDULE_CACHE: dict[int, datetime] = {}


# ============================================================================
# DATA MANAGEMENT
# ============================================================================

def normalize_guild_event_ids(guild_data: dict) -> bool:
    """Ensure every event has a unique positive integer ID."""
    events = guild_data.setdefault("events", [])
    used_ids: set[int] = set()
    max_existing_id = 0
    changed = False

    for event in events:
        event_id = event.get("id")
        if isinstance(event_id, int) and event_id > 0 and event_id not in used_ids:
            used_ids.add(event_id)
            if event_id > max_existing_id:
                max_existing_id = event_id
            continue

        event["id"] = None
        changed = True

    next_id = max_existing_id + 1 if max_existing_id > 0 else 1
    for event in events:
        if event.get("id") is None:
            while next_id in used_ids:
                next_id += 1
            event["id"] = next_id
            used_ids.add(next_id)
            next_id += 1

    return changed

def load_events():
    """Load all events data."""
    if EVENTS_FILE.exists():
        try:
            with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "guilds" not in data:
                    data = {"guilds": {}}
                changed = False
                for guild_data in data.get("guilds", {}).values():
                    if normalize_guild_event_ids(guild_data):
                        changed = True
                if changed:
                    save_events(data)
                return data
        except Exception as e:
            print(f"Error loading events: {e}")
    return {"guilds": {}}


def save_events(data):
    """Save events data."""
    try:
        with open(EVENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving events: {e}")


def load_config():
    """Load guild configurations."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
    return {}


def save_config(data):
    """Save guild configurations."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")


def ensure_guild_data(data, guild_id: int) -> dict:
    """Ensure guild data structure exists."""
    gid = str(guild_id)
    if gid not in data["guilds"]:
        data["guilds"][gid] = {
            "events": [],
            "configs": {
                "bear1": {"reminders": [60, 10]},
                "bear2": {"reminders": [60, 10]},
                "arena": {"reminders": [60, 10]},
                "event": {"reminders": [60, 10, 0]},
            },
            "headers": {},
        }
    configs = data["guilds"][gid].setdefault("configs", {})
    configs.setdefault("bear1", {"reminders": [60, 10]})
    configs.setdefault("bear2", {"reminders": [60, 10]})
    configs.setdefault("arena", {"reminders": [60, 10]})
    configs.setdefault("event", {"reminders": [60, 10, 0]})
    normalize_guild_event_ids(data["guilds"][gid])
    return data["guilds"][gid]


def ensure_guild_config(config, guild_id: int) -> dict:
    """Ensure guild config exists."""
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {
            "installed": False,
            "category_id": None,
            "channels": {},
            "admin_role_id": None,
            "reaction_roles": {
                "enabled": True,
                "channel_id": None,
                "message_id": None,
                "version": 0,
                "roles": {
                    "bear1": None,
                    "bear2": None,
                    "arena": None,
                    "event": None,
                },
            },
        }
    else:
        config[gid].setdefault("admin_role_id", None)
    channels = config[gid].setdefault("channels", {})
    channels.setdefault("reaction", None)
    ensure_reaction_roles_config(config[gid])
    return config[gid]


def ensure_reaction_roles_config(guild_config: dict) -> dict:
    """Ensure reaction-role config shape exists for a guild."""
    reaction_cfg = guild_config.setdefault("reaction_roles", {})
    reaction_cfg.setdefault("enabled", True)
    reaction_cfg.setdefault("channel_id", guild_config.get("channels", {}).get("reaction"))
    reaction_cfg.setdefault("message_id", None)
    reaction_cfg.setdefault("version", 0)
    roles = reaction_cfg.setdefault("roles", {})
    for role_key in REACTION_ROLE_NAMES:
        roles.setdefault(role_key, None)
    return reaction_cfg


def next_event_id(guild_data: dict) -> int:
    """Get next event ID."""
    if not guild_data.get("events"):
        return 1
    return max(ev.get("id", 0) for ev in guild_data["events"]) + 1


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_time(time_str: str) -> Optional[tuple[int, int]]:
    """Parse time string HH:MM."""
    import re
    time_str = time_str.strip()
    pattern = r'^(\d{1,2}):(\d{2})$'
    match = re.match(pattern, time_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            return hours, minutes
    return None


def parse_date_time_utc(date_str: str, time_str: str) -> Optional[datetime]:
    """Parse date YYYY-MM-DD and time HH:MM to UTC datetime."""
    try:
        parts = date_str.split("-")
        if len(parts) != 3:
            return None
        y, m, d = [int(x) for x in parts]
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


R4_ROLE_ID = 1488153346895515789

def has_command_permission(member: discord.Member) -> bool:
    """Check if member can use management commands in this guild."""
    if member.guild_permissions.administrator:
        return True

    config = load_config()
    guild_config = ensure_guild_config(config, member.guild.id)
    admin_role_id = guild_config.get("admin_role_id")
    if admin_role_id:
        try:
            admin_role_id = int(admin_role_id)
        except (TypeError, ValueError):
            admin_role_id = None

    if admin_role_id and any(role.id == admin_role_id for role in member.roles):
        return True

    # Backward compatibility fallback for guilds that still rely on the legacy role.
    return any(role.id == R4_ROLE_ID for role in member.roles)


def get_notification_role(guild: discord.Guild) -> Optional[discord.Role]:
    """Legacy compatibility helper (role mentions are no longer used)."""
    return None


def normalize_event_type_for_roles(event_type: str, event_name: str = "") -> str:
    """Normalize event types so role mention routing is consistent."""
    if event_type in {"bear1", "bear2", "arena", "event"}:
        return event_type
    if event_type == "bear":
        lowered = (event_name or "").lower()
        return "bear2" if "2" in lowered else "bear1"
    return "event"


def get_notification_mention(guild: discord.Guild, event_type: str = "event", event_name: str = "") -> str:
    """Return role mention for a specific notification type, with safe fallback."""
    normalized_type = normalize_event_type_for_roles(event_type, event_name)
    role = get_role_for_type(guild, normalized_type)
    if role:
        return role.mention
    return NOTIFICATION_MENTION


def get_channel(guild: discord.Guild, guild_config: dict, channel_type: str) -> Optional[discord.TextChannel]:
    """Get configured channel by type."""
    channel_id = guild_config.get("channels", {}).get(channel_type)
    if channel_id:
        return guild.get_channel(channel_id)
    return None


def find_channel_by_name(guild: discord.Guild, channel_name: str) -> Optional[discord.TextChannel]:
    """Find a channel by name, ignoring emojis and special characters.
    
    Searches for channels where the name ends with the specified name,
    allowing for emoji prefixes like '📝｜bear-log' or '🐻｜bear'.
    """
    # First try exact match
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    if channel:
        return channel
    
    # Try finding channels that end with the name (to handle emoji prefixes)
    for ch in guild.text_channels:
        if ch.name.endswith(channel_name):
            return ch
    
    return None


def get_role_for_type(guild: discord.Guild, role_type: str) -> Optional[discord.Role]:
    """Get configured role object for a notification type."""
    config = load_config()
    guild_config = ensure_guild_config(config, guild.id)
    reaction_cfg = ensure_reaction_roles_config(guild_config)
    role_id = reaction_cfg.get("roles", {}).get(role_type)
    if role_id:
        try:
            role = guild.get_role(int(role_id))
            if role:
                return role
        except (TypeError, ValueError):
            pass
    role_name = REACTION_ROLE_NAMES.get(role_type)
    if not role_name:
        return None
    return discord.utils.get(guild.roles, name=role_name)


def role_key_from_emoji(emoji: str) -> Optional[str]:
    """Resolve reaction emoji to role key."""
    for key, emj in REACTION_EMOJIS.items():
        if emoji == emj:
            return key
    return None


def build_reaction_roles_embed() -> discord.Embed:
    """Build embed used in the reaction-role selection channel."""
    embed = discord.Embed(
        title="📜 Choose Your Adventure!",
        description="React below to activate or disable your notification pings.",
        color=discord.Color.dark_gold(),
    )
    embed.add_field(name="🐻 — Bear Trap 1", value="Get notified before Bear Trap 1.", inline=False)
    embed.add_field(name="🐼 — Bear Trap 2", value="Get notified before Bear Trap 2.", inline=False)
    embed.add_field(name="⚔️ — Arena", value="Get notified about Arena reset.", inline=False)
    embed.add_field(name="🏆 — Event", value="Get notified for game events.", inline=False)
    embed.set_footer(text="👑 Kingshot Notifications Bot • Role Reactions • UTC")
    return embed


def get_reminder_offsets(guild_data: dict, event_type: str) -> list[int]:
    """Get reminder offsets for event type."""
    configs = guild_data.get("configs", {})
    if event_type in configs:
        return configs[event_type].get("reminders", [60, 10, 0])
    return [60, 10, 0]


def format_reminder_offsets(reminders: list[int]) -> str:
    """Format reminder offsets for display."""
    if not reminders:
        return "No reminders configured."
    unique = sorted(set(reminders), reverse=True)
    parts = []
    for offset in unique:
        if offset == 0:
            parts.append("At start")
        elif offset == 1:
            parts.append("1 minute before")
        else:
            parts.append(f"{offset} minutes before")
    return " • ".join(parts)


def format_single_offset(offset: int | None) -> str:
    """Format a single reminder offset."""
    if offset is None:
        return "Not set"
    if offset == 0:
        return "At start"
    if offset == 1:
        return "1 minute before"
    return f"{offset} minutes before"


# ============================================================================
# EMBED BUILDERS
# ============================================================================

def build_channel_header_embed(channel_type: str, guild_data: dict) -> discord.Embed:
    """Build channel header embed."""
    if channel_type == "bear":
        title = "🐻 Bear Event Notifications"
        description = "This channel posts upcoming Bear attack notifications!"
        commands = "/setbear1time • /setbear2time • /setbearping • /cancelbear • /editbear"
    elif channel_type == "arena":
        title = "⚔️ Arena Battle Notifications"
        description = (
            "Arena resets daily at 00:00 UTC. Run your fights as close to reset as possible "
            "to maximize points."
        )
        commands = "/setarenaping"
    else:
        title = "🏆 Event Notifications"
        description = "This channel posts upcoming game event notifications!"
        commands = "/addevent • /addeternity • /addeventlegions • /cancelevent • /editevent • /seteventpings"
    
    embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
    reminder_key = "bear1" if channel_type == "bear" else channel_type
    reminders = get_reminder_offsets(guild_data, reminder_key)
    ordered = sorted(set(reminders), reverse=True)
    if channel_type == "arena":
        event_reminder = ordered[0] if len(ordered) > 0 else None
        final_call = ordered[1] if len(ordered) > 1 else None
        embed.add_field(name="⏱️ Event Reminder", value=format_single_offset(event_reminder), inline=False)
        embed.add_field(name="🔔 Final Call", value=format_single_offset(final_call), inline=False)
        embed.add_field(name="🛑 Arena Reset", value="You will not have time left to run Arena fights.", inline=False)
    elif channel_type == "bear":
        event_reminder = ordered[0] if len(ordered) > 0 else None
        final_call = ordered[1] if len(ordered) > 1 else None
        embed.add_field(name="⏱️ Event Reminder", value=format_single_offset(event_reminder), inline=False)
        embed.add_field(name="🔔 Final Call", value=format_single_offset(final_call), inline=False)
        embed.add_field(name="🎯 Event Start", value="When the bear event begins", inline=False)
    elif channel_type == "event":
        event_reminder = ordered[0] if len(ordered) > 0 else None
        final_call = ordered[1] if len(ordered) > 1 else None
        embed.add_field(name="⏱️ Event Reminder", value=format_single_offset(event_reminder), inline=False)
        embed.add_field(name="🔔 Final Call", value=format_single_offset(final_call), inline=False)
        embed.add_field(name="🎯 Event Start", value="When the event begins", inline=False)
    else:
        reminder_text = format_reminder_offsets(reminders)
        embed.add_field(name="⏱️ Reminders", value=reminder_text, inline=False)
        embed.add_field(name="🎯 Event Start", value="When the event begins", inline=False)
    embed.add_field(name="🎮 Commands", value=commands, inline=False)
    embed.add_field(name="⚙️ Settings", value="Use commands above to adjust reminders (UTC)", inline=False)
    embed.set_footer(text="👑 Kingshot Notifications Bot • UTC")
    return embed


# ============================================================================
# SETUP FUNCTIONS
# ============================================================================


def purge_legacy_bear_events(guild_data: dict) -> int:
    """Remove legacy bear events created before bear1/bear2 split."""
    events = guild_data.get("events", [])
    filtered_events = [ev for ev in events if ev.get("type") != "bear"]
    removed = len(events) - len(filtered_events)
    if removed:
        guild_data["events"] = filtered_events
    return removed


async def ensure_reaction_roles_for_guild(guild: discord.Guild, config: dict, guild_config: dict):
    """Ensure the reaction-role message exists and is up to date for this guild."""
    reaction_cfg = ensure_reaction_roles_config(guild_config)
    channel = None

    stored_channel_id = reaction_cfg.get("channel_id")
    if stored_channel_id:
        channel = guild.get_channel(stored_channel_id)
    if not channel:
        channel = get_channel(guild, guild_config, "reaction")
    if not channel:
        channel = find_channel_by_name(guild, DEFAULT_CHANNEL_NAMES["reaction"])
    if not channel:
        return

    guild_config.setdefault("channels", {})["reaction"] = channel.id
    reaction_cfg["channel_id"] = channel.id

    # Keep role IDs aligned with existing or newly-created roles.
    for role_key, role_name in REACTION_ROLE_NAMES.items():
        role_obj = get_role_for_type(guild, role_key)
        if not role_obj:
            try:
                role_obj = await guild.create_role(name=role_name, mentionable=True, reason="Reaction role setup")
            except Exception as e:
                print(f"Warning: could not create role '{role_name}' in guild {guild.id}: {e}")
                continue
        reaction_cfg["roles"][role_key] = role_obj.id

    existing_message = None
    if reaction_cfg.get("message_id"):
        try:
            existing_message = await channel.fetch_message(int(reaction_cfg["message_id"]))
        except Exception:
            existing_message = None

    embed = build_reaction_roles_embed()
    if existing_message and reaction_cfg.get("version", 0) == REACTION_MESSAGE_VERSION:
        try:
            await existing_message.edit(embed=embed)
            message = existing_message
        except Exception:
            message = await channel.send(embed=embed)
    else:
        message = await channel.send(embed=embed)
        reaction_cfg["message_id"] = message.id
        reaction_cfg["version"] = REACTION_MESSAGE_VERSION

    for emoji in REACTION_EMOJIS.values():
        try:
            await message.add_reaction(emoji)
        except Exception:
            pass

    save_config(config)


async def ensure_channel_headers(guild: discord.Guild, guild_data: dict, guild_config: dict, allowed_types=None):
    """Ensure channel headers exist for the allowed types (or all if None)."""
    headers = guild_data.get("headers", {})
    allowed = set(allowed_types) if allowed_types else {"bear", "arena", "event"}
    
    for channel_type in ["bear", "arena", "event"]:
        if channel_type not in allowed:
            continue
        # Map channel type to config key
        if channel_type == "bear":
            channel = get_channel(guild, guild_config, "bear")
        elif channel_type == "arena":
            channel = get_channel(guild, guild_config, "arena")
        else:  # event
            channel = get_channel(guild, guild_config, "events")
        
        if not channel:
            print(f"⚠️ Channel not found for type: {channel_type}")
            continue
        
        print(f"?� Setting up header for {channel_type} in {channel.name}")
        
        header_info = headers.get(channel_type)
        existing = None
        if header_info and header_info.get("channel_id") == channel.id:
            try:
                existing = await channel.fetch_message(header_info.get("message_id"))
            except Exception:
                pass
        
        embed = build_channel_header_embed(channel_type, guild_data)
        
        if existing:
            try:
                updated = False
                for attempt in range(3):
                    try:
                        await existing.edit(embed=embed)
                        headers[channel_type] = {
                            "channel_id": channel.id,
                            "message_id": existing.id,
                            "version": HEADER_VERSION,
                        }
                        print(f"  Updated existing header for {channel_type}")
                        updated = True
                        break
                    except discord.DiscordServerError as e:
                        if attempt < 2:
                            await asyncio.sleep(1 + attempt)
                            continue
                        print(f"  Warning: temporary Discord error updating {channel_type} header: {e}")
                    except discord.Forbidden as e:
                        print(f"  Warning: missing permissions editing {channel_type} header in channel {channel.id}: {e}")
                        break
                    except discord.HTTPException as e:
                        print(f"  Warning: HTTP error updating {channel_type} header: {e}")
                        break
                if updated:
                    continue
            except Exception as e:
                print(f"  Warning: could not update existing {channel_type} header: {e}")
                pass

        created = False
        for attempt in range(3):
            try:
                sent = await channel.send(embed=embed)
                print(f"  Created new header for {channel_type}")
                headers[channel_type] = {
                    "channel_id": channel.id,
                    "message_id": sent.id,
                    "version": HEADER_VERSION,
                }
                created = True
                break
            except discord.DiscordServerError as e:
                if attempt < 2:
                    await asyncio.sleep(1 + attempt)
                    continue
                print(f"  Warning: temporary Discord error creating {channel_type} header: {e}")
            except discord.Forbidden as e:
                print(f"  Warning: missing permissions creating {channel_type} header in channel {channel.id}: {e}")
                break
            except discord.HTTPException as e:
                print(f"  Warning: HTTP error creating {channel_type} header: {e}")
                break

        if not created:
            print(f"  Skipped header creation for {channel_type}; continuing without blocking commands")
    
    guild_data["headers"] = headers


async def ensure_arena_event(guild: discord.Guild, guild_data: dict, guild_config: dict) -> bool:
    """Ensure arena event exists for next 00:00 UTC and post schedule message."""
    now = datetime.now(pytz.UTC)
    today_midnight = datetime(now.year, now.month, now.day, 0, 0, tzinfo=pytz.UTC)
    
    if now >= today_midnight:
        target = today_midnight + timedelta(days=1)
    else:
        target = today_midnight

    # Skip creation if we already scheduled the arena for this target date (prevents spam when disk storage fails).
    cached_target = ARENA_SCHEDULE_CACHE.get(guild.id)
    if cached_target:
        try:
            if isinstance(cached_target, str):
                cached_dt = datetime.fromisoformat(cached_target)
            else:
                cached_dt = cached_target
            if cached_dt.date() == target.date() and cached_dt >= now:
                return False
        except Exception:
            ARENA_SCHEDULE_CACHE.pop(guild.id, None)
    
    # Check if arena event already exists for target time
    upcoming = [e for e in guild_data.get("events", []) if e.get("type") == "arena"]
    for ev in upcoming:
        try:
            start_dt = datetime.fromisoformat(ev["start_time"])
            if start_dt >= now:
                ARENA_SCHEDULE_CACHE[guild.id] = start_dt
                return False
        except Exception:
            continue
    
    # Create new arena event
    event_id = next_event_id(guild_data)
    arena_channel = get_channel(guild, guild_config, "arena")
    event = {
        "id": event_id,
        "type": "arena",
        "name": "Arena Battles",
        "start_time": target.isoformat(),
        "channel_id": arena_channel.id if arena_channel else None,
        "message_id": None,
        "reminder_offsets": get_reminder_offsets(guild_data, "arena"),
        "sent_offsets": [],
        "created_by": {"user_id": 0, "username": "system"},
        "created_at": now.isoformat(),
    }
    guild_data["events"].append(event)

    # Remember that we've scheduled this target to avoid duplicate postings if events file can't be read.
    ARENA_SCHEDULE_CACHE[guild.id] = target

    # Post schedule message so users see the countdown
    if arena_channel:
        try:
            role_mention = get_notification_mention(guild, "arena")
            ts = int(target.timestamp())
            embed = discord.Embed(
                title="⚔️ Arena Reset Schedule",
                description=(
                    "The server resets at 00:00 UTC. Run your arena fights as close to reset as you can "
                    "to maximize points."
                ),
                color=discord.Color.blurple(),
            )
            embed.add_field(name="🏁 Reset", value=f"<t:{ts}:F> (<t:{ts}:R>)", inline=False)
            embed.add_field(name="🔔 Reminders", value="60m • 10m • reset", inline=False)
            embed.set_footer(text="UTC • Discord will show your local time")
            sent = await arena_channel.send(content=role_mention if role_mention else None, embed=embed)
            event["message_id"] = sent.id
        except Exception as e:
            print(
                f"Warning: could not post arena schedule message in guild {guild.id} "
                f"(channel {arena_channel.id}): {e}"
            )

    return True


# ============================================================================
# EVENT NOTIFICATION FUNCTIONS
# ============================================================================

async def send_event_ping(guild: discord.Guild, event: dict, offset: int, guild_config: dict):
    """Send event ping notification."""
    channel = None
    if event.get("channel_id"):
        channel = guild.get_channel(event["channel_id"])

    if not channel:
        event_type = event.get("type", "event")
        if event_type in {"bear", "bear1", "bear2"}:
            channel = get_channel(guild, guild_config, "bear")
        elif event_type == "arena":
            channel = get_channel(guild, guild_config, "arena")
        else:
            channel = get_channel(guild, guild_config, "events")
    
    if not channel:
        return

    # Build fallback channels to avoid losing notifications when one channel is inaccessible.
    fallback_channels: list[discord.TextChannel] = []
    event_type = event.get("type")
    if event_type == "arena":
        alt_events = get_channel(guild, guild_config, "events")
        alt_bear = get_channel(guild, guild_config, "bear")
        if alt_events:
            fallback_channels.append(alt_events)
        if alt_bear:
            fallback_channels.append(alt_bear)
    elif event_type in {"bear", "bear1", "bear2"}:
        alt_events = get_channel(guild, guild_config, "events")
        if alt_events:
            fallback_channels.append(alt_events)

    target_channels: list[discord.TextChannel] = [channel]
    for alt in fallback_channels:
        if alt and all(existing.id != alt.id for existing in target_channels):
            target_channels.append(alt)

    role_mention = get_notification_mention(guild, event.get("type", "event"), event.get("name", ""))
    
    start_dt = datetime.fromisoformat(event["start_time"])
    ts = int(start_dt.timestamp())
    when_text = f"<t:{ts}:F> (<t:{ts}:R>)"
    
    # Arena-specific messaging
    if event.get("type") == "arena":
        if offset == 60:
            title = "⏱️ 1 Hour Until Arena Reset"
            description = (
                "One hour until the Arena resets. Be prepared to do your Arena runs "
                "as close to the reset as possible to maximize your points."
            )
        elif offset == 10:
            title = "⚔️ It’s Time to Fight"
            description = (
                "Good time to start your 10 Arena attacks: 5 free and 5 purchased with gems. "
                "Remember to time your battles as close to reset as possible."
            )
        elif offset == 0:
            title = "🎯 Arena Reset Now"
            description = (
                "The Arena has been reset. Remember, it's best to wait until the last few minutes "
                "to achieve the best ranking and rewards."
            )
        else:
            title = f"⏱️ Event in {offset} minutes"
            description = f"**{event.get('name','Event')}**\nStart: {when_text}"
        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
    # KVK PVP Zone-specific messaging
    elif event.get("name") == "KVK PVP Zone":
        if offset == 60:
            title = "⚠️ Be Careful"
            description = (
                "There's only 1 hour left before the PvP zone begins and enemy invaders can attack us. "
                "If you don't want to participate, remember to activate your shield."
            )
        elif offset == 10:
            title = "⚠️ Warning"
            description = (
                "There are only 10 minutes left before the PvP zone begins and enemy invaders can attack us. "
                "If you don't want to participate, remember to activate your shield and keep it updated so you're protected throughout the event."
            )
        elif offset == 0:
            title = "🎯 PvP Zone Starting Now"
            description = (
                "The KVK PvP Zone has begun! Enemy invaders can now attack. "
                "Make sure your shield is active if you're not participating."
            )
        else:
            title = f"⏱️ Event in {offset} minutes"
            description = f"**{event.get('name','Event')}**\nStart: {when_text}"
        embed = discord.Embed(title=title, description=description, color=discord.Color.red())
    elif event.get("name") == "Eternity's Reach":
        if offset == 60:
            title = "⏱️ 1 Hour Until Eternity's Reach"
        elif offset == 10:
            title = "🔔 Final Call: Eternity's Reach"
        elif offset == 0:
            title = "🎯 Eternity's Reach Starting Now"
        else:
            title = f"⏱️ Eternity's Reach in {offset} minutes"

        description = (
            f"Start: {when_text}\n\n"
            "Register in the time slot that fits you best for your own run.\n"
            "Available play slots (UTC): 05:00, 11:00, 14:00, 16:00, 18:00, 21:00.\n"
            "Check the strategy guides shared in Discord chats to maximize your individual score."
        )
        embed = discord.Embed(title=title, description=description, color=discord.Color.dark_teal())
        embed.set_image(url=ETERNITY_IMAGE_URL)
    else:
        if offset == 0:
            title = "🎯 Event Starting Now"
        elif offset == 10:
            title = "🔔 Final Call"
        else:
            title = f"⏱️ Event in {offset} minutes"
        embed = discord.Embed(
            title=title,
            description=f"**{event.get('name','Event')}**\nStart: {when_text}",
            color=discord.Color.gold()
        )
    
    event_id = event.get("id")
    if isinstance(event_id, int) and event_id > 0:
        embed.set_footer(text=f"Event ID: {event_id} • UTC time • shown in your local time by Discord")
    else:
        embed.set_footer(text="UTC time • shown in your local time by Discord")

    content = role_mention if role_mention else None
    for target in target_channels:
        try:
            sent = await target.send(content=content, embed=embed)
            return sent
        except discord.Forbidden as e:
            print(f"Warning: missing access sending event ping to channel {target.id} in guild {guild.id}: {e}")
            continue
        except discord.DiscordServerError as e:
            print(f"Warning: Discord server error sending event ping to channel {target.id}: {e}")
            continue
        except discord.HTTPException as e:
            print(f"Warning: HTTP error sending event ping to channel {target.id}: {e}")
            continue

    return None


async def delete_event_message(guild: discord.Guild, event: dict, guild_config: dict):
    """Delete event message and all reminder messages."""
    channel = None
    if event.get("channel_id"):
        channel = guild.get_channel(event["channel_id"])

    if not channel:
        event_type = event.get("type", "event")
        if event_type in {"bear", "bear1", "bear2"}:
            channel = get_channel(guild, guild_config, "bear")
        elif event_type == "arena":
            channel = get_channel(guild, guild_config, "arena")
        else:
            channel = get_channel(guild, guild_config, "events")
    
    if not channel:
        return
    
    # Delete main event message
    if event.get("message_id"):
        try:
            msg = await channel.fetch_message(event["message_id"])
            await msg.delete()
        except Exception:
            pass
    
    # Delete all reminder messages
    for msg_id in event.get("reminder_message_ids", []):
        try:
            msg = await channel.fetch_message(msg_id)
            await msg.delete()
        except Exception:
            pass


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

@tasks.loop(minutes=1)
async def check_event_notifications():
    """Check scheduled events and send notifications."""
    try:
        data = load_events()
        config = load_config()
        now = datetime.now(pytz.UTC)
        changed = False
        
        for guild in bot.guilds:
            try:
                guild_data = ensure_guild_data(data, guild.id)
                guild_config = ensure_guild_config(config, guild.id)

                if not guild_config.get("installed"):
                    continue

                # Ensure arena event exists and post schedule message
                if await ensure_arena_event(guild, guild_data, guild_config):
                    changed = True

                # Process all events
                for ev in list(guild_data.get("events", [])):
                    try:
                        start_dt = datetime.fromisoformat(ev["start_time"])
                    except Exception:
                        continue

                    offsets = ev.get("reminder_offsets") or get_reminder_offsets(guild_data, ev.get("type", "event"))

                    # Send reminders
                    for offset in offsets:
                        sent_offsets = ev.setdefault("sent_offsets", [])
                        if offset in sent_offsets:
                            continue

                        trigger_time = start_dt - timedelta(minutes=offset)
                        # Catch-up mode: if the bot was restarting during the exact minute window,
                        # still deliver pending reminders while the event has not started yet.
                        if now >= trigger_time and now < start_dt:
                            try:
                                sent_msg = await send_event_ping(guild, ev, offset, guild_config)
                                if sent_msg:
                                    sent_offsets.append(offset)
                                    # Store reminder message IDs to delete later
                                    reminder_msg_ids = ev.setdefault("reminder_message_ids", [])
                                    reminder_msg_ids.append(sent_msg.id)
                                    changed = True
                                else:
                                    print(
                                        f"Warning: could not send reminder offset {offset} for event {ev.get('id')} "
                                        f"in guild {guild.id} (channel missing or inaccessible)"
                                    )
                            except Exception as send_error:
                                print(
                                    f"Warning: reminder send failed for guild {guild.id}, event {ev.get('id')}, "
                                    f"offset {offset}: {send_error}"
                                )

                    # Clean up past events (bear stays longer to allow 30m damage reminder)
                    cleanup_deadline = start_dt + timedelta(minutes=5)
                    if ev.get("type") in {"bear", "bear1", "bear2"}:
                        cleanup_deadline = start_dt + timedelta(minutes=40)

                        # Send bear damage report reminder 30 minutes after bear event
                        # Check before cleanup to ensure it's sent even if there were delays
                        thirty_min_after = start_dt + timedelta(minutes=30)
                        if False:  # DISABLED: bear-log damage report reminder (desactivado manualmente)
                            # Buscar específicamente el canal bear-log (prioridad absoluta)
                            bear_log_channel = None

                            # 1. Intentar configuración guardada
                            bear_log_channel = get_channel(guild, guild_config, "bear_log")

                            # 2. Buscar por nombre "bear-log" directamente
                            if not bear_log_channel:
                                bear_log_channel = find_channel_by_name(guild, "bear-log")

                            # 3. Buscar variantes de bear-log (con emojis, etc)
                            if not bear_log_channel:
                                for ch in guild.text_channels:
                                    if "bear-log" in ch.name.lower() or ch.name.lower() == "bear-log":
                                        bear_log_channel = ch
                                        break

                            # 4. Si aún no lo encuentra, usar canal de bear solo como último recurso
                            if not bear_log_channel:
                                bear_log_channel = get_channel(guild, guild_config, "bear")

                            if not bear_log_channel:
                                bear_log_channel = get_channel(guild, guild_config, "events")

                            if bear_log_channel:
                                try:
                                    role_mention = get_notification_mention(guild, ev.get("type", "event"), ev.get("name", ""))

                                    # Obtener información del evento
                                    bear_name = ev.get("name", "Bear")
                                    event_time = start_dt.strftime("%d/%m/%Y %H:%M")

                                    await bear_log_channel.send(
                                        f"📊 **Damage Report Reminder**\n\n"
                                        f"**{bear_name}** - {event_time}\n\n"
                                        f"Please, could a {(role_mention if role_mention else 'relevant')} player send the screenshoot of damage report for this Bear Hunt? Thank you."
                                    )
                                    ev["damage_report_reminder_sent"] = True
                                    changed = True
                                    print(f"Sent damage report reminder for bear event ID {ev['id']} to channel {bear_log_channel.id}")
                                except Exception as e:
                                    print(f"Error sending damage report reminder: {e}")
                            else:
                                print(f"Warning: Could not find bear_log/bear/events channel for guild {guild.id}")

                    if now > cleanup_deadline:
                        await delete_event_message(guild, ev, guild_config)

                        # Auto-schedule next bear event (+2 days) when a bear ends
                        if ev.get("type") in {"bear", "bear1", "bear2"}:
                            next_bear_start = start_dt + timedelta(days=2)
                            next_bear_id = next_event_id(guild_data)
                            normalized_type = normalize_event_type_for_roles(ev.get("type", "bear"), ev.get("name", ""))
                            bear_name = "Bear Trap 1" if normalized_type == "bear1" else "Bear Trap 2"
                            next_bear = {
                                "id": next_bear_id,
                                "type": normalized_type,
                                "name": bear_name,
                                "start_time": next_bear_start.isoformat(),
                                "channel_id": ev.get("channel_id"),
                                "reminder_offsets": ev.get("reminder_offsets") or get_reminder_offsets(guild_data, normalized_type),
                                "sent_offsets": [],
                                "created_by": ev.get("created_by"),
                                "created_at": now.isoformat()
                            }
                            guild_data["events"].append(next_bear)
                            print(f"Auto-scheduled next {bear_name} (ID {next_bear_id}) for {next_bear_start}")

                            # Post the new bear message
                            bear_channel = get_channel(guild, guild_config, "bear")
                            if bear_channel:
                                try:
                                    start_ts = int(next_bear_start.timestamp())
                                    role_mention = get_notification_mention(guild, next_bear.get("type", "event"), next_bear.get("name", ""))
                                    embed = discord.Embed(
                                        title=f"🐻 {bear_name} Scheduled",
                                        description=f"Start: <t:{start_ts}:F> (<t:{start_ts}:R>)",
                                        color=discord.Color.green()
                                    )
                                    embed.set_footer(text=f"Event ID: {next_bear_id} • UTC • Discord will show your local time")
                                    msg = await bear_channel.send(content=role_mention if role_mention else None, embed=embed)
                                    next_bear["message_id"] = msg.id
                                except Exception as e:
                                    print(f"Error posting auto-scheduled {bear_name} message: {e}")

                        guild_data["events"] = [x for x in guild_data["events"] if x["id"] != ev["id"]]
                        changed = True
            except Exception as guild_error:
                print(f"Error processing guild {guild.id}: {guild_error}")
        
        if changed:
            save_events(data)
    except Exception as e:
        print(f"Error in event notification checker: {e}")


# ============================================================================
# BOT EVENTS
# ============================================================================

async def sync_commands_for_guild(guild: discord.Guild, retries: int = 3) -> list[app_commands.AppCommand]:
    """Sync application commands for a single guild with retries."""
    await bot.wait_until_ready()

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            guild_obj = discord.Object(id=guild.id)
            bot.tree.copy_global_to(guild=guild_obj)
            return await bot.tree.sync(guild=guild_obj)
        except discord.DiscordServerError as e:
            last_error = e
            if attempt < retries - 1:
                await asyncio.sleep(1 + attempt)
                continue
            raise
        except discord.HTTPException as e:
            last_error = e
            if attempt < retries - 1:
                await asyncio.sleep(1 + attempt)
                continue
            raise

    if last_error:
        raise last_error
    return []

@bot.event
async def on_ready():
    """Bot startup handler."""
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot user ID: {bot.user.id}')

    guild_count = len(bot.guilds)
    print(f'\n📊 Connected to {guild_count} server(s):')
    for guild in bot.guilds:
        print(f'  - {guild.name} (ID: {guild.id})')

    if not check_event_notifications.is_running():
        check_event_notifications.start()
        print('\n🔔 Event notification checker started')

    # Refresh headers/reaction roles for installed guilds and purge legacy bear events.
    events_data = load_events()
    config = load_config()
    events_changed = False
    for guild in bot.guilds:
        try:
            guild_data = ensure_guild_data(events_data, guild.id)
            guild_config = ensure_guild_config(config, guild.id)
            removed_legacy = purge_legacy_bear_events(guild_data)
            if removed_legacy:
                events_changed = True
                print(f"Purged {removed_legacy} legacy bear event(s) in guild {guild.id}")
            if guild_config.get("installed"):
                await ensure_channel_headers(guild, guild_data, guild_config)
                await ensure_reaction_roles_for_guild(guild, config, guild_config)
        except Exception as e:
            print(f"Warning: setup refresh failed for guild {guild.id}: {e}")

    if events_changed:
        save_events(events_data)
    save_config(config)

    print('\nSyncing commands to Discord...')
    # Sync only per guild (guild commands take priority and prevent duplicates with globals)
    guild_synced = []
    for guild in bot.guilds:
        try:
            guild_synced = await sync_commands_for_guild(guild)
            print(f'  ✓ Commands synced for guild {guild.name}: {len(guild_synced)} commands')
        except Exception as e:
            print(f'  ✗ Error syncing commands for guild {guild.name}: {e}')
            import traceback
            traceback.print_exc()

    for cmd in guild_synced:
        print(f'    - /{cmd.name}: {cmd.description}')


@bot.event
async def on_guild_join(guild):
    """Handler for joining a new server."""
    print(f'\n✅ Joined new server: {guild.name} (ID: {guild.id})')
    try:
        synced = await sync_commands_for_guild(guild)
        print(f'  ✓ Commands synced for new guild {guild.name}: {len(synced)} commands')
    except Exception as e:
        print(f'  ✗ Error syncing commands for new guild {guild.name}: {e}')
        import traceback
        traceback.print_exc()


@bot.event
async def on_guild_remove(guild):
    """Handler for being removed from a server."""
    print(f'\n❌ Removed from server: {guild.name} (ID: {guild.id})')


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Assign notification roles on reaction add."""
    if payload.user_id == bot.user.id or not payload.guild_id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    config = load_config()
    guild_config = ensure_guild_config(config, payload.guild_id)
    reaction_cfg = ensure_reaction_roles_config(guild_config)
    if not reaction_cfg.get("enabled"):
        return
    stored_message_id = reaction_cfg.get("message_id")
    if not stored_message_id:
        return
    try:
        stored_message_id = int(stored_message_id)
    except (TypeError, ValueError):
        return
    if payload.message_id != stored_message_id:
        return

    role_key = role_key_from_emoji(str(payload.emoji))
    if not role_key:
        return

    role = get_role_for_type(guild, role_key)
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
    """Remove notification roles on reaction remove."""
    if not payload.guild_id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    config = load_config()
    guild_config = ensure_guild_config(config, payload.guild_id)
    reaction_cfg = ensure_reaction_roles_config(guild_config)
    if not reaction_cfg.get("enabled"):
        return
    stored_message_id = reaction_cfg.get("message_id")
    if not stored_message_id:
        return
    try:
        stored_message_id = int(stored_message_id)
    except (TypeError, ValueError):
        return
    if payload.message_id != stored_message_id:
        return

    role_key = role_key_from_emoji(str(payload.emoji))
    if not role_key:
        return

    role = get_role_for_type(guild, role_key)
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


# ============================================================================
# INSTALL COMMAND
# ============================================================================

@bot.tree.command(name="install")
@app_commands.describe(
    mode="Choose installation mode: auto (create channels) or manual (specify existing)"
)
@app_commands.choices(mode=[
    app_commands.Choice(name="🤖 Auto (create channels)", value="auto"),
    app_commands.Choice(name="?�️ Manual (use existing)", value="manual")
])
async def install_command(
    interaction: discord.Interaction,
    mode: app_commands.Choice[str]
):
    """Install the notification system in this server."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return
    
    if not has_command_permission(interaction.user):
        await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
        return
    
    config = load_config()
    guild_config = ensure_guild_config(config, interaction.guild.id)

    # Allow /install to always (re)configure the server.
    if mode.value == "auto":
        await install_auto(interaction, config, guild_config)
    else:
        await install_manual(interaction, config, guild_config)


async def install_auto(interaction: discord.Interaction, config: dict, guild_config: dict):
    """Auto installation - create category and channels."""
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    
    try:
        # Create category
        category = await guild.create_category("Kingshot Notifications")
        guild_config["category_id"] = category.id
        
        # Create channels
        bear_channel = await guild.create_text_channel("🐻｜bear", category=category)
        bear_log_channel = await guild.create_text_channel("📝｜bear-log", category=category)
        arena_channel = await guild.create_text_channel("⚔️｜arena", category=category)
        events_channel = await guild.create_text_channel("🏆｜events", category=category)
        reaction_channel = await guild.create_text_channel("📜｜notification-settings", category=category)

        guild_config["channels"] = {
            "bear": bear_channel.id,
            "bear_log": bear_log_channel.id,
            "arena": arena_channel.id,
            "events": events_channel.id,
            "reaction": reaction_channel.id,
        }
        reaction_cfg = ensure_reaction_roles_config(guild_config)
        reaction_cfg["channel_id"] = reaction_channel.id
        
        guild_config["installed"] = True
        save_config(config)
        
        # Setup headers
        data = load_events()
        guild_data = ensure_guild_data(data, guild.id)
        
        await ensure_channel_headers(guild, guild_data, guild_config)
        await ensure_reaction_roles_for_guild(guild, config, guild_config)

        save_events(data)
        
        embed = discord.Embed(
            title="?� Installation Complete!",
            description="The notification system has been set up successfully.",
            color=discord.Color.green()
        )
        embed.add_field(name="📁 Category", value=f"{category.mention}", inline=False)
        embed.add_field(
            name="📺 Channels", 
            value=f"{bear_channel.mention}\n{bear_log_channel.mention}\n{arena_channel.mention}\n{events_channel.mention}\n{reaction_channel.mention}",
            inline=False
        )
        embed.add_field(
            name="📖 Next Steps",
            value="• Use reactions in #notification-settings to opt in/out of pings\n"
                  "• Use `/setadmin` to select the admin role for this server\n"
                  "• Use `/setbear1time` and `/setbear2time` to schedule bear traps\n"
                  "• Use `/addevent` for simple events\n"
                  "• Use `/addeternity` to schedule Eternity's Reach (05:00 UTC)\n"
                  "• Use `/addeventlegions` for Swordland/Tri Alliance\n"
                  "• Arena notifications are automatic at 00:00 UTC",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error during installation: {str(e)}", ephemeral=True)
        print(f"Installation error: {e}")
        import traceback
        traceback.print_exc()


async def install_manual(interaction: discord.Interaction, config: dict, guild_config: dict):
    """Manual installation - ask for existing channels."""
    await interaction.response.send_message(
        "?�️ **Manual Installation**\n\n"
        "Please mention or provide the channel names/IDs for:\n"
        "1️⃣ Category name (will be created if doesn't exist)\n"
        "2️⃣ Bear channel\n"
        "3️⃣ Bear log channel\n"
        "4️⃣ Arena channel\n"
        "5️⃣ Events channel\n"
        "6️⃣ Reaction roles channel\n\n"
        "**Format:** Respond in chat with channel mentions or names, one per line.\n"
        "Example:\n```\nKingshot Notifications\n#bear\n#bear-log\n#arena\n#events\n#notification-settings```\n\n"
        "⏳ Waiting for your response (60 seconds)...",
        ephemeral=True
    )
    
    def check(m):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
    
    try:
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        lines = [line.strip() for line in msg.content.split('\n') if line.strip()]
        
        if len(lines) < 6:
            await interaction.followup.send("❌ Not enough information provided. Please try again.", ephemeral=True)
            return
        
        category_name = lines[0]
        
        # Find or create category
        category = discord.utils.get(interaction.guild.categories, name=category_name)
        if not category:
            category = await interaction.guild.create_category(category_name)
        
        guild_config["category_id"] = category.id
        
        # Parse channels
        channels_to_find = {
            "bear": lines[1],
            "bear_log": lines[2],
            "arena": lines[3],
            "events": lines[4],
            "reaction": lines[5],
        }
        
        for key, value in channels_to_find.items():
            # Try to extract channel ID from mention
            if value.startswith('<#') and value.endswith('>'):
                channel_id = int(value[2:-1])
                channel = interaction.guild.get_channel(channel_id)
            else:
                # Search by name
                channel_name = value.lstrip('#')
                channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
            
            if channel:
                guild_config["channels"][key] = channel.id
            else:
                await interaction.followup.send(f"❌ Could not find channel: {value}", ephemeral=True)
                return
        
        guild_config["installed"] = True
        save_config(config)
        
        # Setup headers
        data = load_events()
        guild_data = ensure_guild_data(data, interaction.guild.id)
        
        await ensure_channel_headers(interaction.guild, guild_data, guild_config)
        await ensure_reaction_roles_for_guild(interaction.guild, config, guild_config)

        save_events(data)
        
        embed = discord.Embed(
            title="?� Manual Installation Complete!",
            description="The notification system has been configured.",
            color=discord.Color.green()
        )
        embed.add_field(name="📁 Category", value=f"<#{guild_config['category_id']}>", inline=False)
        embed.add_field(
            name="📺 Configured Channels",
            value="\n".join([f"<#{ch_id}>" for ch_id in guild_config["channels"].values()]),
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except asyncio.TimeoutError:
        await interaction.followup.send("⏰ Timeout - No response received. Please try again.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error during manual installation: {str(e)}", ephemeral=True)
        print(f"Manual installation error: {e}")
        import traceback
        traceback.print_exc()


@bot.tree.command(name="uninstall")
async def uninstall_command(interaction: discord.Interaction):
    """Remove notification bot configuration from this server (deletes channels separately if needed)."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return
    
    if not has_command_permission(interaction.user):
        await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
        return
    
    config = load_config()
    guild_id = interaction.guild.id
    gid = str(guild_id)

    guild_config = config.get(gid)
    if not guild_config:
        await interaction.response.send_message("ℹ️ Bot is not installed in this server yet.", ephemeral=True)
        return
    
    # Remove guild configuration
    del config[gid]
    save_config(config)
    
    # Clean up events for this guild
    data = load_events()
    guilds = data.get("guilds", {})
    legacy_guild_data = data.get("guild_data", {})

    event_count = 0
    if gid in guilds:
        event_count += len(guilds[gid].get("events", []))
        del guilds[gid]

    # Backward compatibility: clean old key if it exists.
    if gid in legacy_guild_data:
        event_count += len(legacy_guild_data[gid].get("events", []))
        del legacy_guild_data[gid]

    save_events(data)

    if event_count > 0:
        
        embed = discord.Embed(
            title="✅ Bot Uninstalled",
            description=f"Configuration removed for **{interaction.guild.name}**",
            color=discord.Color.orange()
        )
        embed.add_field(name="📊 Cleaned Up", value=f"{event_count} scheduled event(s) removed", inline=False)
        embed.add_field(name="💡 Note", value="Use `/install` to set up the bot again later.", inline=False)
    else:
        embed = discord.Embed(
            title="✅ Bot Uninstalled",
            description=f"Configuration removed for **{interaction.guild.name}**",
            color=discord.Color.orange()
        )
        embed.add_field(name="💡 Note", value="Use `/install` to set up the bot again later.", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="setadmin")
@app_commands.describe(role="Role allowed to manage this bot in this server")
async def setadmin_command(interaction: discord.Interaction, role: discord.Role):
    """Set the per-server role that can manage notification commands."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Only Discord administrators can configure `/setadmin`.",
            ephemeral=True,
        )
        return

    if role.is_default():
        await interaction.response.send_message(
            "❌ Please select a specific role, not @everyone.",
            ephemeral=True,
        )
        return

    apply_admin_role_config(interaction.guild.id, role.id)

    await interaction.response.send_message(
        f"✅ Admin role configured: {role.mention} (ID: {role.id})\n"
        "Members with this role can now use bot management commands.\n"
        "If a role is missing from this picker, use `/setadminid`.",
        ephemeral=True,
    )


def apply_admin_role_config(guild_id: int, role_id: int):
    """Persist the admin role configuration for a guild."""
    config = load_config()
    guild_config = ensure_guild_config(config, guild_id)
    guild_config["admin_role_id"] = role_id
    save_config(config)


@bot.tree.command(name="setadminid")
@app_commands.describe(role_id="Role ID or role mention to allow (example: 123456789 or <@&123456789>)")
async def setadminid_command(interaction: discord.Interaction, role_id: str):
    """Set admin role by ID/mention when Discord picker doesn't list all roles."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Only Discord administrators can configure `/setadminid`.",
            ephemeral=True,
        )
        return

    match = re.search(r"\d+", role_id)
    if not match:
        await interaction.response.send_message(
            "❌ Invalid role input. Use a role ID or mention like `<@&123456789>`.",
            ephemeral=True,
        )
        return

    parsed_role_id = int(match.group(0))
    role = interaction.guild.get_role(parsed_role_id)
    if not role:
        await interaction.response.send_message(
            "❌ Role not found in this server. Check the ID/mention and try again.",
            ephemeral=True,
        )
        return

    if role.is_default():
        await interaction.response.send_message(
            "❌ Please select a specific role, not @everyone.",
            ephemeral=True,
        )
        return

    apply_admin_role_config(interaction.guild.id, role.id)

    await interaction.response.send_message(
        f"✅ Admin role configured: {role.mention} (ID: {role.id})",
        ephemeral=True,
    )


# ============================================================================
# BEAR COMMANDS
# ============================================================================

async def schedule_bear_trap(
    interaction: discord.Interaction,
    trap_type: str,
    date: str,
    time: str,
):
    """Shared handler for /setbear1time and /setbear2time."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return

    if not has_command_permission(interaction.user):
        await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
        return

    config = load_config()
    guild_config = ensure_guild_config(config, interaction.guild.id)
    if not guild_config.get("installed"):
        await interaction.response.send_message(
            "❌ Bot not installed. Please run `/install` first.",
            ephemeral=True,
        )
        return

    start_dt = parse_date_time_utc(date, time)
    if not start_dt:
        await interaction.response.send_message(
            "❌ Invalid format. Use:\n"
            "• Date: YYYY-MM-DD (e.g., 2026-01-25)\n"
            "• Time: HH:MM (e.g., 14:30)\n"
            "All times are in UTC.",
            ephemeral=True,
        )
        return

    now = datetime.now(pytz.UTC)
    if start_dt <= now:
        await interaction.response.send_message("❌ Date/time must be in the future (UTC).", ephemeral=True)
        return

    channel = get_channel(interaction.guild, guild_config, "bear")
    if not channel:
        await interaction.response.send_message("❌ Bear channel not configured.", ephemeral=True)
        return

    trap_name = "Bear Trap 1" if trap_type == "bear1" else "Bear Trap 2"

    data = load_events()
    guild_data = ensure_guild_data(data, interaction.guild.id)

    # Verificar si ya existe una trampa programada del mismo tipo
    existing_trap = None
    for event in guild_data.get("events", []):
        if event.get("type") == trap_type:
            existing_trap = event
            break

    if existing_trap:
        trap_id = existing_trap.get("id")
        await interaction.response.send_message(
            f"⚠️ There is already a {trap_name} scheduled (ID {trap_id}).\n\n"
            f"Only one schedule per trap is allowed. Use `/editbear` with ID `{trap_id}` to modify the existing one.",
            ephemeral=True,
        )
        return

    event_id = next_event_id(guild_data)
    event = {
        "id": event_id,
        "type": trap_type,
        "name": trap_name,
        "start_time": start_dt.isoformat(),
        "channel_id": channel.id,
        "message_id": None,
        "reminder_offsets": get_reminder_offsets(guild_data, trap_type),
        "sent_offsets": [],
        "created_by": {"user_id": interaction.user.id, "username": str(interaction.user)},
        "created_at": now.isoformat(),
    }
    guild_data["events"].append(event)
    save_events(data)

    role_mention = get_notification_mention(interaction.guild, trap_type, trap_name)
    ts = int(start_dt.timestamp())
    embed = discord.Embed(
        title=f"🐻 {trap_name} Scheduled",
        description=f"Start: <t:{ts}:F> (<t:{ts}:R>)",
        color=discord.Color.green(),
    )
    embed.set_footer(text=f"Event ID: {event_id} • UTC • Discord will show your local time")
    sent = await channel.send(content=role_mention if role_mention else None, embed=embed)
    event["message_id"] = sent.id
    save_events(data)

    await interaction.response.send_message(
        f"✅ {trap_name} scheduled (ID {event_id}) for <t:{ts}:F>.\n"
        "*This trap will auto-renew +48h after it ends.*",
        ephemeral=True,
    )


@bot.tree.command(name="setbear1time")
@app_commands.describe(
    date="Trap 1 date in YYYY-MM-DD format (UTC)",
    time="Trap 1 time in HH:MM format (UTC, 24h)",
)
async def setbear1time_command(interaction: discord.Interaction, date: str, time: str):
    """Schedule Bear Trap 1."""
    await schedule_bear_trap(interaction, "bear1", date, time)


@bot.tree.command(name="setbear2time")
@app_commands.describe(
    date="Trap 2 date in YYYY-MM-DD format (UTC)",
    time="Trap 2 time in HH:MM format (UTC, 24h)",
)
async def setbear2time_command(interaction: discord.Interaction, date: str, time: str):
    """Schedule Bear Trap 2."""
    await schedule_bear_trap(interaction, "bear2", date, time)


@bot.tree.command(name="refresh")
@app_commands.describe(channel="Select what to refresh")
@app_commands.choices(channel=[
    app_commands.Choice(name="ALL", value="all"),
    app_commands.Choice(name="Bear", value="bear"),
    app_commands.Choice(name="Arena", value="arena"),
    app_commands.Choice(name="Events", value="event"),
])
async def refresh_command(interaction: discord.Interaction, channel: app_commands.Choice[str]):
    """Refresh headers/countdowns: ALL, Bear, Arena, or Events."""
    try:
        if not interaction.guild:
            await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
            return

        if not has_command_permission(interaction.user):
            await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
            return

        config = load_config()
        guild_config = ensure_guild_config(config, interaction.guild.id)

        if not guild_config.get("installed"):
            await interaction.response.send_message("❌ Bot not installed. Run `/install` first.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        data = load_events()
        guild_data = ensure_guild_data(data, interaction.guild.id)

        chosen = channel.value
        scopes = {chosen} if chosen != "all" else {"bear", "arena", "event"}

        # Delete bot messages only in selected channels
        channel_map = {
            "bear": guild_config.get("channels", {}).get("bear"),
            "arena": guild_config.get("channels", {}).get("arena"),
            "event": guild_config.get("channels", {}).get("events"),
        }

        for key, ch_id in channel_map.items():
            if key not in scopes:
                continue
            if not ch_id:
                continue
            ch = interaction.guild.get_channel(ch_id)
            if not ch:
                continue

            try:
                deleted_count = 0
                async for msg in ch.history(limit=None):
                    if msg.author == interaction.client.user:
                        try:
                            await msg.delete()
                            deleted_count += 1
                        except Exception:
                            pass
                print(f"refresh: deleted {deleted_count} messages from {key} channel")
            except Exception as e:
                print(f"refresh: error cleaning {key} channel: {e}")

        # Refresh headers only for selected scopes
        headers = guild_data.get("headers", {})
        for t in scopes:
            headers.pop(t, None)
        guild_data["headers"] = headers

        await ensure_channel_headers(interaction.guild, guild_data, guild_config, scopes)

        # Recreate countdown messages only for selected event types
        bear_channel = interaction.guild.get_channel(guild_config.get("channels", {}).get("bear"))
        arena_channel = interaction.guild.get_channel(guild_config.get("channels", {}).get("arena"))
        events_channel = interaction.guild.get_channel(guild_config.get("channels", {}).get("events"))

        for event in guild_data.get("events", []):
            try:
                event_type = event.get("type")
                scope_type = "bear" if event_type in {"bear", "bear1", "bear2"} else event_type
                if scope_type not in scopes:
                    continue
                start_dt = datetime.fromisoformat(event["start_time"])
                ts = int(start_dt.timestamp())

                if event_type in {"bear", "bear1", "bear2"} and bear_channel:
                    channel = bear_channel
                    title = f"🐻 {event.get('name', 'Bear Trap')} Scheduled"
                elif event_type == "arena" and arena_channel:
                    channel = arena_channel
                    title = "⚔️ Arena Reset Schedule"
                elif event_type == "event" and events_channel:
                    channel = events_channel
                    title = f"🏆 {event.get('name', 'Event')} Scheduled"
                else:
                    continue

                if event_type == "arena":
                    embed = discord.Embed(
                        title=title,
                        description=(
                            "The server resets at 00:00 UTC. Run your arena fights as close to reset as you can "
                            "to maximize points."
                        ),
                        color=discord.Color.blurple(),
                    )
                    embed.add_field(name="🏁 Reset", value=f"<t:{ts}:F> (<t:{ts}:R>)", inline=False)
                    embed.set_footer(text=f"Event ID: {event.get('id')} • UTC • Discord will show your local time")
                else:
                    embed = discord.Embed(
                        title=title,
                        description=f"Start: <t:{ts}:F> (<t:{ts}:R>)",
                        color=discord.Color.green() if event_type in {"bear", "bear1", "bear2"} else discord.Color.gold(),
                    )
                    embed.set_footer(text=f"Event ID: {event.get('id')} • UTC • Discord will show your local time")

                role_mention = get_notification_mention(interaction.guild, event_type, event.get("name", ""))
                sent = await channel.send(content=role_mention if role_mention else None, embed=embed)
                event["message_id"] = sent.id
                event["channel_id"] = channel.id
                
            except Exception as e:
                print(f"refresh: error recreating event {event.get('id')}: {e}")

        save_events(data)

        label = chosen.upper() if chosen != "event" else "EVENTS"
        await interaction.followup.send(f"?� Refreshed: {label}", ephemeral=True)
    except Exception as e:
        print(f"refresh command failed: {e}")
        import traceback
        traceback.print_exc()
        try:
            if interaction.is_expired():
                return
            if interaction.response.is_done():
                await interaction.followup.send("❌ Refresh failed. Check logs.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Refresh failed. Check logs.", ephemeral=True)
        except Exception:
            pass


@bot.tree.command(name="setbearping")
@app_commands.describe(
    event_reminder="Minutes before (Event Reminder, e.g., 60)",
    final_call="Minutes before (Final Call, e.g., 10)",
)
async def setbearping_command(
    interaction: discord.Interaction,
    event_reminder: int = 60,
    final_call: int = 10,
):
    """Configure bear event reminder times (in minutes before start)."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return
    
    if not has_command_permission(interaction.user):
        await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
        return
    
    config = load_config()
    guild_config = ensure_guild_config(config, interaction.guild.id)
    
    if not guild_config.get("installed"):
        await interaction.response.send_message("❌ Bot not installed. Run `/install` first.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        data = load_events()
        guild_data = ensure_guild_data(data, interaction.guild.id)

        reminders = [event_reminder, final_call]
        guild_data["configs"]["bear1"]["reminders"] = reminders
        guild_data["configs"]["bear2"]["reminders"] = reminders

        now = datetime.now(pytz.UTC)
        for ev in guild_data.get("events", []):
            if ev.get("type") not in {"bear", "bear1", "bear2"}:
                continue
            try:
                start_dt = datetime.fromisoformat(ev["start_time"])
            except Exception:
                continue
            if start_dt >= now:
                ev["reminder_offsets"] = reminders

        save_events(data)

        # Update bear header to reflect new reminder times
        await ensure_channel_headers(interaction.guild, guild_data, guild_config, ["bear"])
        save_events(data)

        await interaction.followup.send(
            "✅ Bear trap reminders updated:\n"
            f"• Event Reminder: {event_reminder} minutes before start\n"
            f"• Final Call: {final_call} minutes before start",
            ephemeral=True,
        )
    except Exception as e:
        print(f"setbearping command failed: {e}")
        import traceback
        traceback.print_exc()
        await interaction.followup.send("❌ Could not update bear reminders. Check bot permissions/logs.", ephemeral=True)


@bot.tree.command(name="cancelbear")
@app_commands.describe(event_id="Bear event ID (shown in scheduled message footer)")
async def cancelbear_command(
    interaction: discord.Interaction,
    event_id: int
):
    """Cancel a scheduled bear event."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return
    
    if not has_command_permission(interaction.user):
        await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
        return
    
    config = load_config()
    guild_config = ensure_guild_config(config, interaction.guild.id)
    
    if not guild_config.get("installed"):
        await interaction.response.send_message("❌ Bot not installed.", ephemeral=True)
        return
    
    data = load_events()
    guild_data = ensure_guild_data(data, interaction.guild.id)
    
    target = None
    for ev in guild_data.get("events", []):
        if ev.get("type") in {"bear", "bear1", "bear2"} and ev.get("id") == event_id:
            target = ev
            break
    
    if not target:
        await interaction.response.send_message("❌ Bear event not found.", ephemeral=True)
        return
    
    await delete_event_message(interaction.guild, target, guild_config)
    guild_data["events"] = [e for e in guild_data["events"] if e.get("id") != event_id]
    save_events(data)
    
    await interaction.response.send_message(f"🗑️ Bear event #{event_id} cancelled.", ephemeral=True)


@bot.tree.command(name="editbear")
@app_commands.describe(
    event_id="Bear event ID (shown in scheduled message footer)",
    new_date="New date in YYYY-MM-DD format UTC",
    new_time="New time in HH:MM format UTC, 24h",
)
async def editbear_command(
    interaction: discord.Interaction,
    event_id: int,
    new_date: str,
    new_time: str,
):
    """Edit a scheduled bear event's date/time."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return

    if not has_command_permission(interaction.user):
        await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
        return

    config = load_config()
    guild_config = ensure_guild_config(config, interaction.guild.id)

    if not guild_config.get("installed"):
        await interaction.response.send_message("❌ Bot not installed. Run `/install` first.", ephemeral=True)
        return

    data = load_events()
    guild_data = ensure_guild_data(data, interaction.guild.id)

    target_event = None
    for ev in guild_data.get("events", []):
        if ev.get("type") in {"bear", "bear1", "bear2"} and ev.get("id") == event_id:
            target_event = ev
            break

    if not target_event:
        await interaction.response.send_message("❌ Bear event not found.", ephemeral=True)
        return

    original_start_time = target_event["start_time"]
    new_dt = parse_date_time_utc(new_date, new_time)
    if not new_dt:
        await interaction.response.send_message(
            "❌ Invalid date/time format. Use:\n"
            "• Date: YYYY-MM-DD (e.g., 2026-01-25)\n"
            "• Time: HH:MM (e.g., 14:30)\n"
            "All times are in UTC.",
            ephemeral=True,
        )
        return

    now = datetime.now(pytz.UTC)
    if new_dt <= now:
        await interaction.response.send_message("❌ Date/time must be in the future (UTC).", ephemeral=True)
        return

    target_event["start_time"] = new_dt.isoformat()

    channel = get_channel(interaction.guild, guild_config, "bear")
    if channel and target_event.get("message_id"):
        try:
            message = await channel.fetch_message(target_event["message_id"])
            ts = int(new_dt.timestamp())

            embed = discord.Embed(
                title=f"🐻 {target_event.get('name', 'Bear Trap')} Scheduled",
                description=f"Start: <t:{ts}:F> (<t:{ts}:R>)",
                color=discord.Color.green(),
            )
            embed.set_footer(text=f"Event ID: {event_id} • UTC • Discord will show your local time")

            await message.edit(embed=embed)
        except discord.NotFound:
            target_event["message_id"] = None
        except Exception as e:
            print(f"Error updating bear message: {e}")

    save_events(data)

    orig_dt = datetime.fromisoformat(original_start_time)
    await interaction.response.send_message(
        f"✅ Bear event #{event_id} updated:\n"
        f"• Time: <t:{int(orig_dt.timestamp())}:F> → <t:{int(new_dt.timestamp())}:F>",
        ephemeral=True,
    )


# ============================================================================
# ARENA COMMANDS
# ============================================================================

@bot.tree.command(name="setarenaping")
@app_commands.describe(
    event_reminder="Minutes before (Event Reminder, e.g., 60)",
    final_call="Minutes before (Final Call, e.g., 10)",
)
async def setarenaping_command(
    interaction: discord.Interaction,
    event_reminder: int = 60,
    final_call: int = 10,
):
    """Configure arena reminder times (arena opens daily at 00:00 UTC)."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return
    
    if not has_command_permission(interaction.user):
        await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
        return
    
    config = load_config()
    guild_config = ensure_guild_config(config, interaction.guild.id)
    
    if not guild_config.get("installed"):
        await interaction.response.send_message("❌ Bot not installed.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        data = load_events()
        guild_data = ensure_guild_data(data, interaction.guild.id)

        reminders = [event_reminder, final_call]
        guild_data["configs"]["arena"]["reminders"] = reminders

        now = datetime.now(pytz.UTC)
        for ev in guild_data.get("events", []):
            if ev.get("type") != "arena":
                continue
            try:
                start_dt = datetime.fromisoformat(ev["start_time"])
            except Exception:
                continue
            if start_dt >= now:
                ev["reminder_offsets"] = reminders

        save_events(data)

        # Update arena header to reflect new reminder times
        await ensure_channel_headers(interaction.guild, guild_data, guild_config, ["arena"])
        save_events(data)

        await interaction.followup.send(
            "✅ Arena reminders updated:\n"
            f"• Event Reminder: {event_reminder} minutes before 00:00 UTC\n"
            f"• Final Call: {final_call} minutes before 00:00 UTC",
            ephemeral=True,
        )
    except Exception as e:
        print(f"setarenaping command failed: {e}")
        import traceback
        traceback.print_exc()
        await interaction.followup.send("❌ Could not update arena reminders. Check bot permissions/logs.", ephemeral=True)


# ============================================================================
# EVENT COMMANDS
# ============================================================================

@bot.tree.command(name="addevent")
@app_commands.describe(
    event_name="Name of the event",
    date="Date in YYYY-MM-DD format (UTC)",
    time="Time in HH:MM format (UTC, 24h)"
)
@app_commands.choices(event_name=[app_commands.Choice(name=name, value=name) for name in SIMPLE_EVENT_TYPES])
async def addevent_command(
    interaction: discord.Interaction,
    event_name: app_commands.Choice[str],
    date: str,
    time: str,
):
    """Schedule a simple game event with one date/time."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return
    
    if not has_command_permission(interaction.user):
        await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
        return
    
    config = load_config()
    guild_config = ensure_guild_config(config, interaction.guild.id)
    
    if not guild_config.get("installed"):
        await interaction.response.send_message("❌ Bot not installed. Run `/install` first.", ephemeral=True)
        return
    
    start_dt = parse_date_time_utc(date, time)
    if not start_dt:
        await interaction.response.send_message(
            "❌ Invalid format. Use:\n"
            "• Date: YYYY-MM-DD (e.g., 2026-01-25)\n"
            "• Time: HH:MM (e.g., 14:30)\n"
            "All times are in UTC.",
            ephemeral=True
        )
        return
    
    now = datetime.now(pytz.UTC)
    if start_dt <= now:
        await interaction.response.send_message("❌ Dates/times must be in the future (UTC).", ephemeral=True)
        return
    
    channel = get_channel(interaction.guild, guild_config, "events")
    if not channel:
        await interaction.response.send_message("❌ Events channel not configured.", ephemeral=True)
        return
    
    data = load_events()
    guild_data = ensure_guild_data(data, interaction.guild.id)
    role_mention = get_notification_mention(interaction.guild, "event")
    reminder_offsets = get_reminder_offsets(guild_data, "event")

    eid = next_event_id(guild_data)
    ev = {
        "id": eid,
        "type": "event",
        "name": event_name.value,
        "start_time": start_dt.isoformat(),
        "channel_id": channel.id,
        "message_id": None,
        "reminder_offsets": reminder_offsets,
        "sent_offsets": [],
        "created_by": {"user_id": interaction.user.id, "username": str(interaction.user)},
        "created_at": now.isoformat(),
    }
    guild_data["events"].append(ev)
    ts = int(start_dt.timestamp())
    embed = discord.Embed(
        title="🏆 Event Scheduled",
        description=f"**{event_name.value}**\nStart: <t:{ts}:F> (<t:{ts}:R>)",
        color=discord.Color.gold(),
    )
    embed.set_footer(text=f"Event ID: {eid} • UTC • Discord will show your local time")
    sent_msg = await channel.send(content=role_mention if role_mention else None, embed=embed)
    ev["message_id"] = sent_msg.id
    save_events(data)

    await interaction.response.send_message(
        f"?� Event #{eid} scheduled for <t:{ts}:F> in {channel.mention}",
        ephemeral=True,
    )


@bot.tree.command(name="addeternity")
@app_commands.describe(
    date="Date in YYYY-MM-DD format (UTC). The event is always scheduled at 05:00 UTC."
)
async def addeternity_command(
    interaction: discord.Interaction,
    date: str,
):
    """Schedule Eternity's Reach on a specific date at 05:00 UTC."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return

    if not has_command_permission(interaction.user):
        await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
        return

    config = load_config()
    guild_config = ensure_guild_config(config, interaction.guild.id)

    if not guild_config.get("installed"):
        await interaction.response.send_message("❌ Bot not installed. Run `/install` first.", ephemeral=True)
        return

    start_dt = parse_date_time_utc(date, "05:00")
    if not start_dt:
        await interaction.response.send_message(
            "❌ Invalid date format. Use YYYY-MM-DD (example: 2026-01-25).\n"
            "The command always uses 05:00 UTC.",
            ephemeral=True,
        )
        return

    now = datetime.now(pytz.UTC)
    if start_dt <= now:
        await interaction.response.send_message("❌ Date must be in the future (UTC).", ephemeral=True)
        return

    channel = get_channel(interaction.guild, guild_config, "events")
    if not channel:
        await interaction.response.send_message("❌ Events channel not configured.", ephemeral=True)
        return

    data = load_events()
    guild_data = ensure_guild_data(data, interaction.guild.id)
    role_mention = get_notification_mention(interaction.guild, "event", "Eternity's Reach")
    reminder_offsets = get_reminder_offsets(guild_data, "event")

    eid = next_event_id(guild_data)
    ev = {
        "id": eid,
        "type": "event",
        "name": "Eternity's Reach",
        "start_time": start_dt.isoformat(),
        "channel_id": channel.id,
        "message_id": None,
        "reminder_offsets": reminder_offsets,
        "sent_offsets": [],
        "created_by": {"user_id": interaction.user.id, "username": str(interaction.user)},
        "created_at": now.isoformat(),
    }
    guild_data["events"].append(ev)

    ts = int(start_dt.timestamp())
    embed = discord.Embed(
        title="🏆 Eternity's Reach Scheduled",
        description=(
            f"**Eternity's Reach**\nStart: <t:{ts}:F> (<t:{ts}:R>)\n\n"
            "Fixed event time: 05:00 UTC"
        ),
        color=discord.Color.dark_teal(),
    )
    embed.set_footer(text=f"Event ID: {eid} • UTC • Discord will show your local time")
    sent_msg = await channel.send(content=role_mention if role_mention else None, embed=embed)
    ev["message_id"] = sent_msg.id
    save_events(data)

    await interaction.response.send_message(
        f"✅ Eternity's Reach #{eid} scheduled for <t:{ts}:F> (05:00 UTC) in {channel.mention}",
        ephemeral=True,
    )


@bot.tree.command(name="addeventlegions")
@app_commands.describe(
    event_name="Legion event name",
    legion1_date="Legion 1 date (YYYY-MM-DD UTC)",
    legion1_time="Legion 1 time (HH:MM UTC)",
    legion2_date="Legion 2 date (YYYY-MM-DD UTC)",
    legion2_time="Legion 2 time (HH:MM UTC)",
)
@app_commands.choices(event_name=[app_commands.Choice(name=name, value=name) for name in LEGION_EVENT_TYPES])
async def addeventlegions_command(
    interaction: discord.Interaction,
    event_name: app_commands.Choice[str],
    legion1_date: str,
    legion1_time: str,
    legion2_date: str,
    legion2_time: str,
):
    """Schedule Swordland/Tri Alliance with Legion 1 and Legion 2 times."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return

    if not has_command_permission(interaction.user):
        await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
        return

    config = load_config()
    guild_config = ensure_guild_config(config, interaction.guild.id)

    if not guild_config.get("installed"):
        await interaction.response.send_message("❌ Bot not installed. Run `/install` first.", ephemeral=True)
        return

    start_dt_legion1 = parse_date_time_utc(legion1_date, legion1_time)
    start_dt_legion2 = parse_date_time_utc(legion2_date, legion2_time)
    if not start_dt_legion1 or not start_dt_legion2:
        await interaction.response.send_message(
            "❌ Invalid format. Use YYYY-MM-DD and HH:MM (UTC) for both legions.",
            ephemeral=True,
        )
        return

    now = datetime.now(pytz.UTC)
    if start_dt_legion1 <= now or start_dt_legion2 <= now:
        await interaction.response.send_message("❌ Dates/times must be in the future (UTC).", ephemeral=True)
        return

    channel = get_channel(interaction.guild, guild_config, "events")
    if not channel:
        await interaction.response.send_message("❌ Events channel not configured.", ephemeral=True)
        return

    data = load_events()
    guild_data = ensure_guild_data(data, interaction.guild.id)
    events_created = []
    role_mention = get_notification_mention(interaction.guild, "event")
    reminder_offsets = get_reminder_offsets(guild_data, "event")

    base_name = event_name.value.split(" (Legion")[0]
    targets = [
        (f"{base_name} - Legion 1", start_dt_legion1),
        (f"{base_name} - Legion 2", start_dt_legion2),
    ]

    for name, dt in targets:
        eid = next_event_id(guild_data)
        ev = {
            "id": eid,
            "type": "event",
            "name": name,
            "start_time": dt.isoformat(),
            "channel_id": channel.id,
            "message_id": None,
            "reminder_offsets": reminder_offsets,
            "sent_offsets": [],
            "created_by": {"user_id": interaction.user.id, "username": str(interaction.user)},
            "created_at": now.isoformat(),
        }
        guild_data["events"].append(ev)
        ts = int(dt.timestamp())
        embed = discord.Embed(
            title="🏆 Event Scheduled",
            description=f"**{name}**\nStart: <t:{ts}:F> (<t:{ts}:R>)",
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"Event ID: {eid} • UTC • Discord will show your local time")
        sent_msg = await channel.send(content=role_mention if role_mention else None, embed=embed)
        ev["message_id"] = sent_msg.id
        events_created.append((eid, ts))

    save_events(data)

    await interaction.response.send_message(
        f"?� {base_name} scheduled:\n"
        f"• Legion 1 (ID {events_created[0][0]}): <t:{events_created[0][1]}:F>\n"
        f"• Legion 2 (ID {events_created[1][0]}): <t:{events_created[1][1]}:F>",
        ephemeral=True,
    )


@bot.tree.command(name="cancelevent")
@app_commands.describe(event_id="Event ID (shown in scheduled message footer)")
async def cancelevent_command(
    interaction: discord.Interaction,
    event_id: int
):
    """Cancel a scheduled event."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return
    
    if not has_command_permission(interaction.user):
        await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
        return
    
    config = load_config()
    guild_config = ensure_guild_config(config, interaction.guild.id)
    
    if not guild_config.get("installed"):
        await interaction.response.send_message("❌ Bot not installed.", ephemeral=True)
        return
    
    data = load_events()
    guild_data = ensure_guild_data(data, interaction.guild.id)
    
    target = None
    for ev in guild_data.get("events", []):
        if ev.get("type") == "event" and ev.get("id") == event_id:
            target = ev
            break
    
    if not target:
        await interaction.response.send_message("❌ Event not found.", ephemeral=True)
        return
    
    await delete_event_message(interaction.guild, target, guild_config)
    guild_data["events"] = [e for e in guild_data["events"] if e.get("id") != event_id]
    save_events(data)
    
    await interaction.response.send_message(f"🗑️ Event #{event_id} cancelled.", ephemeral=True)


@bot.tree.command(name="editevent")
@app_commands.describe(
    event_id="Event ID to edit (shown in scheduled message footer)",
    new_date="New date in YYYY-MM-DD format UTC",
    new_time="New time in HH:MM format UTC, 24h"
)
async def editevent_command(
    interaction: discord.Interaction,
    event_id: int,
    new_date: str,
    new_time: str
):
    """Edit a scheduled event's date/time. Use event ID to edit Legion 1 or Legion 2 separately."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return
    
    if not has_command_permission(interaction.user):
        await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
        return
    
    config = load_config()
    guild_config = ensure_guild_config(config, interaction.guild.id)
    
    if not guild_config.get("installed"):
        await interaction.response.send_message("❌ Bot not installed. Run `/install` first.", ephemeral=True)
        return
    
    data = load_events()
    guild_data = ensure_guild_data(data, interaction.guild.id)
    
    # Find the event to edit
    target_event = None
    for ev in guild_data.get("events", []):
        if ev.get("type") == "event" and ev.get("id") == event_id:
            target_event = ev
            break
    
    if not target_event:
        await interaction.response.send_message("❌ Event not found.", ephemeral=True)
        return
    
    # Store original values
    original_start_time = target_event["start_time"]
    
    # Parse original datetime
    original_dt = datetime.fromisoformat(original_start_time)
    
    # Parse new date and time
    new_dt = parse_date_time_utc(new_date, new_time)
    if not new_dt:
        await interaction.response.send_message(
            "❌ Invalid date/time format. Use:\n"
            "• Date: YYYY-MM-DD (e.g., 2026-01-25)\n"
            "• Time: HH:MM (e.g., 14:30)\n"
            "All times are in UTC.",
            ephemeral=True
        )
        return
    
    # Check that new time is in the future
    now = datetime.now(pytz.UTC)
    if new_dt <= now:
        await interaction.response.send_message("❌ Date/time must be in the future (UTC).", ephemeral=True)
        return
    
    target_event["start_time"] = new_dt.isoformat()
    
    # Update the message in Discord
    channel = get_channel(interaction.guild, guild_config, "events")
    if channel and target_event.get("message_id"):
        try:
            message = await channel.fetch_message(target_event["message_id"])
            start_dt = datetime.fromisoformat(target_event["start_time"])
            ts = int(start_dt.timestamp())
            
            embed = discord.Embed(
                title="🏆 Event Scheduled",
                description=f"**{target_event['name']}**\nStart: <t:{ts}:F> (<t:{ts}:R>)",
                color=discord.Color.gold(),
            )
            embed.set_footer(text=f"Event ID: {event_id} • UTC • Discord will show your local time")
            
            await message.edit(embed=embed)
        except discord.NotFound:
            # Message was deleted, clear the message_id
            target_event["message_id"] = None
        except Exception as e:
            print(f"Error updating event message: {e}")
    
    save_events(data)
    
    # Build response showing what changed
    orig_dt = datetime.fromisoformat(original_start_time)
    new_dt = datetime.fromisoformat(target_event["start_time"])
    
    await interaction.response.send_message(
        f"?� Event #{event_id} updated:\n"
        f"• Time: <t:{int(orig_dt.timestamp())}:F> → <t:{int(new_dt.timestamp())}:F>",
        ephemeral=True
    )


@bot.tree.command(name="seteventpings")
@app_commands.describe(
    event_reminder="Minutes before (Event Reminder, e.g., 60)",
    final_call="Minutes before (Final Call, e.g., 10)",
)
async def seteventpings_command(
    interaction: discord.Interaction,
    event_reminder: int = 60,
    final_call: int = 10,
):
    """Configure game event reminder times (in minutes before start)."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return
    
    if not has_command_permission(interaction.user):
        await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
        return
    
    config = load_config()
    guild_config = ensure_guild_config(config, interaction.guild.id)
    
    if not guild_config.get("installed"):
        await interaction.response.send_message("❌ Bot not installed.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        data = load_events()
        guild_data = ensure_guild_data(data, interaction.guild.id)

        reminders = sorted(set([event_reminder, final_call, 0]))
        guild_data["configs"]["event"]["reminders"] = reminders

        now = datetime.now(pytz.UTC)
        for ev in guild_data.get("events", []):
            if ev.get("type") != "event":
                continue
            try:
                start_dt = datetime.fromisoformat(ev["start_time"])
            except Exception:
                continue
            if start_dt >= now:
                ev["reminder_offsets"] = reminders

        save_events(data)

        # Update event header to reflect new reminder times
        await ensure_channel_headers(interaction.guild, guild_data, guild_config, ["event"])
        save_events(data)

        await interaction.followup.send(
            "✅ Event reminders updated:\n"
            f"• Event Reminder: {event_reminder} minutes before start\n"
            f"• Final Call: {final_call} minutes before start\n"
            "• Event Start: At the scheduled start time",
            ephemeral=True,
        )
    except Exception as e:
        print(f"seteventpings command failed: {e}")
        import traceback
        traceback.print_exc()
        await interaction.followup.send("❌ Could not update event reminders. Check bot permissions/logs.", ephemeral=True)


def normalize_embed_text(text: str) -> str:
    """Normalize text pasted with escaped newlines for Discord embeds."""
    normalized = text.replace("\\r\\n", "\n").replace("\\n", "\n")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def extract_docx_text(docx_bytes: bytes) -> str:
    """Extract styled plain text from a DOCX file preserving lists and spacing."""
    with zipfile.ZipFile(BytesIO(docx_bytes)) as archive:
        document_xml = archive.read("word/document.xml")

    root = ET.fromstring(document_xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    out_lines: list[str] = []
    prev_kind = ""

    for paragraph in root.findall(".//w:p", ns):
        parts: list[str] = []
        for node in paragraph.iter():
            local_name = node.tag.rsplit("}", 1)[-1]
            if local_name == "t":
                parts.append(node.text or "")
            elif local_name == "tab":
                parts.append("    ")
            elif local_name in {"br", "cr"}:
                parts.append("\n")

        line = "".join(parts).strip()

        paragraph_props = paragraph.find("w:pPr", ns)
        is_list = paragraph_props is not None and paragraph_props.find("w:numPr", ns) is not None

        style_name = ""
        if paragraph_props is not None:
            style_node = paragraph_props.find("w:pStyle", ns)
            if style_node is not None:
                style_name = style_node.attrib.get(f"{{{ns['w']}}}val", "")
        is_heading = style_name.lower().startswith("heading")

        if not line:
            if out_lines and out_lines[-1] != "":
                out_lines.append("")
            prev_kind = "blank"
            continue

        if is_heading:
            formatted = f"**{line}**"
            kind = "heading"
        elif is_list:
            if re.match(r"^[•\-\*]\s", line):
                formatted = line
            else:
                formatted = f"• {line}"
            kind = "list"
        else:
            formatted = line
            kind = "text"

        if out_lines and out_lines[-1] != "":
            if not (prev_kind == "list" and kind == "list"):
                out_lines.append("")

        out_lines.append(formatted)
        prev_kind = kind

    return "\n".join(out_lines).strip()


def split_embed_chunks(text: str, max_len: int = 3800) -> list[str]:
    """Split long text into chunks that fit Discord embed description limits."""
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current_lines: list[str] = []
    current_size = 0

    for line in text.split("\n"):
        line_size = len(line) + 1
        if current_lines and current_size + line_size > max_len:
            chunks.append("\n".join(current_lines).strip())
            current_lines = [line]
            current_size = line_size
        else:
            current_lines.append(line)
            current_size += line_size

    if current_lines:
        chunks.append("\n".join(current_lines).strip())

    return chunks


async def read_guide_attachment(file: discord.Attachment) -> str:
    """Read supported guide files and return normalized text."""
    filename = (file.filename or "").lower()

    if filename.endswith((".txt", ".md")):
        raw = await file.read()
        return normalize_embed_text(raw.decode("utf-8", errors="replace"))

    if filename.endswith(".docx"):
        raw = await file.read()
        return normalize_embed_text(extract_docx_text(raw))

    raise ValueError("Unsupported file. Use .txt, .md or .docx")


@bot.tree.command(name="embed")
@app_commands.describe(
    title="Embed title",
    content="Embed description/content",
    color="Hex color, e.g. #57F287 (optional)",
    channel="Target channel (optional, current channel by default)",
    image_url="Image URL (optional)",
    thumbnail_url="Thumbnail URL (optional)",
    footer="Footer text (optional)",
)
async def embed_command(
    interaction: discord.Interaction,
    title: str,
    content: str,
    color: str | None = None,
    channel: discord.TextChannel | None = None,
    image_url: str | None = None,
    thumbnail_url: str | None = None,
    footer: str | None = None,
):
    """Publish a formatted embed message."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return

    if not has_command_permission(interaction.user):
        await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
        return

    target_channel = channel or interaction.channel
    if not isinstance(target_channel, discord.TextChannel):
        await interaction.response.send_message("❌ Invalid target channel.", ephemeral=True)
        return

    content = normalize_embed_text(content)

    embed_color = discord.Color.blurple()
    if color:
        cleaned = color.strip().replace("#", "")
        if len(cleaned) != 6:
            await interaction.response.send_message("❌ Invalid color. Use HEX like `#57F287`.", ephemeral=True)
            return
        try:
            embed_color = discord.Color(int(cleaned, 16))
        except ValueError:
            await interaction.response.send_message("❌ Invalid color. Use HEX like `#57F287`.", ephemeral=True)
            return

    embed = discord.Embed(
        title=title,
        description=content,
        color=embed_color,
        timestamp=datetime.now(pytz.UTC),
    )

    if image_url:
        embed.set_image(url=image_url)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    if footer:
        embed.set_footer(text=footer)
    else:
        embed.set_footer(text="Kingshot Notifications")

    await target_channel.send(embed=embed)
    await interaction.response.send_message(
        f"?� Embed sent in {target_channel.mention}",
        ephemeral=True,
    )


@bot.tree.command(name="addguide")
@app_commands.describe(
    file="Guide file (.txt, .md, .docx)",
    title="Guide title",
    color="Hex color, e.g. #57F287 (optional)",
    channel="Target channel (optional, current channel by default)",
)
async def addguide_command(
    interaction: discord.Interaction,
    file: discord.Attachment,
    title: str,
    color: str | None = None,
    channel: discord.TextChannel | None = None,
):
    """Create one or more embeds from an attached guide document."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return

    if not has_command_permission(interaction.user):
        await interaction.response.send_message("❌ You need Administrator or the configured /setadmin role to use this command.", ephemeral=True)
        return

    target_channel = channel or interaction.channel
    if not isinstance(target_channel, discord.TextChannel):
        await interaction.response.send_message("❌ Invalid target channel.", ephemeral=True)
        return

    embed_color = discord.Color.blurple()
    if color:
        cleaned = color.strip().replace("#", "")
        if len(cleaned) != 6:
            await interaction.response.send_message("❌ Invalid color. Use HEX like `#57F287`.", ephemeral=True)
            return
        try:
            embed_color = discord.Color(int(cleaned, 16))
        except ValueError:
            await interaction.response.send_message("❌ Invalid color. Use HEX like `#57F287`.", ephemeral=True)
            return

    await interaction.response.defer(ephemeral=True)

    try:
        guide_text = await read_guide_attachment(file)
    except ValueError as parse_error:
        await interaction.followup.send(f"❌ {parse_error}", ephemeral=True)
        return
    except Exception as parse_error:
        await interaction.followup.send(f"❌ Failed to read file: {parse_error}", ephemeral=True)
        return

    if not guide_text:
        await interaction.followup.send("❌ The file is empty.", ephemeral=True)
        return

    chunks = split_embed_chunks(guide_text)
    for index, chunk in enumerate(chunks, start=1):
        chunk_title = title if index == 1 else f"{title} (Part {index})"
        embed = discord.Embed(
            title=chunk_title,
            description=chunk,
            color=embed_color,
            timestamp=datetime.now(pytz.UTC),
        )
        await target_channel.send(embed=embed)

    await interaction.followup.send(
        f"?� Guide published in {target_channel.mention} ({len(chunks)} embed message(s)).",
        ephemeral=True,
    )


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Main function to start the bot."""
    print("\n🔐 Checking authentication...")
    if not DISCORD_TOKEN:
        print('❌ ERROR: Token not found')
        return
    
    print("?� Token validated")
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



