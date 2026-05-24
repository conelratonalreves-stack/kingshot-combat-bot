"""
Run once to remove all global slash commands from this bot.
This eliminates duplicate commands that appear when both global and guild commands exist.
Usage: python clear_global_commands.py
"""
import asyncio
import os
from dotenv import load_dotenv
import discord
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("Clearing all global slash commands...")
    bot.tree.clear_commands(guild=None)
    synced = await bot.tree.sync()
    print(f"Global commands after clear: {len(synced)}")
    print("Done. You can close this script now.")
    await bot.close()

asyncio.run(bot.start(TOKEN))
