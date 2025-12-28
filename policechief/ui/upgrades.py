"""
Upgrades view - station upgrades
Author: BrandjuhNL
"""

import discord
from redbot.core import bank

from .helpers import build_info_embed, build_error_embed, build_success_embed, format_credits
from ..models import PlayerProfile


class UpgradesView(discord.ui.View):
    """Upgrades management view."""
    
    def __init__(self, cog, profile: PlayerProfile, user: discord.User):
        super().__init__(timeout=300)
        self.cog = cog
        self.profile = profile
        self.user = user
        
        # Get available upgrades
        self.available_upgrades = cog.content_loader.get_available_upgrades(
            profile.station_level,
            profile.owned_upgrades
        )
        
        if self.available_upgrades:
            self.add_item(UpgradeSelect(self.available_upgrades))
        
        self.add_item(BackButton())
    
    async def build_embed(self) -> discord.Embed:
        """Build the upgrades embed."""
        try:
            balance = await bank.get_balance(self.user.id)
        except:
            balance = 0
        
        embed = build_info_embed(
            "⚡ Station Upgrades",
            f"Purchase upgrades to improve your station\nBalance: {format_credits(balance)} credits"
        )
        
        # Show owned upgrades
        if self.profile.owned_upgrades:
            upgrade_list = []
            for upgrade_id in self.profile.owned_upgrades:
                upgrade = self.cog.content_loader.upgrades.get(upgrade_id)
                if upgrade:
                    upgrade_list.append(f"✅ {upgrade.name}")
            
            if upgrade_list:
                embed.add_field(
                    name="Owned Upgrades",
                    value="\n".join(upgrade_list[:10]),  # Show max 10
                    inline=False
                )
        else:
            embed.add_field(
                name="Owned Upgrades",
                value="No upgrades purchased yet",
                inline=False
            )
        
        # Show available to purchase
        if self.available_upgrades:
            purchase_list = []
            for upgrade in self.available_upgrades[:5]:
                purchase_list.append(
                    f"**{upgrade.name}** - {format_credits(upgrade.cost)} credits\n"
                    f"  {upgrade.get_effect_description()}"
                )
            
            embed.add_field(
                name="Available Upgrades",
                value="\n".join(purchase_list),
                inline=False
            )
        else:
            embed.add_field(
                name="Available Upgrades",
                value="All available upgrades purchased!",
                inline=False
            )
        
        embed.set_footer(text="Select an upgrade from the dropdown to purchase")
        
        return embed
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Validate interaction."""
        return await self.cog.controller.validate_interaction(interaction, self.profile.user_id)


class UpgradeSelect(discord.ui.Select):
    """Upgrade selection dropdown."""
    
    def __init__(self, upgrades):
        options = []
        for upgrade in upgrades[:25]:  # Max 25 options
            options.append(
                discord.SelectOption(
                    label=upgrade.name[:100],
                    value=upgrade.id,
                    description=f"Cost: {upgrade.cost} credits",
                    emoji="⚡"
                )
            )
        
        super().__init__(
            placeholder="Select an upgrade to purchase...",
            options=options,
            custom_id="pc:upgrades:select_upgrade:"
        )
    
    async def callback(self, interaction: discord.Interaction):
        upgrade_id = self.values[0]
        upgrade = self.view.cog.content_loader.upgrades.get(upgrade_id)
        
        if not upgrade:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Upgrade not found"),
                ephemeral=True
            )
            return
        
        # Check if already owned
        if upgrade_id in self.view.profile.owned_upgrades:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "You already own this upgrade"),
                ephemeral=True
            )
            return
        
        # Check balance
        try:
            balance = await bank.get_balance(interaction.user.id)
        except:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Failed to check balance"),
                ephemeral=True
            )
            return
        
        if balance < upgrade.cost:
            await interaction.response.send_message(
                embed=build_error_embed(
                    "Insufficient Funds",
                    f"You need {format_credits(upgrade.cost)} credits to purchase {upgrade.name}"
                ),
                ephemeral=True
            )
            return
        
        # Purchase upgrade
        bank_success, new_balance = await self.view.cog.game_engine.apply_bank_transaction(
            interaction.user.id,
            -upgrade.cost,
            f"Purchased upgrade: {upgrade.name}"
        )
        
        if not bank_success:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Purchase failed"),
                ephemeral=True
            )
            return
        
        # Add upgrade to profile
        self.view.profile.owned_upgrades.append(upgrade_id)
        await self.view.cog.repository.save_profile(self.view.profile)
        
        # Show success and refresh
        success_embed = build_success_embed(
            "Upgrade Purchased!",
            f"Successfully purchased {upgrade.name} for {format_credits(upgrade.cost)} credits\n\n"
            f"Effect: {upgrade.get_effect_description()}"
        )
        success_embed.add_field(
            name="New Balance",
            value=f"{format_credits(new_balance)} credits",
            inline=True
        )
        
        # Refresh view
        new_view = UpgradesView(self.view.cog, self.view.profile, self.view.user)
        new_embed = await new_view.build_embed()
        
        await interaction.response.edit_message(embed=new_embed, view=new_view)
        await interaction.followup.send(embed=success_embed, ephemeral=True)


class BackButton(discord.ui.Button):
    """Back to dashboard button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Back to Dashboard",
            custom_id="pc:upgrades:dashboard:",
            emoji="🏠"
        )
    
    async def callback(self, interaction: discord.Interaction):
        from .dashboard import DashboardView
        view = DashboardView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)
