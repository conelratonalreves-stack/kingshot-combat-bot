# Read the entire file
with open('spy_bot_from_rpi.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find where stats command starts and ends
stats_start = content.find('@bot.tree.command(name="stats")')
async_main = content.find('async def main():', stats_start)

# Create simple stats command
simple_stats = '''@bot.tree.command(name="stats")
async def stats_command(interaction: discord.Interaction):
    """Show spy bot statistics."""
    
    data = load_spy_data()
    shield_data = load_shield_data()
    reports = data["reports"]
    
    if len(reports) == 0:
        await interaction.response.send_message(
            "📊 **No Data Yet**\\n"
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
        value=f"**Total Reports:** {len(reports)}\\n"
              f"**Unique Alliances:** {len(alliances)}\\n"
              f"**Active Shields:** {active_shields}",
        inline=False
    )
    
    if top_alliances:
        alliance_list = "\\n".join([f"**{alliance}**: {count} player(s)" for alliance, count in top_alliances])
        embed.add_field(
            name="🏆 Top Tracked Alliances",
            value=alliance_list,
            inline=False
        )
    
    embed.set_footer(text="Bot by KnyCat")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


'''

# Replace the broken stats command
new_content = content[:stats_start] + simple_stats + content[async_main:]

# Write to new file
with open('spy_bot_main.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('✓ Created clean stats command')
