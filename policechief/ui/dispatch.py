"""
Dispatch view - mission selection and execution
Author: BrandjuhNL
"""

import discord

from .base import BaseView
from .helpers import build_info_embed, build_error_embed, build_success_embed, format_credits
from ..models import PlayerProfile


class DispatchView(BaseView):
    """Dispatch view for selecting and launching missions."""
    
    def __init__(self, cog, profile: PlayerProfile, user: discord.User):
        super().__init__(timeout=300)
        self.cog = cog
        self.profile = profile
        self.user = user
        
        # Get available missions
        self.missions = cog.content_loader.get_missions_for_district(
            profile.current_district,
            profile.station_level
        )
        
        if self.missions:
            self.add_item(MissionSelect(self.missions))
        
        self.add_item(BackButton())
    
    async def build_embed(self) -> discord.Embed:
        """Build the dispatch embed."""
        balance = await self.cog.game_engine.get_balance(self.user.id)
        display_balance = balance if balance is not None else 0
        
        embed = build_info_embed(
            f"🚨 Dispatch Center - {self.profile.current_district.title()}",
            f"Select a mission to dispatch units"
        )
        
        embed.add_field(
            name="Your Resources",
            value=(
                f"Balance: {format_credits(display_balance)} credits\n"
                f"Reputation: {self.profile.reputation}/100\n"
                f"Heat: {self.profile.heat_level}/100"
            ),
            inline=False
        )
        
        if not self.missions:
            embed.add_field(
                name="No Missions Available",
                value="No missions available in this district at your current level.",
                inline=False
            )
        else:
            # Show first 3 missions as preview
            mission_list = []
            for mission in self.missions[:3]:
                can_dispatch, reason = self.cog.game_engine.can_dispatch_mission(self.profile, mission)
                status = "✅" if can_dispatch else "❌"
                mission_list.append(f"{status} **{mission.name}** - {format_credits(mission.base_reward)} credits")
            
            embed.add_field(
                name="Available Missions",
                value="\n".join(mission_list),
                inline=False
            )
        
        embed.set_footer(text="Select a mission from the dropdown to see details and dispatch")
        
        return embed
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Validate interaction."""
        return await self.cog.controller.validate_interaction(interaction, self.profile.user_id)


class MissionSelect(discord.ui.Select):
    """Mission selection dropdown."""
    
    def __init__(self, missions):
        options = []
        for mission in missions[:25]:  # Max 25 options
            options.append(
                discord.SelectOption(
                    label=mission.name[:100],
                    value=mission.id,
                    description=f"Reward: {mission.base_reward} credits",
                    emoji="🚨"
                )
            )
        
        super().__init__(
            placeholder="Select a mission...",
            options=options,
            custom_id="pc:dispatch:select_mission:"
        )
    
    async def callback(self, interaction: discord.Interaction):
        mission_id = self.values[0]
        mission = self.view.cog.content_loader.missions.get(mission_id)
        
        if not mission:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Mission not found"),
                ephemeral=True
            )
            return
        
        # Show mission details view
        detail_view = MissionDetailView(self.view.cog, self.view.profile, self.view.user, mission)
        embed = await detail_view.build_embed()
        await interaction.response.edit_message(embed=embed, view=detail_view)


class MissionDetailView(BaseView):
    """View showing mission details with dispatch option."""
    
    def __init__(self, cog, profile: PlayerProfile, user: discord.User, mission):
        super().__init__(timeout=300)
        self.cog = cog
        self.profile = profile
        self.user = user
        self.mission = mission
        
        # Check if can dispatch
        can_dispatch, reason = cog.game_engine.can_dispatch_mission(profile, mission)
        
        if can_dispatch:
            self.add_item(DispatchButton(mission))
        else:
            self.add_item(DispatchDisabledButton(reason))
        
        self.add_item(BackToDispatchButton())
    
    async def build_embed(self) -> discord.Embed:
        """Build mission detail embed."""
        balance = await self.cog.game_engine.get_balance(self.user.id)
        display_balance = balance if balance is not None else 0
        
        embed = build_info_embed(
            f"📋 Mission: {self.mission.name}",
            self.mission.description
        )
        
        # Mission details
        success_chance = self.cog.game_engine.calculate_success_chance(self.profile, self.mission)
        reward = self.cog.game_engine.calculate_mission_reward(self.profile, self.mission)
        cost = self.cog.game_engine.calculate_dispatch_cost(self.profile, self.mission)
        
        embed.add_field(
            name="Mission Info",
            value=(
                f"Base Reward: {format_credits(reward)} credits\n"
                f"Fuel Cost: {format_credits(cost)} credits\n"
                f"Success Chance: {success_chance}%\n"
                f"Duration: {self.mission.base_duration} minutes"
            ),
            inline=True
        )
        
        embed.add_field(
            name="Requirements",
            value=self.mission.get_requirements_text(),
            inline=True
        )
        
        # Check if can dispatch
        can_dispatch, reason = self.cog.game_engine.can_dispatch_mission(self.profile, self.mission)
        
        # Check balance
        if balance is None:
            can_dispatch = False
            reason = "Bank unavailable"
        elif balance < cost:
            can_dispatch = False
            reason = f"Insufficient funds (need {format_credits(cost)} credits)"
        elif balance < self.cog.game_engine.MINIMUM_BALANCE:
            can_dispatch = False
            reason = f"Balance below minimum ({format_credits(self.cog.game_engine.MINIMUM_BALANCE)} credits required)"
        
        status_emoji = "✅" if can_dispatch else "❌"
        status_text = "Ready to dispatch" if can_dispatch else reason
        
        embed.add_field(
            name="Status",
            value=f"{status_emoji} {status_text}",
            inline=False
        )
        
        return embed
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Validate interaction."""
        return await self.cog.controller.validate_interaction(interaction, self.profile.user_id)


class DispatchButton(discord.ui.Button):
    """Dispatch mission button."""
    
    def __init__(self, mission):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Dispatch Units",
            custom_id=f"pc:dispatch:execute:{mission.id}",
            emoji="🚨"
        )
        self.mission = mission
    
    async def callback(self, interaction: discord.Interaction):
        # Double-check balance
        balance = await self.view.cog.game_engine.get_balance(interaction.user.id)
        if balance is None:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Failed to check balance"),
                ephemeral=True
            )
            return

        cost = self.view.cog.game_engine.calculate_dispatch_cost(self.view.profile, self.mission)
        
        if balance < cost or balance < self.view.cog.game_engine.MINIMUM_BALANCE:
            await interaction.response.send_message(
                embed=build_error_embed(
                    "Insufficient Funds",
                    f"You need at least {format_credits(max(cost, self.view.cog.game_engine.MINIMUM_BALANCE))} credits"
                ),
                ephemeral=True
            )
            return
        
        # Execute dispatch
        success, amount, message = self.view.cog.game_engine.dispatch_mission(
            self.view.profile,
            self.mission
        )
        
        # Apply bank transaction
        bank_success, new_balance = await self.view.cog.game_engine.apply_bank_transaction(
            interaction.user.id,
            amount,
            f"Mission: {self.mission.name}"
        )
        
        if not bank_success:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Bank transaction failed"),
                ephemeral=True
            )
            return
        
        # Save profile
        await self.view.cog.repository.save_profile(self.view.profile)
        
        # Show result
        if success:
            result_embed = build_success_embed("Mission Successful!", message)
            result_embed.add_field(
                name="Reward",
                value=f"+{format_credits(amount)} credits",
                inline=True
            )
        else:
            result_embed = build_error_embed("Mission Failed", message)
            result_embed.add_field(
                name="Loss",
                value=f"{format_credits(amount)} credits",
                inline=True
            )
        
        result_embed.add_field(
            name="New Balance",
            value=f"{format_credits(new_balance)} credits",
            inline=True
        )
        
        # Return to dispatch view
        from .dispatch import DispatchView
        dispatch_view = DispatchView(self.view.cog, self.view.profile, self.view.user)
        dispatch_embed = await dispatch_view.build_embed()
        
        await interaction.response.edit_message(embed=dispatch_embed, view=dispatch_view)
        await interaction.followup.send(embed=result_embed, ephemeral=True)


class DispatchDisabledButton(discord.ui.Button):
    """Disabled dispatch button."""
    
    def __init__(self, reason: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=f"Cannot Dispatch: {reason[:50]}",
            custom_id="pc:dispatch:disabled:",
            disabled=True
        )


class BackToDispatchButton(discord.ui.Button):
    """Back to dispatch list button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Back",
            custom_id="pc:dispatch:back:",
            emoji="◀️"
        )
    
    async def callback(self, interaction: discord.Interaction):
        from .dispatch import DispatchView
        view = DispatchView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)


class BackButton(discord.ui.Button):
    """Back to dashboard button."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Back to Dashboard",
            custom_id="pc:dispatch:dashboard:",
            emoji="🏠"
        )
    
    async def callback(self, interaction: discord.Interaction):
        from .dashboard import DashboardView
        view = DashboardView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)
