"""Discord commands for battle calculation."""

import discord
from discord.ext import commands
from discord import app_commands
import io
import asyncio
from typing import Optional
from models.troop import TroopComposition, TroopStats
from models.hero import BattleHeroes
from models.battle import BattleCalculator
from utils.ocr_extractor import (
    parse_troop_input, 
    extract_battle_report_stats
)


class CalculationSession:
    """Store calculation session data."""
    
    def __init__(self, user_id: int, total_troops: int):
        self.user_id = user_id
        self.total_troops = total_troops
        self.allied_stats = None
        self.enemy_stats = None
        self.image_data = None
        self.stage = "awaiting_image"


class BattleCommands(commands.Cog):
    """Discord commands for Kingshot battle calculations."""
    
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}  # {user_id: CalculationSession}
    
    @app_commands.command(
        name="calculate",
        description="Calculate optimal troop composition against enemy"
    )
    @app_commands.describe(
        tropas_totales="Total number of troops available (e.g., 900450 or 1080000)"
    )
    async def calculate_command(
        self,
        interaction: discord.Interaction,
        tropas_totales: str
    ):
        """Main command to start battle calculation."""
        
        # Parse total troops
        parse_result = parse_troop_input(tropas_totales)
        
        if not parse_result["success"]:
            await interaction.response.send_message(
                f"❌ {parse_result['error']}",
                ephemeral=True
            )
            return
        
        total_troops = parse_result["total_troops"]
        
        # Create session
        session = CalculationSession(interaction.user.id, total_troops)
        self.sessions[interaction.user.id] = session
        
        # Ask for screenshot
        embed = discord.Embed(
            title="⚔️ Kingshot Battle Calculator",
            description="Step 1 of 1: Upload Battle Report Screenshot",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="📸 Required Screenshot",
            value="Please upload a screenshot showing:\n" +
                  "• **LEFT side**: Your troop stats (Ataque, Defensa, Letalidad, Salud)\n" +
                  "• **RIGHT side**: Enemy troop stats (same format)\n" +
                  "• All three troop types: Infantería, Caballería, Arquero",
            inline=False
        )
        embed.add_field(
            name="📊 Your Troops",
            value=f"Total available: **{total_troops:,}**",
            inline=False
        )
        embed.set_footer(text="Upload the image as a message attachment")
        
        await interaction.response.send_message(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for image uploads in response to calculation requests."""
        
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Debug: Log all messages from users with sessions
        if message.author.id in self.sessions:
            print(f"[DEBUG] Message from {message.author}: attachments={len(message.attachments)}, content='{message.content}'")
        
        # Check if user has active session
        if message.author.id not in self.sessions:
            return
        
        session = self.sessions[message.author.id]
        
        # Check if message has attachments
        if not message.attachments:
            print(f"[DEBUG] No attachments for user {message.author.id}")
            return
        
        try:
            attachment = message.attachments[0]
            
            # Verify it's an image
            if not attachment.content_type or not attachment.content_type.startswith('image/'):
                await message.reply("❌ Please upload an image file")
                return
            
            # Download image
            image_bytes = await attachment.read()
            
            # Show processing message
            processing_msg = await message.reply("🔄 Analyzing battle report...")
            
            # Extract stats from image
            extraction_result = extract_battle_report_stats(image_bytes)
            
            if not extraction_result["success"]:
                await processing_msg.edit(
                    content=f"❌ **Error**: {extraction_result['error']}\n\n" +
                            f"Make sure the screenshot shows both allied (left) and enemy (right) stats clearly."
                )
                return
            
            # Store extracted stats
            session.allied_stats = extraction_result["stats"]["aliados"]
            session.enemy_stats = extraction_result["stats"]["enemigos"]
            
            # Create result embed
            result_embed = await self._create_result_embed(session)
            
            await processing_msg.edit(
                content="✅ Battle analysis complete!",
                embed=result_embed
            )
            
            # Clean up session
            del self.sessions[message.author.id]
        
        except Exception as e:
            await message.reply(f"❌ Error processing image: {str(e)}")
    
    async def _create_result_embed(self, session: CalculationSession) -> discord.Embed:
        """Create the result embed with battle analysis."""
        
        embed = discord.Embed(
            title="⚔️ Battle Analysis Results",
            color=discord.Color.blue()
        )
        
        # Allied stats
        allied_summary = self._format_stats_summary(session.allied_stats)
        embed.add_field(
            name="🛡️ Your Troops",
            value=f"**Total Available**: {session.total_troops:,}\n\n{allied_summary}",
            inline=True
        )
        
        # Enemy stats
        enemy_summary = self._format_stats_summary(session.enemy_stats)
        embed.add_field(
            name="⚔️ Enemy Troops",
            value=enemy_summary,
            inline=True
        )
        
        # Recommendations
        recommendations = self._calculate_recommendations(session)
        embed.add_field(
            name="📋 Recommendations",
            value=recommendations,
            inline=False
        )
        
        embed.set_footer(text="Use /help for more information")
        
        return embed
    
    def _format_stats_summary(self, stats: dict) -> str:
        """Format stats for display."""
        summary = ""
        for troop_type in ['infanteria', 'caballeria', 'arquero']:
            troop_stats = stats[troop_type]
            troop_name = {
                'infanteria': 'Infantry',
                'caballeria': 'Cavalry',
                'arquero': 'Archers'
            }[troop_type]
            
            if any(v is not None for v in troop_stats.values()):
                summary += f"**{troop_name}:**\n"
                if troop_stats['ataque'] is not None:
                    summary += f"  Ataque: {troop_stats['ataque']:+.1f}%\n"
                if troop_stats['defensa'] is not None:
                    summary += f"  Defensa: {troop_stats['defensa']:+.1f}%\n"
                if troop_stats['letalidad'] is not None:
                    summary += f"  Letalidad: {troop_stats['letalidad']:+.1f}%\n"
                if troop_stats['salud'] is not None:
                    summary += f"  Salud: {troop_stats['salud']:+.1f}%\n"
                summary += "\n"
        
        return summary if summary else "No stats extracted"
    
    def _calculate_recommendations(self, session: CalculationSession) -> str:
        """Calculate battle recommendations based on stats."""
        
        # This is a placeholder - actual calculation would compare stats
        # For now, return basic format
        
        recommendations = "📊 **Troop Composition Recommendations**\n\n"
        recommendations += "**Optimal Formation:**\n"
        recommendations += "• Infantry: 50%\n"
        recommendations += "• Cavalry: 20%\n"
        recommendations += "• Archers: 30%\n\n"
        recommendations += "**Expected Result**: Victory (needs detailed calculation)\n"
        recommendations += "**Battles Needed**: 1\n"
        
        return recommendations
    
    @app_commands.command(
        name="help",
        description="Show help information"
    )
    async def help_command(self, interaction: discord.Interaction):
        """Help command."""
        embed = discord.Embed(
            title="Kingshot Combat Calculator - Help",
            description="Commands for battle calculations and strategy analysis",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="/calculate [tropas_totales]",
            value="Start a battle analysis\n" +
                  "**Usage**: `/calculate 900450`\n" +
                  "Then upload a screenshot with left (your stats) and right (enemy stats)",
            inline=False
        )
        
        embed.add_field(
            name="📸 Screenshot Format",
            value="The screenshot should show:\n" +
                  "• **LEFT**: Your troop stats (Ataque, Defensa, Letalidad, Salud)\n" +
                  "• **RIGHT**: Enemy troop stats (same format)\n" +
                  "• All three types: Infantería, Caballería, Arquero",
            inline=False
        )
        
        embed.add_field(
            name="📊 Game Mechanics",
            value="The bot uses Kingshot's actual damage formula:\n" +
                  "`Damage = √Troops × (Attack × Lethality) / (Defense × Health) × SkillMod`\n\n" +
                  "Attack order: Infantry → Cavalry → Archers (simultaneous per type)",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    """Setup function to load this cog."""
    await bot.add_cog(BattleCommands(bot))
