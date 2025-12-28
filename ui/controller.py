"""
Interaction controller - routes UI interactions
Author: BrandjuhNL
"""

import discord
import logging
from typing import Optional

from .helpers import build_error_embed

log = logging.getLogger("red.policechief.controller")


class InteractionController:
    """Central controller for routing UI interactions."""
    
    def __init__(self, cog):
        self.cog = cog
        self.bot = cog.bot
        self.repository = cog.repository
        self.game_engine = cog.game_engine
        self.content = cog.content_loader
        self.tick_engine = cog.tick_engine
    
    async def validate_interaction(
        self,
        interaction: discord.Interaction,
        profile_user_id: int
    ) -> bool:
        """
        Validate that the interaction user owns the profile.
        Sends ephemeral error if not.
        Returns True if valid.
        """
        if interaction.user.id != profile_user_id:
            await interaction.response.send_message(
                embed=build_error_embed(
                    "Not Your Menu",
                    "This menu belongs to someone else!"
                ),
                ephemeral=True
            )
            return False
        return True
    
    def parse_custom_id(self, custom_id: str) -> tuple:
        """
        Parse custom_id with format: pc:<view>:<action>:<payload>
        Returns (view, action, payload)
        """
        parts = custom_id.split(":", 3)
        if len(parts) < 3:
            return None, None, None
        
        prefix = parts[0]
        view = parts[1]
        action = parts[2]
        payload = parts[3] if len(parts) > 3 else ""
        
        if prefix != "pc":
            return None, None, None
        
        return view, action, payload
