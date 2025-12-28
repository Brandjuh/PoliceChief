"""
Staff view - personnel management
Author: BrandjuhNL
"""

import discord

from .base import BaseView
from .helpers import build_info_embed, build_error_embed, build_success_embed, format_credits, format_time_remaining
from ..models import PlayerProfile


class StaffView(BaseView):
    """Staff management view."""
    
    def __init__(self, cog, profile: PlayerProfile, user: discord.User):
        super().__init__(timeout=300)
        self.cog = cog
        self.profile = profile
        self.user = user
        
        # Get available staff
        self.available_staff = cog.content_loader.get_available_staff(profile.station_level)
        
        if self.available_staff:
            self.add_item(StaffSelect(self.available_staff))
        
        self.add_item(BackButton())
    
    async def build_embed(self) -> discord.Embed:
        """Build the staff embed."""
        balance = await self.cog.game_engine.get_balance(self.user.id)
        display_balance = balance if balance is not None else 0
        
        embed = build_info_embed(
            "👮 Staff Management",
            f"Manage your personnel\nBalance: {format_credits(display_balance)} credits"
        )
        
        # Show hired staff
        if self.profile.staff_roster:
            staff_list = []
            for staff_id, quantity in self.profile.staff_roster.items():
                staff = self.cog.content_loader.staff.get(staff_id)
                if staff:
                    status = "🟢" if self.profile.is_staff_available(staff_id) else "🔴"
                    cooldown_text = ""
                    if staff_id in self.profile.staff_cooldowns:
                        cooldown_text = f" ({format_time_remaining(self.profile.staff_cooldowns[staff_id])})"
                    staff_list.append(f"{status} {staff.name} x{quantity}{cooldown_text}")
            
            if staff_list:
                embed.add_field(
                    name="Your Staff",
                    value="\n".join(staff_list[:10]),  # Show max 10
                    inline=False
                )
        else:
            embed.add_field(
                name="Your Staff",
                value="No staff hired yet",
                inline=False
            )
        
        # Show available to hire
        if self.available_staff:
            hire_list = []
            for staff in self.available_staff[:5]:
                hire_list.append(
                    f"**{staff.name}** - {format_credits(staff.hire_cost)} credits"
                )
            
            embed.add_field(
                name="Available to Hire",
                value="\n".join(hire_list),
                inline=False
            )
        
        embed.set_footer(text="Select staff from the dropdown to hire")
        
        return embed
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Validate interaction."""
        return await self.cog.controller.validate_interaction(interaction, self.profile.user_id)


class StaffSelect(discord.ui.Select):
    """Staff selection dropdown."""
    
    def __init__(self, staff_list):
        options = []
        for staff in staff_list[:25]:  # Max 25 options
            options.append(
                discord.SelectOption(
                    label=staff.name[:100],
                    value=staff.id,
                    description=f"Cost: {staff.hire_cost} credits",
                    emoji="👮"
                )
            )
        
        super().__init__(
            placeholder="Select staff to hire...",
            options=options,
            custom_id="pc:staff:select_staff:"
        )
    
    async def callback(self, interaction: discord.Interaction):
        staff_id = self.values[0]
        staff = self.view.cog.content_loader.staff.get(staff_id)
        
        if not staff:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Staff type not found"),
                ephemeral=True
            )
            return
        
        # Check balance
        balance = await self.view.cog.game_engine.get_balance(interaction.user.id)
        if balance is None:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Failed to check balance"),
                ephemeral=True
            )
            return

        if balance < staff.hire_cost:
            await interaction.response.send_message(
                embed=build_error_embed(
                    "Insufficient Funds",
                    f"You need {format_credits(staff.hire_cost)} credits to hire {staff.name}"
                ),
                ephemeral=True
            )
            return
        
        # Hire staff
        bank_success, new_balance = await self.view.cog.game_engine.apply_bank_transaction(
            interaction.user.id,
            -staff.hire_cost,
            f"Hired staff: {staff.name}"
        )
        
        if not bank_success:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Hiring failed"),
                ephemeral=True
            )
            return
        
        # Add staff to profile
        self.view.profile.add_staff(staff_id, 1)
        await self.view.cog.repository.save_profile(self.view.profile)
        
        # Show success and refresh
        success_embed = build_success_embed(
            "Staff Hired!",
            f"Successfully hired {staff.name} for {format_credits(staff.hire_cost)} credits"
        )
        success_embed.add_field(
            name="New Balance",
            value=f"{format_credits(new_balance)} credits",
            inline=True
        )
        
        # Refresh view
        new_view = StaffView(self.view.cog, self.view.profile, self.view.user)
        new_embed = await new_view.build_embed()

        await interaction.response.edit_message(embed=new_embed, view=new_view)
        new_view.attach_message(interaction.message)
        await interaction.followup.send(embed=success_embed, ephemeral=True)


class BackButton(discord.ui.Button):
    """Back to dashboard button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Back to Dashboard",
            custom_id="pc:staff:dashboard:",
            emoji="🏠"
        )
    
    async def callback(self, interaction: discord.Interaction):
        from .dashboard import DashboardView
        view = DashboardView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)
        view.attach_message(interaction.message)
