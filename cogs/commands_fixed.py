"""Discord commands for battle calculation."""

import discord
from discord.ext import commands
from discord import app_commands
import io
import asyncio
import os
from pathlib import Path
from typing import Optional
from models.troop import TroopComposition, TroopStats
from models.hero import BattleHeroes
from models.battle import BattleCalculator
from utils.ocr_extractor import (
    parse_troop_input, 
    extract_battle_report_stats_with_retries
)
from .translations import (
    get_text, set_user_language, get_user_language, get_available_languages
)
from utils.stats_tracker import get_tracker


class BattleCommands(commands.Cog):
    """Discord commands for Kingshot battle calculations."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @staticmethod
    def get_bonus_multiplier(troop_level: str) -> float:
        """Get bonus multiplier based on troop level.
        
        Args:
            troop_level: Level string like "1", "5", "10", "tg1", "tg2", etc.
            
        Returns:
            Multiplier for bonus stats based on exponential growth
        """
        level_str = troop_level.lower().strip()
        
        # True Gold levels (accelerating growth)
        if level_str.startswith("tg"):
            try:
                tg_level = int(level_str[2:])
                tg_multipliers = {
                    1: 2.600,
                    2: 2.875,
                    3: 3.175,
                    4: 3.500,
                    5: 3.850
                }
                return tg_multipliers.get(tg_level, 2.875)
            except:
                return 2.875
        
        # Regular levels T1-T10 (exponential: 1.0 to 2.5)
        try:
            level = int(level_str)
            if 1 <= level <= 10:
                # Exponential formula: 1.0 × (2.5)^((level-1)/9)
                import math
                return 1.0 * math.pow(2.5, (level - 1) / 9.0)
        except:
            pass
        
        # Default to TG2 if invalid
        return 2.875
    
    @app_commands.command(name="calculate")
    @app_commands.describe(troop_level="Select your troop tier (affects bonus multiplier)")
    @app_commands.choices(troop_level=[
        app_commands.Choice(name="T1 (×1.00)", value="1"),
        app_commands.Choice(name="T2 (×1.11)", value="2"),
        app_commands.Choice(name="T3 (×1.22)", value="3"),
        app_commands.Choice(name="T4 (×1.35)", value="4"),
        app_commands.Choice(name="T5 (×1.49)", value="5"),
        app_commands.Choice(name="T6 (×1.65)", value="6"),
        app_commands.Choice(name="T7 (×1.82)", value="7"),
        app_commands.Choice(name="T8 (×2.01)", value="8"),
        app_commands.Choice(name="T9 (×2.22)", value="9"),
        app_commands.Choice(name="T10 (×2.50)", value="10"),
        app_commands.Choice(name="True Gold 1 (×2.60)", value="tg1"),
        app_commands.Choice(name="True Gold 2 (×2.88)", value="tg2"),
        app_commands.Choice(name="True Gold 3 (×3.18)", value="tg3"),
        app_commands.Choice(name="True Gold 4 (×3.50)", value="tg4"),
        app_commands.Choice(name="True Gold 5 (×3.85)", value="tg5"),
    ])
    async def calculate_command(
        self,
        interaction: discord.Interaction,
        troop_level: str
    ):
        """Main command to start battle calculation."""
        
        # Track command usage
        tracker = get_tracker()
        tracker.track_command(
            "calculate",
            interaction.user.id,
            str(interaction.user),
            interaction.guild_id if interaction.guild else None,
            interaction.guild.name if interaction.guild else None
        )
        
        # Get user's language
        lang = get_user_language(interaction.user.id)
        
        # Ask for screenshot
        embed = discord.Embed(
            title=get_text('battle_calculator', lang),
            description=get_text('requires_screenshots', lang),
            color=discord.Color.gold()
        )
        embed.add_field(
            name=get_text('required_screenshots', lang),
            value=get_text('screenshot_instructions', lang),
            inline=False
        )
        embed.add_field(
            name=get_text('time_limit', lang),
            value=get_text('time_limit_text', lang),
            inline=False
        )
        embed.set_footer(text=get_text('reply_instruction', lang))
        
        # Try to attach example images using absolute path
        files = []
        bot_dir = Path(__file__).parent.parent  # Get bot root directory
        
        example_combined_path = bot_dir / 'data' / 'example_combined.png'
        example_top_path = bot_dir / 'data' / 'example_top.png'
        example_bottom_path = bot_dir / 'data' / 'example_bottom.png'

        # Prefer a single combined example to avoid Discord auto-cropping
        if example_combined_path.exists():
            try:
                files.append(discord.File(str(example_combined_path)))
            except Exception as e:
                print(f"Warning: Could not load example_combined.png: {e}")
        else:
            if example_top_path.exists():
                try:
                    files.append(discord.File(str(example_top_path)))
                except Exception as e:
                    print(f"Warning: Could not load example_top.png: {e}")
            
            if example_bottom_path.exists():
                try:
                    files.append(discord.File(str(example_bottom_path)))
                except Exception as e:
                    print(f"Warning: Could not load example_bottom.png: {e}")

        if files:
            await interaction.response.send_message(embed=embed, files=files)
        else:
            await interaction.response.send_message(embed=embed)

        # New flow: request two images (top and bottom parts)
        try:
            # Helper to get one image with retries and timeout
            async def request_image(part_name: str, attempts: int = 2) -> Optional[discord.Message]:
                """Request image from user with timeout and retry logic.

                Accepts any message from the user in the same channel that has attachments;
                replying to the prompt is optional.
                """
                retries = 0

                while retries <= attempts:
                    try:
                        lang = get_user_language(interaction.user.id)
                        prompt = await interaction.followup.send(
                            f"📸 {part_name}",
                            ephemeral=False
                        )

                        print(f"[DEBUG] Waiting for {part_name} image from user {interaction.user.id} (attempt {retries+1}/{attempts+1})")

                        def check(msg):
                            has_attachment = len(msg.attachments) > 0
                            is_author = msg.author.id == interaction.user.id
                            is_channel = msg.channel.id == interaction.channel.id
                            is_reply_to_prompt = msg.reference and msg.reference.message_id == prompt.id
                            if is_author and is_channel and has_attachment:
                                print(f"[DEBUG] Message candidate - attachments: {len(msg.attachments)}, reply_to_prompt: {is_reply_to_prompt}")
                            return is_author and is_channel and has_attachment

                        msg = await self.bot.wait_for('message', timeout=300.0, check=check)
                        print(f"[DEBUG] Received {part_name} image with {len(msg.attachments)} attachments from {msg.author}")
                        return msg

                    except asyncio.TimeoutError:
                        lang = get_user_language(interaction.user.id)
                        remaining = attempts - retries
                        if remaining > 0:
                            await interaction.followup.send(
                                f"{get_text('timeout', lang)} {remaining}",
                                ephemeral=True
                            )
                            retries += 1
                        else:
                            await interaction.followup.send(
                                get_text('max_retries', lang),
                                ephemeral=True
                            )
                            return None
                    except Exception as e:
                        lang = get_user_language(interaction.user.id)
                        print(f"[ERROR] Error waiting for {part_name} image: {e}")
                        await interaction.followup.send(
                            f"{get_text('error', lang)}: {str(e)}",
                            ephemeral=True
                        )
                        return None

            # Request top image
            top_msg = await request_image('TOP (upper) part of the battle report')
            if top_msg is None:
                return

            # If user attached both images at once, split them: first = top, second = bottom
            if len(top_msg.attachments) >= 2:
                print(f"[DEBUG] Received multiple attachments ({len(top_msg.attachments)}) in TOP request; using first as TOP and second as BOTTOM")
                bottom_msg = top_msg  # reuse message; we'll pick 2nd attachment inside _process_two_images
            else:
                # Request bottom image
                bottom_msg = await request_image('BOTTOM (lower) part of the battle report')
                if bottom_msg is None:
                    return

            # Process both images (troop count will be extracted from TOP image)
            await self._process_two_images(top_msg, bottom_msg, interaction.user, troop_level)

        except Exception as e:
            lang = get_user_language(interaction.user.id)
            print(f"[ERROR] Error in two-image flow: {e}")
            await interaction.followup.send(f"{get_text('error', lang)}: {str(e)}", ephemeral=True)
    
    async def _process_image(self, message: discord.Message, user: discord.User, total_troops: int):
        """Process uploaded image and extract stats with retry capability."""
        max_retries = 2
        retry_count = 0
        current_message = message
        
        while retry_count <= max_retries:
            try:
                attachment = current_message.attachments[0]
                
                # Verify it's an image
                if not attachment.content_type or not attachment.content_type.startswith('image/'):
                    await current_message.reply("❌ Please upload an image file.")
                    return
                
                print(f"[DEBUG] Processing image: {attachment.filename} ({attachment.content_type})")
                
                # Show processing message
                lang = get_user_language(user.id)
                processing_msg = await current_message.reply(get_text('analyzing', lang))
                
                # Download image
                image_bytes = await attachment.read()
                print(f"[DEBUG] Image downloaded: {len(image_bytes)} bytes")
                
                # Extract stats from image with retries
                print(f"[DEBUG] Starting OCR extraction...")
                extraction_result = extract_battle_report_stats_with_retries(image_bytes, max_attempts=3)
                
                print(f"[DEBUG] OCR result: {extraction_result}")
                
                if not extraction_result["success"]:
                    retry_count += 1
                    if retry_count <= max_retries:
                        remaining_retries = max_retries - retry_count
                        retry_msg = f"❌ **Error**: {extraction_result['error']}\n\n" + \
                                    f"Make sure the screenshot shows the enemy scout report with both sides clearly visible.\n\n" + \
                                    f"📸 **Please upload the correct screenshot** (Attempt {retry_count}/{max_retries})\n" + \
                                    f"⏱️ You have **5 minutes** to upload the new image. After that, you'll need to use `/calculate` again."
                        await processing_msg.edit(content=retry_msg)
                        
                        # Wait for new image from same user in same channel
                        try:
                            def check(msg):
                                return (
                                    msg.author.id == user.id and
                                    msg.channel.id == current_message.channel.id and
                                    len(msg.attachments) > 0
                                )
                            
                            print(f"[DEBUG] Waiting for retry image (attempt {retry_count}/{max_retries})")
                            current_message = await self.bot.wait_for('message', timeout=300.0, check=check)
                            print(f"[DEBUG] Received retry message with {len(current_message.attachments)} attachments")
                            continue  # Try processing the new image
                        except asyncio.TimeoutError:
                            await processing_msg.edit(
                                content="⏱️ **Timeout**: No new image received within 5 minutes.\n\n" +
                                        "Please use `/calculate` again to start over and try with a clearer screenshot."
                            )
                            return
                    else:
                        await processing_msg.edit(
                            content=f"❌ **Maximum retry attempts reached**\n\n" +
                                    f"Error: {extraction_result['error']}\n\n" +
                                    f"Please use `/calculate` again and ensure the screenshot is:\n" +
                                    f"• Clear and in focus\n" +
                                    f"• Shows both Your stats (left) and Enemy stats (right)\n" +
                                    f"• Includes all three troop types (Infantry, Cavalry, Archers)"
                        )
                        return
                else:
                    # Success! Create result embed
                    total_enemy_troops = extraction_result.get('enemy_troops', 0)
                    if total_enemy_troops == 0:
                        # Fallback: sum counts from stats if available
                        for troop_type in ['infanteria', 'caballeria', 'arquero']:
                            count = extraction_result.get('stats', {}).get('enemigos', {}).get(troop_type, {}).get('count', 0)
                            if count:
                                total_enemy_troops += count

                    lang = get_user_language(user.id)
                    result_embed = await self._create_result_embed(extraction_result["stats"], total_troops, total_enemy_troops, lang=lang)
                    
                    await processing_msg.edit(
                        content=get_text('complete', lang),
                        embed=result_embed
                    )
                    return
                
            except Exception as e:
                print(f"[ERROR] Error processing image: {e}")
                await current_message.reply(f"❌ Error processing image: {str(e)}")
                return
    
    async def _create_result_embed(self, stats: dict, total_troops: int, total_enemy_troops_param: int = 0, troop_level: str = "tg2", lang: str = "en") -> discord.Embed:
        """Create the result embed with battle analysis."""
        
        embed = discord.Embed(
            title=get_text('battle_results', lang),
            color=discord.Color.blue()
        )
        
        # Use enemy_troops from TOP image if available, otherwise calculate from stats
        # Handle None case
        total_enemy_troops = total_enemy_troops_param if total_enemy_troops_param is not None else 0
        for troop_type in ['infanteria', 'caballeria', 'arquero']:
            count = stats.get('enemigos', {}).get(troop_type, {}).get('count')
            if count:
                total_enemy_troops += count

        # Debug trace to verify troop counts used in simulations
        try:
            print(f"[DEBUG] Embed totals - allies: {total_troops}, enemies: {total_enemy_troops}")
        except Exception:
            pass
        
        # Format stats side by side
        allied_lines = []
        enemy_lines = []
        
        allied_lines.append(f"**Total Available**: {total_troops:,}")
        if total_enemy_troops > 0:
            enemy_lines.append(f"**Total Available**: {total_enemy_troops:,}")
        else:
            enemy_lines.append("**Total Available**: N/A")
        
        allied_lines.append("")
        enemy_lines.append("")
        
        # For each troop type, show side by side
        for troop_type in ['infanteria', 'caballeria', 'arquero']:
            troop_name_key = {
                'infanteria': 'infantry',
                'caballeria': 'cavalry',
                'arquero': 'archers'
            }[troop_type]
            troop_name = get_text(troop_name_key, lang)
            
            allied_stats = stats.get('aliados', {}).get(troop_type, {})
            enemy_stats = stats.get('enemigos', {}).get(troop_type, {})
            
            allied_lines.append(f"**{troop_name}:**")
            enemy_lines.append(f"**{troop_name}:**")
            
            # Attack
            if allied_stats.get('ataque') is not None:
                allied_lines.append(f"  {get_text('attack', lang)}: {allied_stats['ataque']:+.1f}%")
            else:
                allied_lines.append(f"  {get_text('attack', lang)}: N/A")
            
            if enemy_stats.get('ataque') is not None:
                enemy_lines.append(f"  {get_text('attack', lang)}: {enemy_stats['ataque']:+.1f}%")
            else:
                enemy_lines.append(f"  {get_text('attack', lang)}: N/A")
            
            # Defense
            if allied_stats.get('defensa') is not None:
                allied_lines.append(f"  {get_text('defense', lang)}: {allied_stats['defensa']:+.1f}%")
            else:
                allied_lines.append(f"  {get_text('defense', lang)}: N/A")
            
            if enemy_stats.get('defensa') is not None:
                enemy_lines.append(f"  {get_text('defense', lang)}: {enemy_stats['defensa']:+.1f}%")
            else:
                enemy_lines.append(f"  {get_text('defense', lang)}: N/A")
            
            # Lethality
            if allied_stats.get('letalidad') is not None:
                allied_lines.append(f"  {get_text('lethality', lang)}: {allied_stats['letalidad']:+.1f}%")
            else:
                allied_lines.append(f"  {get_text('lethality', lang)}: N/A")
            
            if enemy_stats.get('letalidad') is not None:
                enemy_lines.append(f"  {get_text('lethality', lang)}: {enemy_stats['letalidad']:+.1f}%")
            else:
                enemy_lines.append(f"  {get_text('lethality', lang)}: N/A")
            
            # Health
            if allied_stats.get('salud') is not None:
                allied_lines.append(f"  {get_text('health', lang)}: {allied_stats['salud']:+.1f}%")
            else:
                allied_lines.append(f"  {get_text('health', lang)}: N/A")
            
            if enemy_stats.get('salud') is not None:
                enemy_lines.append(f"  {get_text('health', lang)}: {enemy_stats['salud']:+.1f}%")
            else:
                enemy_lines.append(f"  {get_text('health', lang)}: N/A")
            
            allied_lines.append("")
            enemy_lines.append("")
        
        # Add fields with aligned content
        embed.add_field(
            name=get_text('your_troops', lang),
            value="\n".join(allied_lines) if allied_lines else "No stats extracted",
            inline=True
        )
        
        embed.add_field(
            name=get_text('enemy_troops', lang),
            value="\n".join(enemy_lines) if enemy_lines else "No stats extracted",
            inline=True
        )
        
        # Recommendations
        # Run a quick simulation using a default composition split (50/20/30)
        try:
            bonus_multiplier = self.get_bonus_multiplier(troop_level)
            recommendations = self._calculate_recommendations(stats, total_troops, total_enemy_troops, bonus_multiplier, lang)
        except Exception as e:
            recommendations = f"Could not run simulation: {e}"
        embed.add_field(
            name=get_text('recommendations', lang),
            value=recommendations,
            inline=False
        )
        
        footer_text = get_text('donation_footer', lang)
        embed.set_footer(text=footer_text)
        
        return embed

    async def _process_two_images(self, top_message: discord.Message, bottom_message: discord.Message, user: discord.User, troop_level: str = "tg2"):
        """Process two uploaded images (top and bottom parts), merge OCR results, and produce analysis."""
        try:
            # Handle case where both images were uploaded in same message
            if top_message == bottom_message and len(top_message.attachments) >= 2:
                # Both images in one message: first = TOP, second = BOTTOM
                top_att = top_message.attachments[0]
                bot_att = top_message.attachments[1]
            else:
                # Separate messages for TOP and BOTTOM
                top_att = top_message.attachments[0]
                bot_att = bottom_message.attachments[0]

            if not (top_att.content_type and top_att.content_type.startswith('image/')):
                await top_message.reply("❌ The TOP file is not an image. Please run `/calculate` and upload images.")
                return
            if not (bot_att.content_type and bot_att.content_type.startswith('image/')):
                await bottom_message.reply("❌ The BOTTOM file is not an image. Please run `/calculate` and upload images.")
                return

            lang = get_user_language(user.id)
            processing_msg = await bottom_message.reply(get_text('processing', lang))

            # Read bytes
            top_bytes = await top_att.read()
            bottom_bytes = await bot_att.read()

            # Check if images are identical (only if they're actually different attachments)
            if top_att.id == bot_att.id:
                await processing_msg.edit(
                    content="❌ **Same image uploaded twice**\n\n"
                            "You uploaded the same image for TOP and BOTTOM.\n\n"
                            "**Please upload TWO DIFFERENT screenshots:**\n"
                            "• **TOP**: Upper part showing total troop count (Escuadrón)\n"
                            "• **BOTTOM**: Lower part showing attribute bonuses and troop type counts\n\n"
                            "Run `/calculate` again with different images."
                )
                return

            # Run OCR on both with multiple retry attempts
            top_result = extract_battle_report_stats_with_retries(top_bytes, max_attempts=3)
            print(f"[DEBUG] OCR top result: {top_result}")
            if not top_result.get('success'):
                await processing_msg.edit(content=f"❌ Error extracting TOP image: {top_result.get('error')}\n\nPlease retry by running `/calculate`.")
                return

            # Extract total troops from TOP image
            total_troops = top_result.get('ally_troops') or 0
            total_enemy_troops = top_result.get('enemy_troops') or 0
            if total_troops == 0:
                await processing_msg.edit(content=f"❌ Could not extract troop count from TOP image. Please ensure the screenshot clearly shows the power loss line (negative numbers) and the troop count line below it.\n\nPlease retry by running `/calculate`.")
                return

            bottom_result = extract_battle_report_stats_with_retries(bottom_bytes, max_attempts=3)
            print(f"[DEBUG] OCR bottom result: {bottom_result}")
            if not bottom_result.get('success'):
                await processing_msg.edit(content=f"❌ Error extracting BOTTOM image: {bottom_result.get('error')}\n\nPlease retry by running `/calculate`.")
                return
            
            # Verify BOTTOM has attribute bonuses (not all zeros)
            bottom_stats = bottom_result.get('stats', {})
            has_bonuses = any(
                any(troop.get(attr, 0) != 0.0 for attr in ['ataque', 'defensa', 'letalidad', 'salud'])
                for side in bottom_stats.values()
                for troop in side.values()
            )
            if not has_bonuses:
                await processing_msg.edit(
                    content="❌ **BOTTOM image has no attribute bonuses**\n\n"
                            "The BOTTOM screenshot should show the attribute percentages section.\n\n"
                            "**Make sure BOTTOM image shows:**\n"
                            "• Bonificaciones de atributo (Attribute bonuses)\n"
                            "• Attack %, Defense %, Lethality %, Health % for all troop types\n"
                            "• Infantry, Cavalry, and Archers sections\n\n"
                            "Run `/calculate` again with the correct BOTTOM screenshot."
                )
                return

            # Merge stats: prefer attribute percentages from bottom, counts from top
            merged = {'aliados': {}, 'enemigos': {}}
            sides = ['aliados', 'enemigos']
            types = ['infanteria', 'caballeria', 'arquero']

            top_stats = top_result.get('stats', {})
            bottom_stats = bottom_result.get('stats', {})

            for side in sides:
                merged_side = {}
                top_side = top_stats.get(side, {})
                bottom_side = bottom_stats.get(side, {})
                for t in types:
                    merged_t = {}
                    top_t = top_side.get(t, {})
                    bot_t = bottom_side.get(t, {})

                    # Attributes (percent modifiers)
                    merged_t['ataque'] = bot_t.get('ataque') if bot_t.get('ataque') is not None else top_t.get('ataque')
                    merged_t['defensa'] = bot_t.get('defensa') if bot_t.get('defensa') is not None else top_t.get('defensa')
                    merged_t['letalidad'] = bot_t.get('letalidad') if bot_t.get('letalidad') is not None else top_t.get('letalidad')
                    merged_t['salud'] = bot_t.get('salud') if bot_t.get('salud') is not None else top_t.get('salud')

                    merged_side[t] = merged_t
                merged[side] = merged_side

            # Validate that we have complete data for at least one troop type per side
            def has_complete_troop_data(side_stats):
                """Check if at least one troop type has all attributes (can be 0 or non-zero)."""
                for troop_type in side_stats.values():
                    if all(troop_type.get(attr) is not None for attr in ['ataque', 'defensa', 'letalidad', 'salud']):
                        return True
                return False
            
            allies_complete = has_complete_troop_data(merged['aliados'])
            enemies_complete = has_complete_troop_data(merged['enemigos'])
            
            if not (allies_complete and enemies_complete):
                missing_data = []
                if not allies_complete:
                    missing_data.append("YOUR troops (Allied)")
                if not enemies_complete:
                    missing_data.append("ENEMY troops")
                
                await processing_msg.edit(
                    content=f"❌ **Incomplete data extracted**\n\n"
                            f"Missing attribute bonuses for: {' and '.join(missing_data)}\n\n"
                            f"**Please ensure the screenshot shows:**\n"
                            f"• All three troop types (Infantry, Cavalry, Archers)\n"
                            f"• Attribute percentages (Attack, Defense, Lethality, Health)\n"
                            f"• Both YOUR stats (left) and ENEMY stats (right)\n"
                            f"• Clear, focused image without glare or blur\n\n"
                            f"📸 **Run `/calculate` again with a clearer screenshot**"
                )
                return

            # Create and send result embed
            lang = get_user_language(user.id)
            result_embed = await self._create_result_embed(merged, total_troops, total_enemy_troops, troop_level, lang)
            await processing_msg.edit(content=get_text('complete', lang), embed=result_embed)

        except Exception as e:
            print(f"[ERROR] Error processing two images: {e}")
            await bottom_message.reply(f"❌ Error processing images: {e}")
    
    def _format_stats_summary(self, stats: dict) -> str:
        """Format stats for display."""
        summary = ""
        for troop_type in ['infanteria', 'caballeria', 'arquero']:
            troop_stats = stats.get(troop_type, {})
            troop_name = {
                'infanteria': 'Infantry',
                'caballeria': 'Cavalry',
                'arquero': 'Archers'
            }[troop_type]
            
            if any(v is not None for v in troop_stats.values()):
                summary += f"**{troop_name}:**\n"
                if troop_stats.get('ataque') is not None:
                    summary += f"  Attack: {troop_stats['ataque']:+.1f}%\n"
                if troop_stats.get('defensa') is not None:
                    summary += f"  Defense: {troop_stats['defensa']:+.1f}%\n"
                if troop_stats.get('letalidad') is not None:
                    summary += f"  Lethality: {troop_stats['letalidad']:+.1f}%\n"
                if troop_stats.get('salud') is not None:
                    summary += f"  Health: {troop_stats['salud']:+.1f}%\n"
                summary += "\n"
        
        return summary if summary else "No stats extracted"
    
    def _calculate_recommendations(self, stats: dict, total_troops: int, total_enemy_troops: int, bonus_multiplier: float = 2.5, lang: str = "en") -> str:
        """Calculate optimal composition and battle recommendations."""
        
        def make_composition(side: str, total: int, inf_pct: float = 0.5, cav_pct: float = 0.2, bonus_mods: dict = None):
            """Create composition with custom troop split and optional bonuses (can be negative to debuff enemy)."""
            s = stats.get(side, {})
            inf = s.get('infanteria', {})
            cav = s.get('caballeria', {})
            arc = s.get('arquero', {})

            inf_count = int(total * inf_pct)
            cav_count = int(total * cav_pct)
            arc_count = max(0, total - inf_count - cav_count)

            bonus = bonus_mods or {}
            
            return TroopComposition(
                infantry=TroopStats(
                    attack=(inf.get('ataque') or 0.0) + bonus.get('attack', 0.0),
                    lethality=(inf.get('letalidad') or 0.0) + bonus.get('lethality', 0.0),
                    defense=(inf.get('defensa') or 1.0) + bonus.get('defense', 0.0),
                    health=(inf.get('salud') or 1.0) + bonus.get('health', 0.0),
                    count=inf_count,
                    troop_type='infantry'
                ),
                cavalry=TroopStats(
                    attack=(cav.get('ataque') or 0.0) + bonus.get('attack', 0.0),
                    lethality=(cav.get('letalidad') or 0.0) + bonus.get('lethality', 0.0),
                    defense=(cav.get('defensa') or 1.0) + bonus.get('defense', 0.0),
                    health=(cav.get('salud') or 1.0) + bonus.get('health', 0.0),
                    count=cav_count,
                    troop_type='cavalry'
                ),
                archers=TroopStats(
                    attack=(arc.get('ataque') or 0.0) + bonus.get('attack', 0.0),
                    lethality=(arc.get('letalidad') or 0.0) + bonus.get('lethality', 0.0),
                    defense=(arc.get('defensa') or 1.0) + bonus.get('defense', 0.0),
                    health=(arc.get('salud') or 1.0) + bonus.get('health', 0.0),
                    count=arc_count,
                    troop_type='archers'
                )
            )

        # Test multiple troop splits to find optimal damage composition
        # Infantry is critical: attacks first, protects damage dealers (Cav/Archers)
        # Standard formation: 50:20:30 (Inf:Cav:Arc) per Kingshot guides
        # Minimum 10% per type to utilize hero bonuses
        best_damage = -1
        best_composition = None
        best_split = None
        
        for inf_pct in [0.4, 0.45, 0.5, 0.55, 0.6]:
            for cav_pct in [0.1, 0.15, 0.2, 0.25, 0.3]:
                arc_pct = 1.0 - inf_pct - cav_pct
                if arc_pct < 0.1 or arc_pct > 0.5:
                    continue
                
                attacker_comp = make_composition('aliados', total_troops, inf_pct, cav_pct)
                defender_comp = make_composition('enemigos', total_enemy_troops, 0.5, 0.2)
                # Ambos lados usan héroes con +25% SkillMod
                attacker_heroes = BattleHeroes()
                attacker_heroes._damage_boost = 1.25
                defender_heroes = BattleHeroes()
                defender_heroes._damage_boost = 1.25
                
                result = BattleCalculator.simulate_battle(attacker_comp, attacker_heroes, defender_comp, defender_heroes)
                
                # Calculate total damage dealt to enemy
                enemy_dead = sum(result.defender_casualties.values())
                if enemy_dead > best_damage:
                    best_damage = enemy_dead
                    best_composition = attacker_comp
                    best_split = (inf_pct, cav_pct, arc_pct)
        
        # Simulate with optimal composition
        defender_comp = make_composition('enemigos', total_enemy_troops, 0.5, 0.2)
        attacker_heroes = BattleHeroes()
        attacker_heroes._damage_boost = 1.25
        defender_heroes = BattleHeroes()
        defender_heroes._damage_boost = 1.25
        baseline_result = BattleCalculator.simulate_battle(best_composition, attacker_heroes, defender_comp, defender_heroes)

        recommendations = f"{get_text('battle_simulation', lang)}\n\n"
        recommendations += f"{get_text('optimal_composition', lang)}\n"
        recommendations += f"• {get_text('infantry', lang)}: {best_split[0]*100:.0f}% | {get_text('cavalry', lang)}: {best_split[1]*100:.0f}% | {get_text('archers', lang)}: {best_split[2]*100:.0f}%\n\n"
        
        outcome = get_text('victory', lang) if baseline_result.attacker_wins else get_text('defeat', lang)
        recommendations += f"{get_text('expected_result', lang)}: {outcome}\n"
        recommendations += f"{get_text('turns_to_resolution', lang)}: {baseline_result.turns_to_win_attacker if baseline_result.attacker_wins else baseline_result.turns_to_win_defender}\n\n"

        # If battle is lost, show what's needed to win
        if not baseline_result.attacker_wins:
            recommendations += f"{get_text('what_you_need', lang)}\n\n"
            
            # Find minimum bonus for EACH stat independently
            # Test in rounds of 5% increments (5%, 10%, 15%, 20%)
            # Apply 2.5x multiplier internally to match Kingshot's bonus scaling
            # Collect all winning scenarios and show the cheapest option
            
            winning_scenarios = []
            
            # Test each bonus type individually: ONLY 10% and 20%
            # Apply 2.5x multiplier internally to match Kingshot's bonus scaling
            # Collect all winning scenarios to find the cheapest option
            
            # Test 1: Troop increase only
            print(f"[DEBUG] Testing troop increases (10%, 20%)...")
            for bonus_pct in [10, 20]:
                try:
                    test_troops = int(total_troops * (1.0 + bonus_pct / 100.0))
                    test_comp = make_composition('aliados', test_troops, best_split[0], best_split[1])
                    test_attacker_heroes = BattleHeroes()
                    test_attacker_heroes._damage_boost = 1.25
                    test_defender_heroes = BattleHeroes()
                    test_defender_heroes._damage_boost = 1.25
                    test_result = BattleCalculator.simulate_battle(test_comp, test_attacker_heroes, defender_comp, test_defender_heroes)
                    
                    if test_result.attacker_wins:
                        winning_scenarios.append({
                            'type': 'Tropas',
                            'bonus': bonus_pct,
                            'detail': f"+{bonus_pct}% tropas → {test_troops:,}"
                        })
                        print(f"[DEBUG] ✓ Tropas +{bonus_pct}% WINS")
                        break  # Found minimum for this type
                except Exception as e:
                    print(f"[DEBUG] Error testing troops +{bonus_pct}%: {e}")
            
            # Test 2-5: Individual stats (attack, lethality, defense, health)
            for stat_key, stat_text_key in [('attack', 'attack'), ('lethality', 'lethality'), ('defense', 'defense'), ('health', 'health')]:
                stat_label = get_text(stat_text_key, lang)
                print(f"[DEBUG] Testing {stat_label} (10%, 20%)...")
                for bonus_pct in [10, 20]:
                    try:
                        actual_bonus = float(bonus_pct) * bonus_multiplier  # Apply troop level multiplier
                        bonus_mods = {
                            'attack': actual_bonus if stat_key == 'attack' else 0.0,
                            'lethality': actual_bonus if stat_key == 'lethality' else 0.0,
                            'defense': actual_bonus if stat_key == 'defense' else 0.0,
                            'health': actual_bonus if stat_key == 'health' else 0.0
                        }
                        test_comp = make_composition('aliados', total_troops, best_split[0], best_split[1], bonus_mods)
                        
                        # Debug: Print actual stats being tested
                        print(f"[DEBUG] Testing {stat_label} +{bonus_pct}% (actual bonus: +{actual_bonus}%)")
                        print(f"[DEBUG] Attacker Infantry stats: Atk {test_comp.infantry.attack:.1f}% | Let {test_comp.infantry.lethality:.1f}% | Def {test_comp.infantry.defense:.1f}% | HP {test_comp.infantry.health:.1f}%")
                        print(f"[DEBUG] Defender Infantry stats: Atk {defender_comp.infantry.attack:.1f}% | Let {defender_comp.infantry.lethality:.1f}% | Def {defender_comp.infantry.defense:.1f}% | HP {defender_comp.infantry.health:.1f}%")
                        
                        test_attacker_heroes = BattleHeroes()
                        test_attacker_heroes._damage_boost = 1.25
                        test_defender_heroes = BattleHeroes()
                        test_defender_heroes._damage_boost = 1.25
                        test_result = BattleCalculator.simulate_battle(test_comp, test_attacker_heroes, defender_comp, test_defender_heroes)
                        
                        print(f"[DEBUG] Result: Attacker wins = {test_result.attacker_wins}, turns = {test_result.turns_to_win_attacker if test_result.attacker_wins else test_result.turns_to_win_defender}")
                        
                        if test_result.attacker_wins:
                            winning_scenarios.append({
                                'type': stat_label,
                                'bonus': bonus_pct,
                                'detail': f"+{bonus_pct}% {stat_label.lower()}"
                            })
                            print(f"[DEBUG] ✓ {stat_label} +{bonus_pct}% WINS")
                            break
                    except Exception as e:
                        print(f"[DEBUG] Error testing {stat_label} +{bonus_pct}%: {e}")
            
            # Test 6-7: Enemy debuffs (attack, defense)
            for stat_key, stat_label in [('attack', 'Reducción ataque enemigo'), ('defense', 'Reducción defensa enemigo')]:
                print(f"[DEBUG] Testing {stat_label} (10%, 20%)...")
                for bonus_pct in [10, 20]:
                    try:
                        actual_debuff = float(bonus_pct) * bonus_multiplier
                        debuff_mods = {
                            'attack': -actual_debuff if stat_key == 'attack' else 0.0,
                            'lethality': 0.0,
                            'defense': -actual_debuff if stat_key == 'defense' else 0.0,
                            'health': 0.0
                        }
                        debuffed_defender = make_composition('enemigos', total_enemy_troops, 0.5, 0.2, debuff_mods)
                        test_comp = make_composition('aliados', total_troops, best_split[0], best_split[1])
                        test_attacker_heroes = BattleHeroes()
                        test_attacker_heroes._damage_boost = 1.25
                        test_defender_heroes = BattleHeroes()
                        test_defender_heroes._damage_boost = 1.25
                        test_result = BattleCalculator.simulate_battle(test_comp, test_attacker_heroes, debuffed_defender, test_defender_heroes)
                        
                        if test_result.attacker_wins:
                            winning_scenarios.append({
                                'type': stat_label,
                                'bonus': bonus_pct,
                                'detail': f"-{bonus_pct}% {stat_key} enemigo"
                            })
                            print(f"[DEBUG] ✓ {stat_label} -{bonus_pct}% WINS")
                            break
                    except Exception as e:
                        print(f"[DEBUG] Error testing {stat_label} -{bonus_pct}%: {e}")
            
            # Display results
            recommendations += f"{get_text('composition_damage', lang)}\n"
            recommendations += f"• {get_text('infantry', lang)} {best_split[0]*100:.0f}% | {get_text('cavalry', lang)} {best_split[1]*100:.0f}% | {get_text('archers', lang)} {best_split[2]*100:.0f}%\n\n"
            
            recommendations += f"{get_text('cheapest_option', lang)}\n"
            
            if winning_scenarios:
                # Find cheapest winning scenario (lowest bonus percentage)
                cheapest = min(winning_scenarios, key=lambda x: x['bonus'])
                recommendations += f"✅ **{cheapest['type']}: {cheapest['detail']}**\n\n"
                
                # Show all other winning options
                if len(winning_scenarios) > 1:
                    recommendations += f"{get_text('other_options', lang)}\n"
                    for scenario in winning_scenarios:
                        if scenario != cheapest:
                            recommendations += f"• {scenario['type']}: {scenario['detail']}\n"
            else:
                # No winning scenario found with bonuses up to 20%
                recommendations += f"{get_text('no_win_possible', lang)}\n"
                recommendations += f"{get_text('improve_recommendation', lang)}\n"
        
        recommendations += f"\n\n{get_text('note', lang)}"
        try:
            print(f"[DEBUG] Recommendations output: {recommendations}")
        except Exception:
            pass
        return recommendations
    
    @app_commands.command(name="help")
    async def help_command(self, interaction: discord.Interaction):
        """Help command."""
        # Track command usage
        tracker = get_tracker()
        tracker.track_command(
            "help",
            interaction.user.id,
            str(interaction.user),
            interaction.guild_id if interaction.guild else None,
            interaction.guild.name if interaction.guild else None
        )
        
        lang = get_user_language(interaction.user.id)
        
        embed = discord.Embed(
            title=get_text('help_title', lang),
            description=get_text('help_description', lang),
            color=discord.Color.blue()
        )
        
        # /calculate command
        embed.add_field(
            name="⚔️ /calculate [troop_level]",
            value=get_text('help_calculate', lang),
            inline=False
        )
        
        # /language command
        embed.add_field(
            name="🌍 /language [language]",
            value=get_text('help_language', lang),
            inline=False
        )
        
        # Screenshot format
        embed.add_field(
            name=get_text('help_screenshots_title', lang),
            value=get_text('help_screenshots_content', lang),
            inline=False
        )
        
        # Game mechanics
        embed.add_field(
            name=get_text('help_mechanics_title', lang),
            value=get_text('help_mechanics_content', lang),
            inline=False
        )
        
        footer_text = f"{get_text('help_footer', lang)} | {get_text('donation_footer', lang)}"
        embed.set_footer(text=footer_text)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="language")
    @app_commands.describe(language="Select your preferred language")
    @app_commands.choices(language=[
        app_commands.Choice(name="English", value="en"),
        app_commands.Choice(name="Español", value="es"),
        app_commands.Choice(name="Português", value="pt"),
        app_commands.Choice(name="Français", value="fr"),
        app_commands.Choice(name="Deutsch", value="de"),
        app_commands.Choice(name="Nederlands", value="nl"),
        app_commands.Choice(name="العربية", value="ar"),
    ])
    async def language_command(self, interaction: discord.Interaction, language: str):
        """Change bot language preference."""
        # Track command usage
        tracker = get_tracker()
        tracker.track_command(
            "language",
            interaction.user.id,
            str(interaction.user),
            interaction.guild_id if interaction.guild else None,
            interaction.guild.name if interaction.guild else None
        )
        
        set_user_language(interaction.user.id, language)
        
        # Get language name
        lang_names = get_available_languages()
        lang_name = lang_names.get(language, language)
        
        # Response messages in the selected language
        messages = {
            'en': f"✅ Language changed to **{lang_name}**",
            'es': f"✅ Idioma cambiado a **{lang_name}**",
            'pt': f"✅ Idioma alterado para **{lang_name}**",
            'fr': f"✅ Langue changée en **{lang_name}**",
            'de': f"✅ Sprache geändert zu **{lang_name}**",
            'nl': f"✅ Taal gewijzigd naar **{lang_name}**",
            'ar': f"✅ تم تغيير اللغة إلى **{lang_name}**",
        }
        
        message = messages.get(language, f"✅ Language changed to **{lang_name}**")
        await interaction.response.send_message(message, ephemeral=True)
    
    @app_commands.command(name="stats")
    async def stats_command(self, interaction: discord.Interaction):
        """Show bot usage statistics (owner only)."""
        # Only allow bot owner to see stats
        if not hasattr(self.bot, 'owner_id') or interaction.user.id != self.bot.owner_id:
            await interaction.response.send_message("❌ This command is only available to the bot owner.", ephemeral=True)
            return
        
        tracker = get_tracker()
        stats = tracker.get_stats_summary()
        top_users = tracker.get_top_users(5)
        top_guilds = tracker.get_top_guilds(10)
        
        embed = discord.Embed(
            title="📊 Bot Usage Statistics",
            color=discord.Color.blue()
        )
        
        # General stats
        embed.add_field(
            name="📈 General",
            value=f"**Total Commands**: {stats['total_commands']:,}\n"
                  f"**Unique Users**: {stats['total_users']:,}\n"
                  f"**Total Servers**: {stats['total_guilds']:,}\n"
                  f"**Active Servers**: {len(self.bot.guilds):,}",
            inline=False
        )
        
        # Command breakdown
        if stats['commands']:
            cmd_list = "\n".join([f"**/{cmd}**: {count:,}" for cmd, count in stats['commands'].items()])
            embed.add_field(
                name="⚔️ Command Usage",
                value=cmd_list,
                inline=False
            )
        
        # Top users
        if top_users:
            user_list = "\n".join([
                f"{i+1}. **{u['name']}** - {u['command_count']:,} commands"
                for i, u in enumerate(top_users[:5])
            ])
            embed.add_field(
                name="🏆 Top Users",
                value=user_list,
                inline=False
            )
        
        # Top guilds
        if top_guilds:
            guild_list = "\n".join([
                f"{i+1}. **{g['name']}** - {g['command_count']:,} commands"
                for i, g in enumerate(top_guilds[:10])
            ])
            embed.add_field(
                name="🏅 Top Servers",
                value=guild_list,
                inline=False
            )
        
        embed.set_footer(text=f"Started tracking: {stats['started_at'][:10]}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    """Setup function to load this cog."""
    await bot.add_cog(BattleCommands(bot))
