"""
Status view - detailed station statistics
Author: BrandjuhNL
"""

import discord

from .base import BaseView
from .helpers import build_info_embed, build_error_embed, build_success_embed, format_credits
from ..models import PlayerProfile


class StatusView(BaseView):
    """Status view showing detailed statistics."""
    
    def __init__(self, cog, profile: PlayerProfile, user: discord.User):
        super().__init__(timeout=300)
        self.cog = cog
        self.profile = profile
        self.user = user

        self.add_item(RenameStationButton())
        self.add_item(BackButton())
    
    async def build_embed(self) -> discord.Embed:
        """Build the status embed."""
        # Get current balance
        balance = await self.cog.game_engine.get_balance(self.user.id)
        display_balance = balance if balance is not None else 0
        
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
                f"Balance: {format_credits(display_balance)} credits\n"
                f"Reputation: {self.profile.reputation}/100\n"
                f"Heat Level: {self.profile.heat_level}/100"
            ),
            inline=True
        )
        
        # Fleet & Staff with capacity
        vehicle_limit = self.profile.get_vehicle_capacity_limit()
        vehicle_text = (
            f"{self.profile.total_vehicle_count}/{vehicle_limit}"
            if vehicle_limit is not None
            else str(self.profile.total_vehicle_count)
        )
        staff_capacity = self.profile.get_staff_capacity(self.cog.content_loader.vehicles)
        seated_staff = self.profile.get_seated_staff_count(self.cog.content_loader.staff)
        staff_text = f"{seated_staff}/{staff_capacity}" if staff_capacity else "0/0"
        prisoner_capacity = self.profile.get_prisoner_capacity(self.cog.content_loader.vehicles)
        holding_cells = self.profile.get_holding_cell_capacity()

        embed.add_field(
            name="Fleet & Personnel",
            value=(
                f"Vehicles: {vehicle_text}\n"
                f"Staff Seats Filled: {staff_text}\n"
                f"Prisoner Transport: {prisoner_capacity} slots\n"
                f"Holding Cells: {holding_cells} (transfer to prison)\n"
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

        tick_costs = self.cog.game_engine.calculate_tick_costs(self.profile)
        
        embed.add_field(
            name="Financial Summary",
            value=(
                f"Total Income: {format_credits(self.profile.total_income_earned)}\n"
                f"Total Expenses: {format_credits(self.profile.total_expenses_paid)}\n"
                f"Net Profit: {format_credits(net_income)}"
            ),
            inline=True
        )

        embed.add_field(
            name="Recurring Costs (per 5 min)",
            value=(
                f"Salaries: {format_credits(tick_costs['salaries'])}\n"
                f"Maintenance: {format_credits(tick_costs['maintenance'])}\n"
                f"Total Burn: {format_credits(tick_costs['total'])}"
            ),
            inline=True
        )
        
        # Automation status
        dispatch_center_available = self.profile.has_automation_access()
        dispatch_tables = self.cog.game_engine.get_dispatch_table_count(self.profile)
        dispatcher_ready = "Yes" if self.cog.game_engine.has_active_dispatcher(self.profile) else "No"
        ready, message, slots = self.cog.game_engine.describe_automation_status(self.profile)
        embed.add_field(
            name="Automation",
            value=(
                f"Status: {'Enabled' if self.profile.automation_enabled else 'Disabled'}\n"
                f"Active Policies: {len(self.profile.active_policies)}\n"
                f"Dispatch Center: {'Yes' if dispatch_center_available else 'No'}\n"
                f"Dispatch Tables: {dispatch_tables}\n"
                f"Dispatcher On Duty: {dispatcher_ready}\n"
                f"Details: {message if ready else message}"
            ),
            inline=True
        )
        
        return embed
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Validate interaction."""
        return await self.cog.controller.validate_interaction(interaction, self.profile.user_id)


class RenameStationButton(discord.ui.Button):
    """Button for renaming the police station."""

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Rename Station",
            custom_id="pc:status:rename:",
            emoji="✏️"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(StationNameModal(self.view))


class StationNameModal(discord.ui.Modal):
    """Modal to change the station name."""

    def __init__(self, view: StatusView):
        super().__init__(title="Rename Your Station")
        self.view = view
        self.station_name = discord.ui.TextInput(
            label="Station Name",
            default=view.profile.station_name[:50],
            max_length=50,
            min_length=3,
            placeholder="Enter a new station name"
        )
        self.add_item(self.station_name)

    async def on_submit(self, interaction: discord.Interaction):
        new_name = self.station_name.value.strip()

        if not new_name:
            await interaction.response.send_message(
                embed=build_error_embed("Invalid Name", "Please enter a valid station name."),
                ephemeral=True
            )
            return

        self.view.profile.station_name = new_name
        await self.view.cog.repository.save_profile(self.view.profile)

        refreshed_view = StatusView(self.view.cog, self.view.profile, self.view.user)
        refreshed_embed = await refreshed_view.build_embed()
        await interaction.response.edit_message(embed=refreshed_embed, view=refreshed_view)
        refreshed_view.attach_message(interaction.message)

        await interaction.followup.send(
            embed=build_success_embed("Station Renamed", f"Your station is now called **{new_name}**."),
            ephemeral=True
        )


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
        view.attach_message(interaction.message)
