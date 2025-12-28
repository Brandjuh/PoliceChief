"""
Status view - detailed station statistics
Author: BrandjuhNL
"""

import discord
from redbot.core import bank

from .helpers import build_info_embed, format_credits
from ..models import PlayerProfile


class StatusView(discord.ui.View):
    """Status view showing detailed statistics."""
    
    def __init__(self, cog, profile: PlayerProfile, user: discord.User):
        super().__init__(timeout=300)
        self.cog = cog
        self.profile = profile
        self.user = user
        
        self.add_item(BackButton())
    
    async def build_embed(self) -> discord.Embed:
        """Build the status embed."""
        # Get current balance
        try:
            balance = await bank.get_balance(self.user.id)
        except:
            balance = 0
        
        embed = build_info_embed(
            f"📊 Station Status - {self.profile.station_name}",
            f"Detailed statistics for Chief {self.user.display_name}"
        )
        
        # Station info
        embed.add_field(
            name="Station Details",
            value=(
                f"Level: {self.profile.station_level}\n"
                f"Current District: {self.profile.current_district.title()}\n"
                f"Districts Unlocked: {len(self.profile.unlocked_districts)}"
            ),
            inline=True
        )
        
        # Resources
        embed.add_field(
            name="Resources",
            value=(
                f"Balance: {format_credits(balance)} credits\n"
                f"Reputation: {self.profile.reputation}/100\n"
                f"Heat Level: {self.profile.heat_level}/100"
            ),
            inline=True
        )
        
        # Fleet & Staff
        total_vehicles = sum(self.profile.owned_vehicles.values())
        total_staff = sum(self.profile.staff_roster.values())
        
        embed.add_field(
            name="Fleet & Personnel",
            value=(
                f"Total Vehicles: {total_vehicles}\n"
                f"Total Staff: {total_staff}\n"
                f"Upgrades Owned: {len(self.profile.owned_upgrades)}"
            ),
            inline=True
        )
        
        # Mission statistics
        total_missions = self.profile.total_missions_completed + self.profile.total_missions_failed
        success_rate = 0
        if total_missions > 0:
            success_rate = int((self.profile.total_missions_completed / total_missions) * 100)
        
        embed.add_field(
            name="Mission Statistics",
            value=(
                f"Completed: {self.profile.total_missions_completed}\n"
                f"Failed: {self.profile.total_missions_failed}\n"
                f"Success Rate: {success_rate}%"
            ),
            inline=True
        )
        
        # Financial statistics
        net_income = self.profile.total_income_earned - self.profile.total_expenses_paid
        
        embed.add_field(
            name="Financial Summary",
            value=(
                f"Total Income: {format_credits(self.profile.total_income_earned)}\n"
                f"Total Expenses: {format_credits(self.profile.total_expenses_paid)}\n"
                f"Net Profit: {format_credits(net_income)}"
            ),
            inline=True
        )
        
        # Automation status
        embed.add_field(
            name="Automation",
            value=(
                f"Status: {'Enabled' if self.profile.automation_enabled else 'Disabled'}\n"
                f"Active Policies: {len(self.profile.active_policies)}\n"
                f"Dispatch Center: {'Yes' if self.profile.has_upgrade('dispatch_center') else 'No'}"
            ),
            inline=True
        )
        
        return embed
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Validate interaction."""
        return await self.cog.controller.validate_interaction(interaction, self.profile.user_id)


class BackButton(discord.ui.Button):
    """Back to dashboard button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Back",
            custom_id="pc:status:back:",
            emoji="◀️"
        )
    
    async def callback(self, interaction: discord.Interaction):
        from .dashboard import DashboardView
        view = DashboardView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)
