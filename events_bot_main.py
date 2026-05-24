"""Kingshot Events Bot - Event scheduling and notifications."""

import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
from pathlib import Path
import pytz

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('EVENTS_BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', 0))

print("=" * 60)
print("🎯 KINGSHOT EVENTS BOT STARTING...")
print("=" * 60)
print(f"✓ Owner ID: {OWNER_ID}")
print(f"✓ Token loaded: {'Yes' if DISCORD_TOKEN else 'No'}")

# Initialize bot with required intents
intents = discord.Intents.none()
intents.guilds = True
intents.members = True
intents.reactions = True
bot = commands.Bot(command_prefix='!event', intents=intents)
bot.owner_id = OWNER_ID

# Data files
EVENTS_FILE = Path("data/events_data.json")
EVENTS_FILE.parent.mkdir(exist_ok=True)

# Configuration
REACTION_MESSAGE_VERSION = 1
HEADER_VERSION = 1

CHANNEL_NAMES = {
    "bear": "🐻｜bear",
    "arena": "⚔️｜arena",
    "events": "🏆｜events",
    "reaction": "📜｜notification-settings",
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

# Data management
def load_event_data():
    """Load events data from JSON."""
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
    """Save events data to JSON."""
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
    """Get next event ID for guild."""
    if not guild_data.get("events"):
        return 1
    return max(ev.get("id", 0) for ev in guild_data["events"]) + 1


def find_channel_by_name(guild: discord.Guild, target: str):
    """Find channel by name."""
    for ch in guild.text_channels:
        if ch.name == target:
            return ch
    return None


def get_role_for_key(guild: discord.Guild, key: str):
    """Get role by key."""
    role_name = ROLE_NAMES.get(key)
    if not role_name:
        return None
    return discord.utils.get(guild.roles, name=role_name)


def get_event_channel(guild: discord.Guild, event_type: str):
    """Get channel for event type."""
    if event_type == "bear":
        name = CHANNEL_NAMES["bear"]
    elif event_type == "arena":
        name = CHANNEL_NAMES["arena"]
    else:
        name = CHANNEL_NAMES["events"]
    return find_channel_by_name(guild, name)


def get_reminder_offsets(guild_data: dict, event_type: str) -> list[int]:
    """Get reminder offsets for event type."""
    configs = guild_data.get("configs", {})
    if event_type in configs:
        return configs[event_type].get("reminders", [60, 10, 0])
    return [60, 10, 0]


def parse_date_time_utc(date_str: str, time_str: str):
    """Parse date (YYYY-MM-DD) and time (HH:MM) to UTC datetime."""
    try:
        y, m, d = [int(x) for x in date_str.split("-")]
        hh, mm = [int(x) for x in time_str.split(":")]
        dt = datetime(y, m, d, hh, mm, tzinfo=pytz.UTC)
        return dt
    except Exception:
        return None


def role_key_from_emoji(emoji: str):
    """Get role key from emoji."""
    for key, emj in REACTION_EMOJIS.items():
        if emoji == emj:
            return key
    return None


def build_reaction_embed() -> discord.Embed:
    """Build reaction role selection embed."""
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


def build_channel_header_embed(event_type: str) -> discord.Embed:
    """Build channel header embed."""
    title = "🏷️ Event Notifications"
    description = "This channel posts upcoming Event notifications!"
    embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
    embed.add_field(name="⏱️ Event Reminder", value="60 minutes before start", inline=False)
    embed.add_field(name="🔔 Final Call", value="10 minutes before start", inline=False)
    embed.add_field(name="🎯 Event Start", value="When the event begins", inline=False)
    if event_type == "bear":
        embed.add_field(name="🗓️ Bear Commands", value="/setbeartime • /setbearping • /cancelbear • /listbears", inline=False)
    elif event_type == "arena":
        embed.add_field(name="⚔️ Arena Commands", value="/setarenaping", inline=False)
    else:
        embed.add_field(name="🏆 Event Commands", value="/addevent • /cancelevent • /listevent • /seteventpings", inline=False)
    embed.add_field(name="⚙️ Settings", value="Use commands to adjust reminders (UTC)", inline=False)
    embed.set_footer(text="👑 Kingshot Bot • Event Alerts • UTC")
    return embed


def ensure_arena_event_entry(guild_data: dict) -> bool:
    """Ensure arena event for next midnight UTC."""
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


async def send_event_ping(guild: discord.Guild, event: dict, offset: int):
    """Send event reminder ping."""
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
    """Delete event message after it expires."""
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


async def ensure_reaction_roles_for_guild(guild: discord.Guild):
    """Ensure reaction role message exists and is up to date."""
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
    """Ensure channel header messages are up to date."""
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


# Background task for event notifications
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
    
    guild_count = len(bot.guilds)
    print(f'\n📊 Connected to {guild_count} server(s):')
    for guild in bot.guilds:
        print(f'  - {guild.name} (ID: {guild.id})')
    
    # Start event notification checker
    if not check_event_notifications.is_running():
        check_event_notifications.start()
        print('\n🔔 Event notification checker started')
    
    # Setup reaction roles and headers
    for guild in bot.guilds:
        try:
            await ensure_reaction_roles_for_guild(guild)
            await ensure_channel_headers(guild)
        except Exception as e:
            print(f"Error ensuring setup for guild {guild.id}: {e}")
    
    # Sync commands
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
    """Handle reaction role additions."""
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
    """Handle reaction role removals."""
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


# Commands
@bot.tree.command(name="setbeartime")
@app_commands.describe(
    date="Fecha en formato YYYY-MM-DD (UTC)",
    time="Hora en formato HH:MM (UTC)"
)
async def setbeartime_command(
    interaction: discord.Interaction,
    date: str,
    time: str
):
    """Programar un evento de oso en UTC."""
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
    channel = get_event_channel(interaction.guild, "bear")
    if not channel:
        await interaction.response.send_message("❌ No se encontró el canal 🐻｜bear.", ephemeral=True)
        return
    data = load_event_data()
    guild_data = ensure_guild_events(data, interaction.guild.id)
    event_id = next_event_id(guild_data)
    event = {
        "id": event_id,
        "type": "bear",
        "name": "Bear Attack",
        "start_time": start_dt.isoformat(),
        "channel_id": channel.id,
        "message_id": None,
        "reminder_offsets": get_reminder_offsets(guild_data, "bear"),
        "sent_offsets": [],
        "created_by": {"user_id": interaction.user.id, "username": str(interaction.user)},
        "created_at": now.isoformat(),
    }
    guild_data["events"].append(event)
    save_event_data(data)
    role = get_role_for_key(interaction.guild, "bear")
    role_mention = role.mention if role else ""
    ts = int(start_dt.timestamp())
    embed = discord.Embed(
        title="🐻 Bear Scheduled",
        description=f"Start: <t:{ts}:F> (<t:{ts}:R>)",
        color=discord.Color.green(),
    )
    embed.set_footer(text="UTC • Discord mostrará tu hora local")
    sent = await channel.send(content=role_mention if role_mention else None, embed=embed)
    event["message_id"] = sent.id
    save_event_data(data)
    await interaction.response.send_message(
        f"✅ Oso programado #{event_id} para <t:{ts}:F> en {channel.mention}",
        ephemeral=True,
    )


@bot.tree.command(name="setbearping")
@app_commands.describe(
    reminder1="Minutos antes (ej: 60)",
    reminder2="Minutos antes (ej: 10)",
    reminder3="Minutos antes (ej: 0)",
)
async def setbearping_command(
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


@bot.tree.command(name="cancelbear")
@app_commands.describe(event_id="ID del evento de oso")
async def cancelbear_command(
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


@bot.tree.command(name="listbears")
async def listbears_command(interaction: discord.Interaction):
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


@bot.tree.command(name="setarenaping")
@app_commands.describe(
    reminder1="Minutos antes (ej: 60)",
    reminder2="Minutos antes (ej: 10)",
    reminder3="Minutos antes (ej: 0)",
)
async def setarenaping_command(
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


@bot.tree.command(name="addevent")
@app_commands.describe(
    event_name="Nombre del evento",
    date="Fecha en formato YYYY-MM-DD (UTC)",
    time="Hora en formato HH:MM (UTC)"
)
@app_commands.choices(event_name=[app_commands.Choice(name=name, value=name) for name in EVENT_NAME_CHOICES])
async def addevent_command(
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


@bot.tree.command(name="cancelevent")
@app_commands.describe(event_id="ID del evento")
async def cancelevent_command(
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


@bot.tree.command(name="listevent")
async def listevent_command(interaction: discord.Interaction):
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


@bot.tree.command(name="seteventpings")
@app_commands.describe(
    reminder1="Minutos antes (ej: 60)",
    reminder2="Minutos antes (ej: 10)",
    reminder3="Minutos antes (ej: 0)",
)
async def seteventpings_command(
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


async def main():
    """Main function to start the bot."""
    print("\n🔐 Checking authentication...")
    if not DISCORD_TOKEN:
        print('❌ ERROR: EVENTS_BOT_TOKEN not found in .env file')
        print('Please add: EVENTS_BOT_TOKEN=your_token_here to .env')
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
