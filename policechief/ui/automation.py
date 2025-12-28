"""
Automation view - auto-dispatch configuration
Author: BrandjuhNL
"""

import discord

from .helpers import build_info_embed, build_success_embed
from ..models import PlayerProfile


class AutomationView(discord.ui.View):
    """Automation management view."""
    
    def __init__(self, cog, profile: PlayerProfile, user: discord.User):
        super().__init__(timeout=300)
        self.cog = cog
        self.profile = profile
        self.user = user
        
        # Add toggle button
        if profile.automation_enabled:
            self.add_item(DisableAutomationButton())
        else:
            self.add_item(EnableAutomationButton())
        
        # Add policy management (simplified for MVP)
        self.add_item(BackButton())
    
    async def build_embed(self) -> discord.Embed:
        """Build the automation embed."""
        status = "🟢 ENABLED" if self.profile.automation_enabled else "🔴 DISABLED"
        
        embed = build_info_embed(
            "🤖 Automation Center",
            f"Configure automatic mission dispatch\n\nStatus: {status}"
        )
        
        embed.add_field(
            name="How Automation Works",
            value=(
                "When enabled, your station will automatically dispatch available missions "
                "every 5 minutes based on your active policies.\n\n"
                "**Requirements:**\n"
                "• Dispatch Center upgrade\n"
                "• Available vehicles and staff\n"
                "• Sufficient funds\n\n"
                "**Benefits:**\n"
                "• Passive income while offline\n"
                "• Automatic mission execution\n"
                "• Hands-free operation"
            ),
            inline=False
        )
        
        # Show active policies
        if self.profile.active_policies:
            policy_list = []
            for policy_id in self.profile.active_policies:
                policy = self.cog.content_loader.policies.get(policy_id)
                if policy:
                    policy_list.append(f"✅ {policy.name}")
            
            if policy_list:
                embed.add_field(
                    name="Active Policies",
                    value="\n".join(policy_list),
                    inline=False
                )
        else:
            embed.add_field(
                name="Active Policies",
                value="No policies active (all available missions will be considered)",
                inline=False
            )
        
        return embed
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Validate interaction."""
        return await self.cog.controller.validate_interaction(interaction, self.profile.user_id)


class EnableAutomationButton(discord.ui.Button):
    """Enable automation button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Enable Automation",
            custom_id="pc:automation:enable:",
            emoji="🟢"
        )
    
    async def callback(self, interaction: discord.Interaction):
        self.view.profile.automation_enabled = True
        await self.view.cog.repository.save_profile(self.view.profile)
        
        success_embed = build_success_embed(
            "Automation Enabled",
            "Your station will now automatically dispatch missions every 5 minutes!"
        )
        
        # Refresh view
        new_view = AutomationView(self.view.cog, self.view.profile, self.view.user)
        new_embed = await new_view.build_embed()
        
        await interaction.response.edit_message(embed=new_embed, view=new_view)
        await interaction.followup.send(embed=success_embed, ephemeral=True)


class DisableAutomationButton(discord.ui.Button):
    """Disable automation button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Disable Automation",
            custom_id="pc:automation:disable:",
            emoji="🔴"
        )
    
    async def callback(self, interaction: discord.Interaction):
        self.view.profile.automation_enabled = False
        await self.view.cog.repository.save_profile(self.view.profile)
        
        success_embed = build_success_embed(
            "Automation Disabled",
            "Your station will no longer automatically dispatch missions."
        )
        
        # Refresh view
        new_view = AutomationView(self.view.cog, self.view.profile, self.view.user)
        new_embed = await new_view.build_embed()
        
        await interaction.response.edit_message(embed=new_embed, view=new_view)
        await interaction.followup.send(embed=success_embed, ephemeral=True)


class BackButton(discord.ui.Button):
    """Back to dashboard button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Back to Dashboard",
            custom_id="pc:automation:dashboard:",
            emoji="🏠"
        )
    
    async def callback(self, interaction: discord.Interaction):
        from .dashboard import DashboardView
        view = DashboardView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)
