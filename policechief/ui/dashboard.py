"""
Main dashboard view
Author: BrandjuhNL
"""

import discord
from typing import Optional

from .base import BaseView
from .helpers import build_info_embed, format_credits
from ..models import PlayerProfile


class DashboardView(BaseView):
    """Main dashboard menu view."""
    
    def __init__(self, cog, profile: PlayerProfile, user: discord.User):
        super().__init__(timeout=300)
        self.cog = cog
        self.profile = profile
        self.user = user
        
        # Add buttons
        self.add_item(StatusButton())
        self.add_item(DispatchButton())
        self.add_item(FleetButton())
        self.add_item(StaffButton())
        self.add_item(DistrictsButton())
        self.add_item(UpgradesButton())
        
        # Automation button (locked unless upgrade owned)
        if profile.has_upgrade("dispatch_center"):
            self.add_item(AutomationButton())
        else:
            self.add_item(AutomationLockedButton())
        
        self.add_item(HelpButton())
        self.add_item(RefreshButton())
    
    async def build_embed(self) -> discord.Embed:
        """Build the dashboard embed."""
        # Get current balance
        balance = await self.cog.game_engine.get_balance(self.user.id)
        if balance is None:
            balance = 0
        
        embed = build_info_embed(
            f"🚔 {self.profile.station_name}",
            f"Welcome, Chief {self.user.display_name}!"
        )
        
        embed.add_field(
            name="Station Info",
            value=(
                f"Level: {self.profile.station_level}\n"
                f"District: {self.profile.current_district.title()}\n"
                f"Reputation: {self.profile.reputation}/100"
            ),
            inline=True
        )
        
        embed.add_field(
            name="Resources",
            value=(
                f"Balance: {format_credits(balance)} credits\n"
                f"Heat: {self.profile.heat_level}/100\n"
                f"Automation: {'ON' if self.profile.automation_enabled else 'OFF'}"
            ),
            inline=True
        )
        
        # Count vehicles and staff
        total_vehicles = sum(self.profile.owned_vehicles.values())
        total_staff = sum(self.profile.staff_roster.values())
        
        embed.add_field(
            name="Fleet & Staff",
            value=(
                f"Vehicles: {total_vehicles}\n"
                f"Staff: {total_staff}\n"
                f"Missions: {self.profile.total_missions_completed} completed"
            ),
            inline=True
        )
        
        embed.set_footer(text="Use the buttons below to navigate")
        
        return embed
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Validate interaction."""
        return await self.cog.controller.validate_interaction(interaction, self.profile.user_id)


class StatusButton(discord.ui.Button):
    """Status button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Status",
            custom_id="pc:dashboard:status:",
            emoji="📊"
        )
    
    async def callback(self, interaction: discord.Interaction):
        from .status import StatusView
        view = StatusView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)


class DispatchButton(discord.ui.Button):
    """Dispatch button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Dispatch",
            custom_id="pc:dashboard:dispatch:",
            emoji="🚨"
        )
    
    async def callback(self, interaction: discord.Interaction):
        from .dispatch import DispatchView
        view = DispatchView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)


class FleetButton(discord.ui.Button):
    """Fleet button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Fleet",
            custom_id="pc:dashboard:fleet:",
            emoji="🚓"
        )
    
    async def callback(self, interaction: discord.Interaction):
        from .fleet import FleetView
        view = FleetView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)


class StaffButton(discord.ui.Button):
    """Staff button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Staff",
            custom_id="pc:dashboard:staff:",
            emoji="👮"
        )
    
    async def callback(self, interaction: discord.Interaction):
        from .staff import StaffView
        view = StaffView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)


class DistrictsButton(discord.ui.Button):
    """Districts button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Districts",
            custom_id="pc:dashboard:districts:",
            emoji="🗺️"
        )
    
    async def callback(self, interaction: discord.Interaction):
        from .districts import DistrictsView
        view = DistrictsView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)


class UpgradesButton(discord.ui.Button):
    """Upgrades button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Upgrades",
            custom_id="pc:dashboard:upgrades:",
            emoji="⚡"
        )
    
    async def callback(self, interaction: discord.Interaction):
        from .upgrades import UpgradesView
        view = UpgradesView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)


class AutomationButton(discord.ui.Button):
    """Automation button (unlocked)."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Automation",
            custom_id="pc:dashboard:automation:",
            emoji="🤖"
        )
    
    async def callback(self, interaction: discord.Interaction):
        from .automation import AutomationView
        view = AutomationView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)


class AutomationLockedButton(discord.ui.Button):
    """Automation button (locked)."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Automation",
            custom_id="pc:dashboard:automation_locked:",
            emoji="🔒",
            disabled=True
        )


class HelpButton(discord.ui.Button):
    """Help button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Help",
            custom_id="pc:dashboard:help:",
            emoji="❓"
        )
    
    async def callback(self, interaction: discord.Interaction):
        embed = build_info_embed(
            "PoliceChief Help",
            (
                "**How to Play:**\n"
                "• Build your police station by purchasing vehicles and hiring staff\n"
                "• Dispatch units to missions to earn credits\n"
                "• Unlock new districts for better rewards\n"
                "• Purchase upgrades to improve efficiency\n"
                "• Enable automation for passive income\n\n"
                "**Tips:**\n"
                "• Keep your balance above 100 credits to dispatch missions\n"
                "• Higher reputation improves mission success rates\n"
                "• Watch your heat level - too high means tougher missions\n"
                "• Staff and vehicles have cooldowns after missions"
            )
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RefreshButton(discord.ui.Button):
    """Refresh button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Refresh",
            custom_id="pc:dashboard:refresh:",
            emoji="🔄"
        )
    
    async def callback(self, interaction: discord.Interaction):
        # Reload profile and rebuild view
        profile = await self.view.cog.repository.get_profile(self.view.user.id)
        if profile:
            # Process catch-up ticks
            messages = await self.view.cog.tick_engine.process_catchup(profile)
            
            new_view = DashboardView(self.view.cog, profile, self.view.user)
            embed = await new_view.build_embed()
            
            # Add catch-up messages to embed if any
            if messages:
                embed.add_field(
                    name="Recent Activity",
                    value="\n".join(messages[:3]),  # Show max 3 messages
                    inline=False
                )
            
            await interaction.response.edit_message(embed=embed, view=new_view)
        else:
            await interaction.response.send_message(
                "Error refreshing profile",
                ephemeral=True
            )
