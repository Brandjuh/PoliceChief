"""
PoliceChief - An idle/management game cog for Red-DiscordBot
Author: BrandjuhNL
"""

import discord
import logging
from pathlib import Path
from redbot.core import commands, Config
from redbot.core.bot import Red

from .db import Repository, MigrationManager
from .services import ContentLoader, GameEngine, TickEngine
from .ui import DashboardView, InteractionController

log = logging.getLogger("red.policechief")


class PoliceChief(commands.Cog):
    """Build and manage your police station in this idle/management game."""
    
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        
        # Paths
        self.data_path = Path(__file__).parent / "data"
        self.schema_path = Path(__file__).parent / "schemas"
        self.db_path = Path(__file__).parent / "policechief.db"
        
        # Components (initialized in initialize())
        self.repository: Repository = None
        self.migration_manager: MigrationManager = None
        self.content_loader: ContentLoader = None
        self.game_engine: GameEngine = None
        self.tick_engine: TickEngine = None
        self.controller: InteractionController = None
    
    async def initialize(self):
        """Initialize the cog after loading."""
        log.info("Initializing PoliceChief cog...")
        
        # Initialize database
        self.migration_manager = MigrationManager(self.db_path)
        await self.migration_manager.initialize()
        
        # Initialize repository
        self.repository = Repository(self.db_path)
        
        # Initialize content loader
        self.content_loader = ContentLoader(self.data_path, self.schema_path)
        await self.content_loader.load_all()
        
        # Initialize game engine
        self.game_engine = GameEngine(self.bot, self.content_loader)
        
        # Initialize tick engine
        self.tick_engine = TickEngine(
            self.bot,
            self.repository,
            self.game_engine,
            self.content_loader
        )
        self.tick_engine.start()
        
        # Initialize interaction controller
        self.controller = InteractionController(self)
        
        log.info("PoliceChief cog initialized successfully")
    
    def cog_unload(self):
        """Cleanup when cog is unloaded."""
        if self.tick_engine:
            self.tick_engine.stop()
        log.info("PoliceChief cog unloaded")
    
    @commands.command(name="pc")
    async def policechief(self, ctx: commands.Context):
        """Open your police station dashboard."""
        await self._open_dashboard(ctx)

    async def _open_dashboard(self, ctx: commands.Context):
        """Shared dashboard opening logic."""
        # Get or create profile
        profile = await self.repository.get_or_create_profile(ctx.author.id)
        
        # Process catch-up ticks
        catchup_messages = await self.tick_engine.process_catchup(profile)
        
        # Reload profile after catch-up
        profile = await self.repository.get_profile(ctx.author.id)
        
        # Create dashboard view
        view = DashboardView(self, profile, ctx.author)
        embed = await view.build_embed()
        
        # Add catch-up messages if any
        if catchup_messages:
            embed.add_field(
                name="Recent Activity",
                value="\n".join(catchup_messages[:3]),
                inline=False
            )
        
        # Close any existing dashboard before opening a new one
        existing_message = None
        if profile.dashboard_message_id and profile.dashboard_channel_id:
            channel = self.bot.get_channel(profile.dashboard_channel_id)
            if channel and channel.id == ctx.channel.id:
                try:
                    message = await channel.fetch_message(profile.dashboard_message_id)
                    if message and message.components:
                        existing_message = message
                    else:
                        profile.dashboard_message_id = None
                        profile.dashboard_channel_id = None
                        await self.repository.save_profile(profile)
                except discord.NotFound:
                    profile.dashboard_message_id = None
                    profile.dashboard_channel_id = None
                    await self.repository.save_profile(profile)
                except Exception as e:
                    log.warning(f"Failed to update existing dashboard message: {e}")

        if existing_message:
            await existing_message.edit(embed=embed, view=view)
            view.attach_message(existing_message)
            await ctx.send(
                f"📊 Dashboard refreshed. [Open your dashboard]({existing_message.jump_url})",
                suppress_embeds=True
            )
            return

        # Send new message
        message = await ctx.send(embed=embed, view=view)
        view.attach_message(message)

        # Save message ID for future updates
        profile.dashboard_message_id = message.id
        profile.dashboard_channel_id = ctx.channel.id
        await self.repository.save_profile(profile)
    
    @commands.group(name="pcadmin")
    @commands.is_owner()
    async def pcadmin(self, ctx: commands.Context):
        """PoliceChief admin commands."""
        pass
    
    @pcadmin.command(name="reloadpacks")
    async def reload_packs(self, ctx: commands.Context):
        """Reload all content packs."""
        async with ctx.typing():
            await self.content_loader.load_all()
        await ctx.send(
            f"✅ Reloaded content packs:\n"
            f"• {len(self.content_loader.missions)} missions\n"
            f"• {len(self.content_loader.vehicles)} vehicles\n"
            f"• {len(self.content_loader.districts)} districts\n"
            f"• {len(self.content_loader.staff)} staff types\n"
            f"• {len(self.content_loader.upgrades)} upgrades\n"
            f"• {len(self.content_loader.policies)} policies"
        )
    
    @pcadmin.command(name="resetprofile")
    async def reset_profile(self, ctx: commands.Context, user: discord.User = None):
        """Reset a user's profile (or your own)."""
        target = user or ctx.author
        
        # Delete current profile by creating a new one
        profile = await self.repository.create_profile(target.id)
        
        await ctx.send(f"✅ Reset profile for {target.display_name}")
    
    @pcadmin.command(name="addcredits")
    async def add_credits(self, ctx: commands.Context, user: discord.User, amount: int):
        """Add credits to a user's bank account."""
        from redbot.core import bank
        
        try:
            await bank.deposit_credits(user, amount)
            new_balance = await bank.get_balance(user)
            await ctx.send(
                f"✅ Added {amount:,} credits to {user.display_name}\n"
                f"New balance: {new_balance:,} credits"
            )
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @pcadmin.command(name="setprofile")
    async def set_profile(
        self,
        ctx: commands.Context,
        user: discord.User,
        field: str,
        *,
        value: str,
    ):
        """Adjust basic profile fields for a user."""

        field = field.lower()
        profile = await self.repository.get_or_create_profile(user.id)

        try:
            if field == "station_name":
                new_name = value.strip()
                if not 3 <= len(new_name) <= 50:
                    await ctx.send("❌ Station name must be between 3 and 50 characters.")
                    return
                old_value = profile.station_name
                profile.station_name = new_name
                change_text = f"Station name: `{old_value}` → `{new_name}`"
            elif field == "station_level":
                new_level = int(value)
                if new_level < 1:
                    await ctx.send("❌ Station level must be at least 1.")
                    return
                old_value = profile.station_level
                profile.station_level = new_level
                change_text = f"Station level: {old_value} → {new_level}"
            elif field == "reputation":
                new_rep = int(value)
                if not 0 <= new_rep <= 100:
                    await ctx.send("❌ Reputation must be between 0 and 100.")
                    return
                old_value = profile.reputation
                profile.reputation = new_rep
                change_text = f"Reputation: {old_value} → {new_rep}"
            elif field == "heat":
                new_heat = int(value)
                if not 0 <= new_heat <= 100:
                    await ctx.send("❌ Heat level must be between 0 and 100.")
                    return
                old_value = profile.heat_level
                profile.heat_level = new_heat
                change_text = f"Heat level: {old_value} → {new_heat}"
            elif field == "automation":
                normalized = value.strip().lower()
                if normalized in {"true", "yes", "on", "1"}:
                    new_state = True
                elif normalized in {"false", "no", "off", "0"}:
                    new_state = False
                else:
                    await ctx.send("❌ Automation value must be true/false.")
                    return
                old_value = profile.automation_enabled
                profile.automation_enabled = new_state
                change_text = f"Automation: {'ON' if old_value else 'OFF'} → {'ON' if new_state else 'OFF'}"
            elif field == "district":
                district_id = value.strip().lower()
                if district_id not in self.content_loader.districts:
                    await ctx.send("❌ Unknown district ID.")
                    return
                old_value = profile.current_district
                profile.current_district = district_id
                if district_id not in profile.unlocked_districts:
                    profile.unlocked_districts.append(district_id)
                change_text = f"Current district: {old_value} → {district_id}"
            else:
                await ctx.send(
                    "❌ Unknown field. Use one of: station_name, station_level, reputation, heat, automation, district."
                )
                return
        except ValueError:
            await ctx.send("❌ Invalid value for the selected field.")
            return

        await self.repository.save_profile(profile)
        await ctx.send(f"✅ Updated profile for {user.display_name}\n{change_text}")
