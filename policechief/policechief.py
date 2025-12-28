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
    
    @commands.group(name="pc")
    async def policechief(self, ctx: commands.Context):
        """PoliceChief commands."""
        pass
    
    @policechief.command(name="menu")
    async def menu(self, ctx: commands.Context):
        """Open your police station dashboard."""
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
        if profile.dashboard_message_id and profile.dashboard_channel_id:
            channel = self.bot.get_channel(profile.dashboard_channel_id)
            if channel and channel.id == ctx.channel.id:
                existing_channel = channel

        if existing_channel:
            try:
                channel = self.bot.get_channel(profile.dashboard_channel_id)
                if channel:
                    try:
                        message = await channel.fetch_message(profile.dashboard_message_id)
                        await message.edit(embed=embed, view=view)
                        await ctx.send(
                            f"📊 Dashboard refreshed. [Open your dashboard]({message.jump_url})",
                            suppress_embeds=True
                        )
                        return
                    except discord.NotFound:
                        pass
            except Exception as e:
                log.warning(f"Failed to update existing dashboard message: {e}")

        # Send new message
        message = await ctx.send(embed=embed, view=view)
        view.attach_message(message)

        # Save message ID for future updates
        profile.dashboard_message_id = message.id
        profile.dashboard_channel_id = ctx.channel.id
        await self.repository.save_profile(profile)
    
    @policechief.command(name="start")
    async def start(self, ctx: commands.Context):
        """Start your police station (alias for menu)."""
        await ctx.invoke(self.menu)
    
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
