"""Discord <-> Telegram bridge bot.

This service runs as an independent process and mirrors selected channels
between Discord and Telegram in near real time.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
from pathlib import Path
from typing import Any, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters


load_dotenv()

DISCORD_TOKEN = os.getenv("BRIDGE_DISCORD_TOKEN") or os.getenv("DISCORD_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = DATA_DIR / "telegram_bridge_config.json"
MAP_FILE = DATA_DIR / "telegram_bridge_message_map.json"

MAX_MAPPINGS = 8000
DEFAULT_BACKFILL_LIMIT = 100


class BridgeStorage:
    """JSON storage for bridge config and mirrored message ids."""

    def __init__(self, config_file: Path, map_file: Path) -> None:
        self.config_file = config_file
        self.map_file = map_file
        self.config: dict[str, Any] = self._load_json(
            config_file,
            {
                "guilds": {}
            },
        )
        self.message_map: dict[str, Any] = self._load_json(
            map_file,
            {
                "discord_to_telegram": {},
                "telegram_to_discord": {},
                "discord_edit_targets": {},
            },
        )
        self._normalize()

    def _load_json(self, path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            return fallback
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return fallback

    def _atomic_write(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        tmp.replace(path)

    def _normalize(self) -> None:
        self.config.setdefault("guilds", {})
        self.message_map.setdefault("discord_to_telegram", {})
        self.message_map.setdefault("telegram_to_discord", {})
        self.message_map.setdefault("discord_edit_targets", {})

    def save_config(self) -> None:
        self._atomic_write(self.config_file, self.config)

    def save_map(self) -> None:
        self._atomic_write(self.map_file, self.message_map)

    def ensure_guild(self, guild_id: int) -> dict[str, Any]:
        gid = str(guild_id)
        guilds = self.config["guilds"]
        if gid not in guilds:
            guilds[gid] = {"bridges": {}}
        guilds[gid].setdefault("bridges", {})
        return guilds[gid]

    def get_bridge_for_discord(self, guild_id: int, channel_id: int) -> Optional[dict[str, Any]]:
        guild = self.ensure_guild(guild_id)
        return guild["bridges"].get(str(channel_id))

    def set_bridge(
        self,
        guild_id: int,
        channel_id: int,
        telegram_chat_id: int,
        telegram_thread_id: Optional[int],
    ) -> dict[str, Any]:
        guild = self.ensure_guild(guild_id)
        bridges = guild["bridges"]
        record = bridges.get(str(channel_id), {})
        record.update(
            {
                "discord_channel_id": int(channel_id),
                "telegram_chat_id": int(telegram_chat_id),
                "telegram_thread_id": int(telegram_thread_id) if telegram_thread_id is not None else None,
                "enabled": True,
                "features": {
                    "text": True,
                    "attachments": True,
                    "replies": True,
                    "edits": True,
                    "deletes": True,
                },
                "backfill_limit": int(record.get("backfill_limit", DEFAULT_BACKFILL_LIMIT)),
            }
        )
        bridges[str(channel_id)] = record
        self.save_config()
        return record

    def remove_bridge(self, guild_id: int, channel_id: int) -> bool:
        guild = self.ensure_guild(guild_id)
        bridges = guild["bridges"]
        removed = bridges.pop(str(channel_id), None) is not None
        if removed:
            self.save_config()
        return removed

    def find_bridge_by_telegram(self, chat_id: int, thread_id: Optional[int]) -> Optional[dict[str, Any]]:
        for guild in self.config.get("guilds", {}).values():
            for bridge in guild.get("bridges", {}).values():
                if not bridge.get("enabled", True):
                    continue
                if int(bridge.get("telegram_chat_id")) != int(chat_id):
                    continue
                configured_thread = bridge.get("telegram_thread_id")
                if configured_thread is None and thread_id is None:
                    return bridge
                if configured_thread is not None and thread_id is not None and int(configured_thread) == int(thread_id):
                    return bridge
        return None

    def set_enabled(self, guild_id: int, channel_id: int, enabled: bool) -> bool:
        bridge = self.get_bridge_for_discord(guild_id, channel_id)
        if not bridge:
            return False
        bridge["enabled"] = enabled
        self.save_config()
        return True

    def set_backfill_limit(self, guild_id: int, channel_id: int, limit: int) -> bool:
        bridge = self.get_bridge_for_discord(guild_id, channel_id)
        if not bridge:
            return False
        bridge["backfill_limit"] = max(1, min(limit, 500))
        self.save_config()
        return True

    def list_bridges(self, guild_id: int) -> list[dict[str, Any]]:
        guild = self.ensure_guild(guild_id)
        return list(guild.get("bridges", {}).values())

    def set_message_mapping(
        self,
        discord_message_id: int,
        discord_channel_id: int,
        guild_id: int,
        telegram_chat_id: int,
        telegram_message_ids: list[int],
    ) -> None:
        d_key = str(discord_message_id)
        self.message_map["discord_to_telegram"][d_key] = {
            "guild_id": int(guild_id),
            "discord_channel_id": int(discord_channel_id),
            "telegram_chat_id": int(telegram_chat_id),
            "telegram_message_ids": [int(x) for x in telegram_message_ids],
        }
        if telegram_message_ids:
            self.message_map["discord_edit_targets"][d_key] = int(telegram_message_ids[0])
        for telegram_message_id in telegram_message_ids:
            t_key = self.telegram_key(telegram_chat_id, telegram_message_id)
            self.message_map["telegram_to_discord"][t_key] = int(discord_message_id)

        self._trim_maps()
        self.save_map()

    def telegram_key(self, chat_id: int, message_id: int) -> str:
        return f"{chat_id}:{message_id}"

    def get_telegram_for_discord(self, discord_message_id: int) -> Optional[dict[str, Any]]:
        return self.message_map["discord_to_telegram"].get(str(discord_message_id))

    def get_discord_for_telegram(self, chat_id: int, message_id: int) -> Optional[int]:
        return self.message_map["telegram_to_discord"].get(self.telegram_key(chat_id, message_id))

    def remove_by_discord(self, discord_message_id: int) -> Optional[dict[str, Any]]:
        d_key = str(discord_message_id)
        mapping = self.message_map["discord_to_telegram"].pop(d_key, None)
        self.message_map["discord_edit_targets"].pop(d_key, None)
        if mapping:
            chat_id = int(mapping["telegram_chat_id"])
            for t_id in mapping.get("telegram_message_ids", []):
                self.message_map["telegram_to_discord"].pop(self.telegram_key(chat_id, int(t_id)), None)
            self.save_map()
        return mapping

    def _trim_maps(self) -> None:
        d_map = self.message_map["discord_to_telegram"]
        if len(d_map) <= MAX_MAPPINGS:
            return
        oldest_keys = list(d_map.keys())[: len(d_map) - MAX_MAPPINGS]
        for key in oldest_keys:
            mapping = d_map.pop(key, None)
            self.message_map["discord_edit_targets"].pop(key, None)
            if not mapping:
                continue
            chat_id = int(mapping["telegram_chat_id"])
            for t_id in mapping.get("telegram_message_ids", []):
                self.message_map["telegram_to_discord"].pop(self.telegram_key(chat_id, int(t_id)), None)


class DiscordTelegramBridge(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True
        intents.message_content = True

        super().__init__(command_prefix="/", intents=intents)

        self.owner_id = OWNER_ID
        self.storage = BridgeStorage(CONFIG_FILE, MAP_FILE)
        self._did_guild_sync = False
        self.telegram: Application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

        self.telegram.add_handler(CommandHandler("start", self.telegram_start))
        self.telegram.add_handler(CommandHandler("bridge_link", self.telegram_bridge_link))
        self.telegram.add_handler(MessageHandler(filters.UpdateType.MESSAGE & ~filters.COMMAND, self.on_telegram_message))
        self.telegram.add_handler(
            MessageHandler(filters.UpdateType.EDITED_MESSAGE & ~filters.COMMAND, self.on_telegram_edited_message)
        )

    async def setup_hook(self) -> None:
        try:
            await self.telegram.initialize()
            await self.telegram.start()
            if self.telegram.updater:
                await self.telegram.updater.start_polling(drop_pending_updates=True)
            print("[✅] Telegram connected successfully")
        except Exception as e:
            print(f"[⚠️ ] Error connecting to Telegram: {e}")
            print(f"[⚠️ ] Discord will continue running without Telegram")

        # Keep a global sync for DM/global availability.
        await self.tree.sync()

    async def close(self) -> None:
        try:
            if self.telegram.updater:
                await self.telegram.updater.stop()
            await self.telegram.stop()
        except Exception as e:
            print(f"[⚠️ ] Error closing Telegram: {e}")
        await self.telegram.shutdown()
        await super().close()

    async def on_ready(self) -> None:
        print(f"Discord connected as {self.user} ({self.user.id})")
        bot_user = await self.telegram.bot.get_me()
        print(f"Telegram connected as @{bot_user.username} ({bot_user.id})")

        # Ensure commands are available immediately in joined guilds.
        if not self._did_guild_sync:
            for guild in self.guilds:
                try:
                    synced = await self.tree.sync(guild=guild)
                    print(f"[Bridge] Synced {len(synced)} commands in guild {guild.name} ({guild.id})")
                except Exception as exc:
                    print(f"[Bridge] Guild sync failed for {guild.id}: {exc}")
            self._did_guild_sync = True

    async def is_admin(self, interaction: discord.Interaction) -> bool:
        if not interaction.user:
            return False
        if interaction.user.id == self.owner_id:
            return True
        if isinstance(interaction.user, discord.Member):
            return interaction.user.guild_permissions.administrator
        return False

    async def telegram_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat:
            msg = (
                "Bridge active. Share this chat_id when configuring in Discord.\n"
                f"chat_id: {update.effective_chat.id}"
            )
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

    async def telegram_bridge_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Escribe /bridge_link en un tema de Telegram para obtener los datos de vinculación."""
        if not update.effective_message or not update.effective_chat:
            return
        chat_id = update.effective_chat.id
        thread_id = update.effective_message.message_thread_id

        if thread_id:
            cmd = f"/bridge_add channel:#CHANNEL telegram_chat_id:{chat_id} telegram_thread_id:{thread_id}"
            msg = (
                f"✅ Topic detected:\n\n"
                f"📋 Run this in Discord (replace #CHANNEL with the desired channel):\n\n"
                f"`{cmd}`\n\n"
                f"• chat_id: `{chat_id}`\n"
                f"• thread_id: `{thread_id}`"
            )
        else:
            cmd = f"/bridge_add channel:#CHANNEL telegram_chat_id:{chat_id}"
            msg = (
                f"✅ Group detected (no specific topic):\n\n"
                f"📋 Run this in Discord (replace #CHANNEL with the desired channel):\n\n"
                f"`{cmd}`\n\n"
                f"• chat_id: `{chat_id}`\n"
                f"⚠️ This message is not inside a topic. "
                f"If you want to link a specific topic, run /bridge_link inside that topic."
            )
        await update.effective_message.reply_text(msg)

    def build_discord_to_telegram_text(self, message: discord.Message) -> str:
        channel_name = message.channel.name if isinstance(message.channel, discord.TextChannel) else "channel"
        base = f"[Discord] {message.author.display_name} in #{channel_name}"
        body = (message.content or "").strip()

        reply_block = ""
        if message.reference and message.reference.resolved and isinstance(message.reference.resolved, discord.Message):
            ref = message.reference.resolved
            quoted = (ref.content or "").strip()
            if quoted:
                if len(quoted) > 250:
                    quoted = quoted[:247] + "..."
                reply_block = f"\n\nReplying to {ref.author.display_name}: {quoted}"
            else:
                reply_block = f"\n\nReplying to {ref.author.display_name}"

        text = f"{base}\n{body}{reply_block}".strip()
        if len(text) > 4000:
            text = text[:3997] + "..."
        return text

    def build_telegram_to_discord_text(self, message: Any) -> str:
        sender = message.from_user.full_name if message.from_user else "Telegram User"
        body = (message.text or message.caption or "").strip()

        reply_block = ""
        # Only treat as reply if there is actual quoted content (avoids false positives from thread topic messages)
        if message.reply_to_message:
            quoted = (message.reply_to_message.text or message.reply_to_message.caption or "").strip()
            if quoted:
                if len(quoted) > 250:
                    quoted = quoted[:247] + "..."
                reply_sender = message.reply_to_message.from_user.full_name if message.reply_to_message.from_user else ""
                reply_block = f"\n\nReplying to {reply_sender}: {quoted}" if reply_sender else f"\n\nReplying to: {quoted}"

        text = f"[Telegram] {sender}\n{body}{reply_block}".strip()
        if len(text) > 1900:
            text = text[:1897] + "..."
        return text

    async def relay_discord_to_telegram(self, message: discord.Message, bridge: dict[str, Any]) -> None:
        text = self.build_discord_to_telegram_text(message)
        chat_id = int(bridge["telegram_chat_id"])
        thread_id = bridge.get("telegram_thread_id")
        thread_id = int(thread_id) if thread_id is not None else None

        sent_ids: list[int] = []

        try:
            text_msg = await self.telegram.bot.send_message(chat_id=chat_id, text=text, message_thread_id=thread_id)
            sent_ids.append(text_msg.message_id)

            if bridge["features"].get("attachments", True):
                for att in message.attachments:
                    if att.content_type and att.content_type.startswith("image/"):
                        sent = await self.telegram.bot.send_photo(
                            chat_id=chat_id,
                            photo=att.url,
                            message_thread_id=thread_id,
                        )
                    else:
                        sent = await self.telegram.bot.send_document(
                            chat_id=chat_id,
                            document=att.url,
                            message_thread_id=thread_id,
                        )
                    sent_ids.append(sent.message_id)

            self.storage.set_message_mapping(
                discord_message_id=message.id,
                discord_channel_id=message.channel.id,
                guild_id=message.guild.id if message.guild else 0,
                telegram_chat_id=chat_id,
                telegram_message_ids=sent_ids,
            )
        except TelegramError as exc:
            print(f"[Bridge] Discord->Telegram failed: {exc}")

    async def relay_telegram_to_discord(self, telegram_message: Any, bridge: dict[str, Any]) -> Optional[int]:
        channel_id = int(bridge["discord_channel_id"])
        channel = self.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return None

        text = self.build_telegram_to_discord_text(telegram_message)
        reference: Optional[discord.MessageReference] = None

        if bridge["features"].get("replies", True) and telegram_message.reply_to_message:
            source_chat = telegram_message.chat_id
            source_reply_id = telegram_message.reply_to_message.message_id
            discord_reply_id = self.storage.get_discord_for_telegram(source_chat, source_reply_id)
            if discord_reply_id:
                try:
                    reply_message = await channel.fetch_message(int(discord_reply_id))
                    reference = reply_message.to_reference(fail_if_not_exists=False)
                except Exception:
                    reference = None

        sent = await channel.send(content=text, reference=reference)

        if bridge["features"].get("attachments", True):
            files: list[discord.File] = []
            if telegram_message.photo:
                largest = telegram_message.photo[-1]
                tg_file = await largest.get_file()
                payload = io.BytesIO(await tg_file.download_as_bytearray())
                payload.seek(0)
                files.append(discord.File(payload, filename=f"telegram_photo_{telegram_message.message_id}.jpg"))

            if telegram_message.document:
                tg_file = await telegram_message.document.get_file()
                payload = io.BytesIO(await tg_file.download_as_bytearray())
                payload.seek(0)
                doc_name = telegram_message.document.file_name or f"telegram_document_{telegram_message.message_id}"
                files.append(discord.File(payload, filename=doc_name))

            if files:
                await channel.send(files=files)

        self.storage.set_message_mapping(
            discord_message_id=sent.id,
            discord_channel_id=channel_id,
            guild_id=channel.guild.id,
            telegram_chat_id=telegram_message.chat_id,
            telegram_message_ids=[telegram_message.message_id],
        )
        return sent.id

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user or not message.guild:
            await self.process_commands(message)
            return

        bridge = self.storage.get_bridge_for_discord(message.guild.id, message.channel.id)
        if bridge and bridge.get("enabled", True):
            if bridge["features"].get("text", True) or (bridge["features"].get("attachments", True) and message.attachments):
                await self.relay_discord_to_telegram(message, bridge)

        await self.process_commands(message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.author == self.user or not after.guild:
            return

        if before.content == after.content:
            return

        bridge = self.storage.get_bridge_for_discord(after.guild.id, after.channel.id)
        if not bridge or not bridge.get("enabled", True):
            return
        if not bridge["features"].get("edits", True):
            return

        mapping = self.storage.get_telegram_for_discord(after.id)
        if not mapping:
            return

        target_message_id = self.storage.message_map.get("discord_edit_targets", {}).get(str(after.id))
        if not target_message_id:
            return

        text = self.build_discord_to_telegram_text(after)
        try:
            await self.telegram.bot.edit_message_text(
                chat_id=int(mapping["telegram_chat_id"]),
                message_id=int(target_message_id),
                text=text,
            )
        except TelegramError as exc:
            print(f"[Bridge] Discord edit mirror failed: {exc}")

    async def on_message_delete(self, message: discord.Message) -> None:
        if not message.guild:
            return

        bridge = self.storage.get_bridge_for_discord(message.guild.id, message.channel.id)
        if not bridge or not bridge.get("enabled", True):
            return
        if not bridge["features"].get("deletes", True):
            return

        mapping = self.storage.remove_by_discord(message.id)
        if not mapping:
            return

        chat_id = int(mapping["telegram_chat_id"])
        for telegram_message_id in mapping.get("telegram_message_ids", []):
            try:
                await self.telegram.bot.delete_message(chat_id=chat_id, message_id=int(telegram_message_id))
            except TelegramError:
                pass

    async def on_telegram_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if not message:
            return

        me = await context.bot.get_me()
        if message.from_user and message.from_user.id == me.id:
            return

        chat_id = message.chat_id
        thread_id = getattr(message, "message_thread_id", None)
        bridge = self.storage.find_bridge_by_telegram(chat_id, thread_id)
        if not bridge:
            return

        try:
            await self.relay_telegram_to_discord(message, bridge)
        except Exception as exc:
            print(f"[Bridge] Telegram->Discord failed: {exc}")

    async def on_telegram_edited_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.edited_message
        if not message:
            return

        bridge = self.storage.find_bridge_by_telegram(message.chat_id, getattr(message, "message_thread_id", None))
        if not bridge or not bridge.get("features", {}).get("edits", True):
            return

        discord_message_id = self.storage.get_discord_for_telegram(message.chat_id, message.message_id)
        if not discord_message_id:
            return

        channel = self.get_channel(int(bridge["discord_channel_id"]))
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            d_msg = await channel.fetch_message(int(discord_message_id))
            await d_msg.edit(content=self.build_telegram_to_discord_text(message))
        except Exception as exc:
            print(f"[Bridge] Telegram edit mirror failed: {exc}")


bot = DiscordTelegramBridge()


@bot.tree.command(name="bridge_add", description="Link a Discord channel with a Telegram chat")
@app_commands.describe(
    channel="Discord channel to link",
    telegram_chat_id="Telegram chat ID (e.g. -100123456789)",
    telegram_thread_id="Telegram topic/thread ID (optional)",
)
async def bridge_add(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    telegram_chat_id: str,
    telegram_thread_id: Optional[str] = None,
) -> None:
    if not interaction.guild:
        await interaction.response.send_message("This command only works inside a server.", ephemeral=True)
        return
    if not await bot.is_admin(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    try:
        chat_id = int(telegram_chat_id.strip())
    except ValueError:
        await interaction.response.send_message("Invalid telegram_chat_id.", ephemeral=True)
        return

    parsed_thread: Optional[int] = None
    if telegram_thread_id:
        try:
            parsed_thread = int(telegram_thread_id.strip())
        except ValueError:
            await interaction.response.send_message("Invalid telegram_thread_id.", ephemeral=True)
            return

    bot.storage.set_bridge(interaction.guild.id, channel.id, chat_id, parsed_thread)
    await interaction.response.send_message(
        f"Bridge active: {channel.mention} -> chat {chat_id}"
        + (f" (thread {parsed_thread})" if parsed_thread is not None else ""),
        ephemeral=True,
    )


@bot.tree.command(name="bridge_remove", description="Remove the bridge link from a channel")
@app_commands.describe(channel="Discord channel")
async def bridge_remove(interaction: discord.Interaction, channel: discord.TextChannel) -> None:
    if not interaction.guild:
        await interaction.response.send_message("This command only works inside a server.", ephemeral=True)
        return
    if not await bot.is_admin(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    removed = bot.storage.remove_bridge(interaction.guild.id, channel.id)
    if not removed:
        await interaction.response.send_message("That channel was not linked.", ephemeral=True)
        return

    await interaction.response.send_message(f"Bridge removed for {channel.mention}.", ephemeral=True)


@bot.tree.command(name="bridge_enable", description="Enable sync for a channel")
@app_commands.describe(channel="Discord channel")
async def bridge_enable(interaction: discord.Interaction, channel: discord.TextChannel) -> None:
    if not interaction.guild:
        await interaction.response.send_message("This command only works inside a server.", ephemeral=True)
        return
    if not await bot.is_admin(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    ok = bot.storage.set_enabled(interaction.guild.id, channel.id, True)
    if not ok:
        await interaction.response.send_message("That channel is not linked.", ephemeral=True)
        return

    await interaction.response.send_message(f"Bridge enabled for {channel.mention}.", ephemeral=True)


@bot.tree.command(name="bridge_disable", description="Disable sync for a channel")
@app_commands.describe(channel="Discord channel")
async def bridge_disable(interaction: discord.Interaction, channel: discord.TextChannel) -> None:
    if not interaction.guild:
        await interaction.response.send_message("This command only works inside a server.", ephemeral=True)
        return
    if not await bot.is_admin(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    ok = bot.storage.set_enabled(interaction.guild.id, channel.id, False)
    if not ok:
        await interaction.response.send_message("That channel is not linked.", ephemeral=True)
        return

    await interaction.response.send_message(f"Bridge disabled for {channel.mention}.", ephemeral=True)


@bot.tree.command(name="bridge_list", description="Show all linked channels")
async def bridge_list(interaction: discord.Interaction) -> None:
    if not interaction.guild:
        await interaction.response.send_message("This command only works inside a server.", ephemeral=True)
        return
    if not await bot.is_admin(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    bridges = bot.storage.list_bridges(interaction.guild.id)
    if not bridges:
        await interaction.response.send_message("No channels linked.", ephemeral=True)
        return

    lines: list[str] = []
    for item in bridges:
        status = "ON" if item.get("enabled", True) else "OFF"
        d_channel = interaction.guild.get_channel(int(item["discord_channel_id"]))
        label = d_channel.mention if isinstance(d_channel, discord.TextChannel) else f"#{item['discord_channel_id']}"
        thread = item.get("telegram_thread_id")
        thread_text = f", thread={thread}" if thread is not None else ""
        lines.append(f"- [{status}] {label} -> chat {item['telegram_chat_id']}{thread_text}")

    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@bot.tree.command(name="bridge_backfill", description="Copy recent Discord messages to Telegram")
@app_commands.describe(channel="Source channel", limit="Number of messages (1-500)")
async def bridge_backfill(interaction: discord.Interaction, channel: discord.TextChannel, limit: int = DEFAULT_BACKFILL_LIMIT) -> None:
    if not interaction.guild:
        await interaction.response.send_message("This command only works inside a server.", ephemeral=True)
        return
    if not await bot.is_admin(interaction):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    bridge = bot.storage.get_bridge_for_discord(interaction.guild.id, channel.id)
    if not bridge:
        await interaction.response.send_message("That channel is not linked.", ephemeral=True)
        return

    limit = max(1, min(limit, 500))
    bot.storage.set_backfill_limit(interaction.guild.id, channel.id, limit)
    await interaction.response.defer(ephemeral=True, thinking=True)

    count = 0
    async for msg in channel.history(limit=limit, oldest_first=True):
        if msg.author == bot.user:
            continue
        await bot.relay_discord_to_telegram(msg, bridge)
        count += 1
        await asyncio.sleep(0.25)

    await interaction.followup.send(f"Backfill complete. Messages copied: {count}.", ephemeral=True)


@bot.tree.command(name="bridge_help", description="Bridge configuration help")
async def bridge_help(interaction: discord.Interaction) -> None:
    text = (
        "Commands:\n"
        "/bridge_add channel telegram_chat_id [telegram_thread_id]\n"
        "/bridge_remove channel\n"
        "/bridge_list\n"
        "/bridge_enable channel\n"
        "/bridge_disable channel\n"
        "/bridge_backfill channel [limit]\n\n"
        "Note: Telegram does not expose user message deletion events to bots,\n"
        "so real-time deletion from Telegram to Discord may not always be reflected."
    )
    await interaction.response.send_message(text, ephemeral=True)


def validate_env() -> None:
    missing: list[str] = []
    if not DISCORD_TOKEN:
        missing.append("BRIDGE_DISCORD_TOKEN")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")

    if missing:
        values = ", ".join(missing)
        raise RuntimeError(f"Missing required env vars: {values}")


if __name__ == "__main__":
    validate_env()
    bot.run(DISCORD_TOKEN)
