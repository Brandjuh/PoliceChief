"""
Districts view - district unlocking and selection
Author: BrandjuhNL
"""

import discord
from redbot.core import bank

from .helpers import build_info_embed, build_error_embed, build_success_embed, format_credits
from ..models import PlayerProfile


class DistrictsView(discord.ui.View):
    """Districts management view."""
    
    def __init__(self, cog, profile: PlayerProfile, user: discord.User):
        super().__init__(timeout=300)
        self.cog = cog
        self.profile = profile
        self.user = user
        
        # Get available districts
        self.available_districts = cog.content_loader.get_available_districts(profile.station_level)
        
        if self.available_districts:
            self.add_item(DistrictSelect(self.available_districts, profile))
        
        self.add_item(BackButton())
    
    async def build_embed(self) -> discord.Embed:
        """Build the districts embed."""
        try:
            balance = await bank.get_balance(self.user.id)
        except:
            balance = 0
        
        embed = build_info_embed(
            "🗺️ District Management",
            f"Unlock and manage districts\nBalance: {format_credits(balance)} credits"
        )
        
        embed.add_field(
            name="Current District",
            value=f"📍 {self.profile.current_district.title()}",
            inline=False
        )
        
        # Show unlocked districts
        if self.profile.unlocked_districts:
            district_list = []
            for district_id in self.profile.unlocked_districts:
                district = self.cog.content_loader.districts.get(district_id)
                if district:
                    current = "📍" if district_id == self.profile.current_district else "🔓"
                    district_list.append(f"{current} {district.name}")
            
            embed.add_field(
                name="Unlocked Districts",
                value="\n".join(district_list),
                inline=False
            )
        
        # Show available to unlock
        locked_districts = [
            d for d in self.available_districts
            if d.id not in self.profile.unlocked_districts
        ]
        
        if locked_districts:
            unlock_list = []
            for district in locked_districts[:5]:
                unlock_list.append(
                    f"🔒 **{district.name}** - {format_credits(district.unlock_cost)} credits"
                )
            
            embed.add_field(
                name="Available to Unlock",
                value="\n".join(unlock_list),
                inline=False
            )
        
        embed.set_footer(text="Select a district from the dropdown to unlock or switch to it")
        
        return embed
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Validate interaction."""
        return await self.cog.controller.validate_interaction(interaction, self.profile.user_id)


class DistrictSelect(discord.ui.Select):
    """District selection dropdown."""
    
    def __init__(self, districts, profile):
        options = []
        for district in districts[:25]:  # Max 25 options
            is_unlocked = district.id in profile.unlocked_districts
            is_current = district.id == profile.current_district
            
            label = district.name[:100]
            if is_current:
                label = f"📍 {label} (Current)"
            elif is_unlocked:
                label = f"🔓 {label}"
            else:
                label = f"🔒 {label}"
            
            options.append(
                discord.SelectOption(
                    label=label,
                    value=district.id,
                    description=f"Unlock: {district.unlock_cost} credits" if not is_unlocked else "Unlocked",
                    emoji="🗺️"
                )
            )
        
        super().__init__(
            placeholder="Select a district...",
            options=options,
            custom_id="pc:districts:select_district:"
        )
    
    async def callback(self, interaction: discord.Interaction):
        district_id = self.values[0]
        district = self.view.cog.content_loader.districts.get(district_id)
        
        if not district:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "District not found"),
                ephemeral=True
            )
            return
        
        # Check if already unlocked
        if district_id in self.view.profile.unlocked_districts:
            # Switch to this district
            self.view.profile.current_district = district_id
            await self.view.cog.repository.save_profile(self.view.profile)
            
            success_embed = build_success_embed(
                "District Changed",
                f"Switched to {district.name}"
            )
            
            # Refresh view
            new_view = DistrictsView(self.view.cog, self.view.profile, self.view.user)
            new_embed = await new_view.build_embed()
            
            await interaction.response.edit_message(embed=new_embed, view=new_view)
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            return
        
        # Need to unlock - check balance
        try:
            balance = await bank.get_balance(interaction.user.id)
        except:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Failed to check balance"),
                ephemeral=True
            )
            return
        
        if balance < district.unlock_cost:
            await interaction.response.send_message(
                embed=build_error_embed(
                    "Insufficient Funds",
                    f"You need {format_credits(district.unlock_cost)} credits to unlock {district.name}"
                ),
                ephemeral=True
            )
            return
        
        # Unlock district
        bank_success, new_balance = await self.view.cog.game_engine.apply_bank_transaction(
            interaction.user.id,
            -district.unlock_cost,
            f"Unlocked district: {district.name}"
        )
        
        if not bank_success:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Unlock failed"),
                ephemeral=True
            )
            return
        
        # Add district to profile
        self.view.profile.unlocked_districts.append(district_id)
        self.view.profile.current_district = district_id  # Auto-switch to new district
        await self.view.cog.repository.save_profile(self.view.profile)
        
        # Show success and refresh
        success_embed = build_success_embed(
            "District Unlocked!",
            f"Successfully unlocked {district.name} for {format_credits(district.unlock_cost)} credits"
        )
        success_embed.add_field(
            name="New Balance",
            value=f"{format_credits(new_balance)} credits",
            inline=True
        )
        
        # Refresh view
        new_view = DistrictsView(self.view.cog, self.view.profile, self.view.user)
        new_embed = await new_view.build_embed()
        
        await interaction.response.edit_message(embed=new_embed, view=new_view)
        await interaction.followup.send(embed=success_embed, ephemeral=True)


class BackButton(discord.ui.Button):
    """Back to dashboard button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Back to Dashboard",
            custom_id="pc:districts:dashboard:",
            emoji="🏠"
        )
    
    async def callback(self, interaction: discord.Interaction):
        from .dashboard import DashboardView
        view = DashboardView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)
