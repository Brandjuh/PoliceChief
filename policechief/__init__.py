"""
PoliceChief - An idle/management game cog for Red-DiscordBot
Author: BrandjuhNL
"""

from .policechief import PoliceChief

__red_end_user_data_statement__ = "This cog stores user game profiles and progress data."


async def setup(bot):
    """Load the PoliceChief cog."""
    cog = PoliceChief(bot)
    await bot.add_cog(cog)
    await cog.initialize()
