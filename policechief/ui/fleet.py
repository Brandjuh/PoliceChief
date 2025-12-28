"""
Fleet view - vehicle management
Author: BrandjuhNL
"""

import discord

from .base import BaseView
from .helpers import build_info_embed, build_error_embed, build_success_embed, format_credits, format_time_remaining
from ..models import PlayerProfile


class FleetView(BaseView):
    """Fleet management view."""
    
    def __init__(self, cog, profile: PlayerProfile, user: discord.User):
        super().__init__(timeout=300)
        self.cog = cog
        self.profile = profile
        self.user = user
        
        # Get available vehicles
        self.available_vehicles = cog.content_loader.get_available_vehicles(profile.station_level)
        
        if self.available_vehicles:
            self.add_item(VehicleSelect(self.available_vehicles))
        
        self.add_item(BackButton())
    
    async def build_embed(self) -> discord.Embed:
        """Build the fleet embed."""
        balance = await self.cog.game_engine.get_balance(self.user.id)
        display_balance = balance if balance is not None else 0
        
        embed = build_info_embed(
            "🚓 Fleet Management",
            f"Manage your vehicle fleet\nBalance: {format_credits(display_balance)} credits"
        )

        capacity_limit = self.profile.get_vehicle_capacity_limit()
        capacity_text = (
            f"{self.profile.total_vehicle_count}/{capacity_limit} vehicles"
            if capacity_limit is not None
            else f"{self.profile.total_vehicle_count} vehicles"
        )

        # Show owned vehicles
        if self.profile.owned_vehicles:
            vehicle_list = []
            for vehicle_id, quantity in self.profile.owned_vehicles.items():
                vehicle = self.cog.content_loader.vehicles.get(vehicle_id)
                if vehicle:
                    status = "🟢" if self.profile.is_vehicle_available(vehicle_id) else "🔴"
                    cooldown_text = ""
                    if vehicle_id in self.profile.vehicle_cooldowns:
                        cooldown_text = f" ({format_time_remaining(self.profile.vehicle_cooldowns[vehicle_id])})"
                    vehicle_list.append(f"{status} {vehicle.name} x{quantity}{cooldown_text}")

            if vehicle_list:
                embed.add_field(
                    name=f"Your Fleet ({capacity_text})",
                    value="\n".join(vehicle_list[:10]),  # Show max 10
                    inline=False
                )
        else:
            embed.add_field(
                name=f"Your Fleet ({capacity_text})",
                value="No vehicles owned yet",
                inline=False
            )
        
        # Show available for purchase
        if self.available_vehicles:
            purchase_list = []
            for vehicle in self.available_vehicles[:5]:
                purchase_list.append(
                    f"**{vehicle.name}** - {format_credits(vehicle.purchase_cost)} credits"
                )
            
            embed.add_field(
                name="Available to Purchase",
                value="\n".join(purchase_list),
                inline=False
            )
        
        embed.set_footer(text="Select a vehicle from the dropdown to purchase")
        
        return embed
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Validate interaction."""
        return await self.cog.controller.validate_interaction(interaction, self.profile.user_id)


class VehicleSelect(discord.ui.Select):
    """Vehicle selection dropdown."""
    
    def __init__(self, vehicles):
        options = []
        for vehicle in vehicles[:25]:  # Max 25 options
            options.append(
                discord.SelectOption(
                    label=vehicle.name[:100],
                    value=vehicle.id,
                    description=f"Cost: {vehicle.purchase_cost} credits",
                    emoji="🚓"
                )
            )
        
        super().__init__(
            placeholder="Select a vehicle to purchase...",
            options=options,
            custom_id="pc:fleet:select_vehicle:"
        )
    
    async def callback(self, interaction: discord.Interaction):
        vehicle_id = self.values[0]
        vehicle = self.view.cog.content_loader.vehicles.get(vehicle_id)

        if not vehicle:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Vehicle not found"),
                ephemeral=True
            )
            return

        if not self.view.profile.has_vehicle_capacity():
            limit = self.view.profile.get_vehicle_capacity_limit()
            limit_text = f"{limit} vehicles" if limit is not None else "current capacity"
            await interaction.response.send_message(
                embed=build_error_embed(
                    "Capacity Reached",
                    f"Your station can only house {limit_text}. Upgrade your station to expand your fleet."
                ),
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

        if balance < vehicle.purchase_cost:
            await interaction.response.send_message(
                embed=build_error_embed(
                    "Insufficient Funds",
                    f"You need {format_credits(vehicle.purchase_cost)} credits to purchase {vehicle.name}"
                ),
                ephemeral=True
            )
            return
        
        # Purchase vehicle
        bank_success, new_balance = await self.view.cog.game_engine.apply_bank_transaction(
            interaction.user.id,
            -vehicle.purchase_cost,
            f"Purchased vehicle: {vehicle.name}"
        )
        
        if not bank_success:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Purchase failed"),
                ephemeral=True
            )
            return
        
        # Add vehicle to profile
        self.view.profile.add_vehicle(vehicle_id, 1)
        await self.view.cog.repository.save_profile(self.view.profile)
        
        # Show success and refresh
        success_embed = build_success_embed(
            "Vehicle Purchased!",
            f"Successfully purchased {vehicle.name} for {format_credits(vehicle.purchase_cost)} credits"
        )
        success_embed.add_field(
            name="New Balance",
            value=f"{format_credits(new_balance)} credits",
            inline=True
        )
        
        # Refresh view
        new_view = FleetView(self.view.cog, self.view.profile, self.view.user)
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
            custom_id="pc:fleet:dashboard:",
            emoji="🏠"
        )
    
    async def callback(self, interaction: discord.Interaction):
        from .dashboard import DashboardView
        view = DashboardView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)
        view.attach_message(interaction.message)
