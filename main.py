"""Main entry point for Kingshot Combat Calculator Discord bot."""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.stats_tracker import get_tracker

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', 0))

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Store owner ID in bot for access from cogs
bot.owner_id = OWNER_ID


@bot.event
async def on_ready():
    """Event handler for bot startup."""
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot user ID: {bot.user.id}')
    print(f'Application ID: {bot.application_id}')
    
    # Show server count
    guild_count = len(bot.guilds)
    print(f'\n📊 Connected to {guild_count} server(s):')
    for guild in bot.guilds:
        print(f'  - {guild.name} (ID: {guild.id}) - {guild.member_count} members')
    
    # Show usage statistics
    tracker = get_tracker()
    stats = tracker.get_stats_summary()
    print(f'\n📈 Bot Statistics:')
    print(f'  Total commands used: {stats["total_commands"]}')
    print(f'  Unique users: {stats["total_users"]}')
    print(f'  Total servers tracked: {stats["total_guilds"]}')
    if stats["commands"]:
        print(f'  Command usage: {stats["commands"]}')
    
    # List commands before sync
    print('\nCommands registered in tree (before sync):')
    for cmd in bot.tree.get_commands():
        params_str = ', '.join([p.name for p in cmd.parameters]) if hasattr(cmd, 'parameters') and cmd.parameters else 'no parameters'
        print(f'  - /{cmd.name} ({params_str})')
    
    # Sync commands to Discord
    print('\nSyncing commands to Discord...')
    try:
        synced = await bot.tree.sync()
        print(f'  ✓ Commands synced successfully! ({len(synced)} commands active)')
        for cmd in synced:
            print(f'    - /{cmd.name}: {cmd.description}')
    except Exception as e:
        print(f'  ✗ Error syncing commands: {e}')
        import traceback
        traceback.print_exc()


@bot.event
async def on_guild_join(guild):
    """Event handler when bot joins a new server."""
    print(f'\n✅ Joined new server: {guild.name} (ID: {guild.id}) - {guild.member_count} members')
    print(f'   Total servers: {len(bot.guilds)}')


@bot.event
async def on_guild_remove(guild):
    """Event handler when bot is removed from a server."""
    print(f'\n❌ Removed from server: {guild.name} (ID: {guild.id})')
    print(f'   Total servers: {len(bot.guilds)}')


@bot.event
async def on_message(message):
    """Debug: Log all messages received."""
    if message.author != bot.user:
        print(f'[MESSAGE] From: {message.author} ({message.author.id}) | Channel: {message.channel.id} | Attachments: {len(message.attachments)} | Content: {message.content[:50] if message.content else ""}')
    await bot.process_commands(message)


@bot.command(name='ping')
async def ping(ctx):
    """Test command to verify bot is working."""
    await ctx.send(f'Pong! Latency: {bot.latency * 1000:.2f}ms')


@bot.command(name='sync')
async def sync(ctx):
    """Sync slash commands (owner only)."""
    if ctx.author.id != OWNER_ID:
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    try:
        # Sync globally
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Synced {len(synced)} commands globally. They may take up to 1 hour to appear in all servers.")
        
        # Also sync to current guild for immediate effect
        if ctx.guild:
            bot.tree.copy_global_to(guild=ctx.guild)
            guild_synced = await bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"✅ Also synced {len(guild_synced)} commands to this server immediately.")
        
        print(f"[SYNC] Commands synced by {ctx.author}")
    except Exception as e:
        await ctx.send(f"❌ Error syncing: {e}")
        print(f"[SYNC ERROR] {e}")
        import traceback
        traceback.print_exc()


# Load cogs
async def load_cogs():
    """Load all cogs (command modules)."""
    cogs_dir = 'cogs'
    if os.path.exists(cogs_dir):
        files = [f for f in os.listdir(cogs_dir) if f.endswith('.py') and not f.startswith('__')]
        # If a fixed replacement exists, prefer it and skip the original
        if 'commands_fixed.py' in files and 'commands.py' in files:
            files.remove('commands.py')

        # Skip any disabled files (renamed backups), temp files, and utility modules
        files = [f for f in files if 'disabled' not in f and not f.startswith('~') and f != 'translations.py']

        print(f'Cog files to load: {files}')
        for filename in files:
            await bot.load_extension(f'cogs.{filename[:-3]}')
            print(f'Loaded cog: {filename}')


async def main():
    """Main function to start the bot."""
    async with bot:
        await load_cogs()
        await bot.start(DISCORD_TOKEN)


if __name__ == '__main__':
    import asyncio
    
    if not DISCORD_TOKEN:
        print('ERROR: DISCORD_TOKEN not found in .env file')
        print('Please create a .env file with: DISCORD_TOKEN=your_token_here')
        exit(1)
    
    asyncio.run(main())
