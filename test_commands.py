"""Test script to verify commands are registered correctly."""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from main import bot, load_cogs

async def test_commands():
    """Test command registration."""
    print("Loading cogs...")
    await load_cogs()
    
    print("\nRegistered commands in tree:")
    for cmd in bot.tree.get_commands():
        params = ', '.join([f"{p.name}: {p.type}" for p in cmd.parameters]) if cmd.parameters else "no parameters"
        print(f"  - /{cmd.name} ({params})")
        print(f"    Description: {cmd.description}")
    
    if not bot.tree.get_commands():
        print("  ⚠️ No commands registered!")
    
    print("\nDone!")

if __name__ == '__main__':
    asyncio.run(test_commands())
