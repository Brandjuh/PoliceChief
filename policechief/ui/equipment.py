"""
Equipment management view
Author: BrandjuhNL
"""

import discord

from .base import BaseView
from .helpers import build_info_embed, build_error_embed, build_success_embed, format_credits
from ..models import PlayerProfile


def _format_assignment_lines(profile: PlayerProfile, cog) -> tuple[list[str], list[str]]:
    vehicle_lines: list[str] = []
    staff_lines: list[str] = []

    for vehicle_id, assignments in profile.equipment_assignments.get("vehicles", {}).items():
        vehicle = cog.content_loader.vehicles.get(vehicle_id)
        if not vehicle:
            continue
        usage = profile.get_vehicle_slot_usage(vehicle_id, cog.content_loader.vehicles, cog.content_loader.equipment)
        items = ", ".join(
            f"{cog.content_loader.equipment.get(eq_id).name if cog.content_loader.equipment.get(eq_id) else eq_id} x{qty}"
            for eq_id, qty in assignments.items()
        )
        vehicle_lines.append(
            f"{vehicle.name} ({usage['used']}/{usage['total']} slots): {items}"
        )

    for staff_id, assignments in profile.equipment_assignments.get("staff", {}).items():
        staff = cog.content_loader.staff.get(staff_id)
        if not staff:
            continue
        usage = profile.get_staff_slot_usage(staff_id, cog.content_loader.staff, cog.content_loader.equipment)
        items = ", ".join(
            f"{cog.content_loader.equipment.get(eq_id).name if cog.content_loader.equipment.get(eq_id) else eq_id} x{qty}"
            for eq_id, qty in assignments.items()
        )
        staff_lines.append(
            f"{staff.name} ({usage['used']}/{usage['total']} slots): {items}"
        )

    return vehicle_lines, staff_lines


class EquipmentView(BaseView):
    """Equipment purchasing and assignment view."""

    def __init__(self, cog, profile: PlayerProfile, user: discord.User):
        super().__init__(timeout=300)
        self.cog = cog
        self.profile = profile
        self.user = user

        self.available_equipment = cog.content_loader.get_available_equipment(profile.station_level)

        if self.available_equipment:
            self.add_item(EquipmentPurchaseSelect(self.available_equipment))

        if profile.equipment_inventory:
            sell_select = EquipmentSellSelect(self.cog, self.profile)
            if sell_select.options:
                self.add_item(sell_select)

            vehicle_select = EquipmentEquipVehicleSelect(self.cog, self.profile)
            if vehicle_select.options:
                self.add_item(vehicle_select)

            staff_select = EquipmentEquipStaffSelect(self.cog, self.profile)
            if staff_select.options:
                self.add_item(staff_select)

            unequip_select = EquipmentUnequipSelect(self.cog, self.profile)
            if unequip_select.options:
                self.add_item(unequip_select)

        self.add_item(BackButton())

    async def build_embed(self) -> discord.Embed:
        balance = await self.cog.game_engine.get_balance(self.user.id)
        display_balance = balance if balance is not None else 0

        embed = build_info_embed(
            "🧰 Equipment Management",
            f"Buy, sell, and assign equipment. Balance: {format_credits(display_balance)} credits",
        )

        # Inventory summary
        if self.profile.equipment_inventory:
            inventory_lines = []
            for equipment_id, qty in self.profile.equipment_inventory.items():
                equipment = self.cog.content_loader.equipment.get(equipment_id)
                if not equipment:
                    continue
                free = self.profile.get_unassigned_equipment(equipment_id)
                inventory_lines.append(
                    f"{equipment.name} x{qty} (unassigned: {free})"
                )
            if inventory_lines:
                embed.add_field(
                    name="Stored Equipment",
                    value="\n".join(inventory_lines[:10]),
                    inline=False,
                )
        else:
            embed.add_field(
                name="Stored Equipment",
                value="No equipment owned yet",
                inline=False,
            )

        vehicle_lines, staff_lines = _format_assignment_lines(self.profile, self.cog)
        if vehicle_lines:
            embed.add_field(
                name="Vehicle Loadouts",
                value="\n".join(vehicle_lines[:5]),
                inline=False,
            )
        if staff_lines:
            embed.add_field(
                name="Staff Loadouts",
                value="\n".join(staff_lines[:5]),
                inline=False,
            )

        if not vehicle_lines and not staff_lines:
            embed.add_field(
                name="Assignments",
                value="No equipment assigned. Equip vehicles or staff to speed up missions!",
                inline=False,
            )

        embed.set_footer(text="Purchase equipment or assign it to available slots.")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await self.cog.controller.validate_interaction(interaction, self.profile.user_id)


class EquipmentPurchaseSelect(discord.ui.Select):
    def __init__(self, equipment_list):
        options = []
        for item in equipment_list[:25]:
            options.append(
                discord.SelectOption(
                    label=item.name[:100],
                    value=item.id,
                    description=f"Cost: {item.purchase_cost} credits",
                    emoji="🛒",
                )
            )

        super().__init__(
            placeholder="Select equipment to purchase...",
            options=options,
            custom_id="pc:equipment:purchase:",
        )

    async def callback(self, interaction: discord.Interaction):
        equipment_id = self.values[0]
        equipment = self.view.cog.content_loader.equipment.get(equipment_id)
        if not equipment:
            await interaction.response.send_message(
                embed=build_error_embed("Not Found", "Equipment not found."),
                ephemeral=True,
            )
            return

        balance = await self.view.cog.game_engine.get_balance(interaction.user.id)
        if balance is None:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Failed to check balance."),
                ephemeral=True,
            )
            return

        if balance < equipment.purchase_cost:
            await interaction.response.send_message(
                embed=build_error_embed(
                    "Insufficient Funds",
                    f"You need {format_credits(equipment.purchase_cost)} credits to buy {equipment.name}",
                ),
                ephemeral=True,
            )
            return

        success, new_balance = await self.view.cog.game_engine.apply_bank_transaction(
            interaction.user.id,
            -equipment.purchase_cost,
            f"Purchased equipment: {equipment.name}",
        )

        if not success:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Could not complete purchase."),
                ephemeral=True,
            )
            return

        self.view.profile.add_equipment(equipment_id, 1)
        await self.view.cog.repository.save_profile(self.view.profile)

        new_view = EquipmentView(self.view.cog, self.view.profile, self.view.user)
        new_embed = await new_view.build_embed()
        await interaction.response.edit_message(embed=new_embed, view=new_view)
        new_view.attach_message(interaction.message)

        await interaction.followup.send(
            embed=build_success_embed(
                "Equipment Purchased",
                f"Bought {equipment.name} for {format_credits(equipment.purchase_cost)} credits. New balance: {format_credits(new_balance)}",
            ),
            ephemeral=True,
        )


class EquipmentSellSelect(discord.ui.Select):
    def __init__(self, cog, profile: PlayerProfile):
        self.cog = cog
        options = []
        for equipment_id, qty in profile.equipment_inventory.items():
            free_qty = profile.get_unassigned_equipment(equipment_id)
            equipment = cog.content_loader.equipment.get(equipment_id)
            if not equipment or free_qty <= 0:
                continue
            options.append(
                discord.SelectOption(
                    label=f"Sell {equipment.name}",
                    value=equipment.id,
                    description=f"Unassigned: {free_qty} (value {equipment.sell_value} credits each)",
                    emoji="💸",
                )
            )

        super().__init__(
            placeholder="Sell unassigned equipment...",
            options=options[:25],
            custom_id="pc:equipment:sell:",
        )

    async def callback(self, interaction: discord.Interaction):
        equipment_id = self.values[0]
        equipment = self.cog.content_loader.equipment.get(equipment_id)
        if not equipment:
            await interaction.response.send_message(
                embed=build_error_embed("Not Found", "Equipment no longer exists."),
                ephemeral=True,
            )
            return

        free_qty = self.view.profile.get_unassigned_equipment(equipment_id)
        if free_qty <= 0:
            await interaction.response.send_message(
                embed=build_error_embed("Unavailable", "All copies are currently assigned."),
                ephemeral=True,
            )
            return

        self.view.profile.remove_equipment(equipment_id, 1)
        await self.view.cog.repository.save_profile(self.view.profile)

        success, new_balance = await self.view.cog.game_engine.apply_bank_transaction(
            interaction.user.id,
            equipment.sell_value,
            f"Sold equipment: {equipment.name}",
        )

        if not success:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Could not apply sale."),
                ephemeral=True,
            )
            return

        refreshed = EquipmentView(self.view.cog, self.view.profile, self.view.user)
        embed = await refreshed.build_embed()
        await interaction.response.edit_message(embed=embed, view=refreshed)
        refreshed.attach_message(interaction.message)

        await interaction.followup.send(
            embed=build_success_embed(
                "Equipment Sold",
                f"Sold one {equipment.name} for {format_credits(equipment.sell_value)} credits. New balance: {format_credits(new_balance)}",
            ),
            ephemeral=True,
        )


class EquipmentEquipVehicleSelect(discord.ui.Select):
    def __init__(self, cog, profile: PlayerProfile):
        self.cog = cog
        options = []
        for equipment_id, qty in profile.equipment_inventory.items():
            equipment = cog.content_loader.equipment.get(equipment_id)
            free_qty = profile.get_unassigned_equipment(equipment_id)
            if not equipment or free_qty <= 0:
                continue
            for vehicle_id, vehicle in cog.content_loader.vehicles.items():
                usage = profile.get_vehicle_slot_usage(vehicle_id, cog.content_loader.vehicles, cog.content_loader.equipment)
                available_slots = max(0, usage["total"] - usage["used"])
                if available_slots <= 0 or not equipment.applies_to_vehicle(vehicle.vehicle_type):
                    continue
                options.append(
                    discord.SelectOption(
                        label=f"Equip {equipment.name} -> {vehicle.name}",
                        value=f"{equipment.id}|{vehicle.id}",
                        description=f"Free slots: {available_slots} | Unassigned: {free_qty}",
                        emoji="🚓",
                    )
                )
        super().__init__(
            placeholder="Assign equipment to a vehicle type...",
            options=options[:25],
            custom_id="pc:equipment:equip_vehicle:",
        )

    async def callback(self, interaction: discord.Interaction):
        equipment_id, vehicle_id = self.values[0].split("|")
        equipment = self.cog.content_loader.equipment.get(equipment_id)
        vehicle = self.cog.content_loader.vehicles.get(vehicle_id)
        if not equipment or not vehicle:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Equipment or vehicle not found."),
                ephemeral=True,
            )
            return

        if not equipment.applies_to_vehicle(vehicle.vehicle_type):
            await interaction.response.send_message(
                embed=build_error_embed("Invalid", f"{equipment.name} cannot be used on {vehicle.name}."),
                ephemeral=True,
            )
            return

        success = self.view.profile.assign_equipment_to_vehicle(
            vehicle_id,
            equipment_id,
            1,
            self.cog.content_loader.vehicles,
            self.cog.content_loader.equipment,
        )
        if not success:
            await interaction.response.send_message(
                embed=build_error_embed("Unavailable", "No free slots or items to assign."),
                ephemeral=True,
            )
            return

        await self.cog.repository.save_profile(self.view.profile)
        updated_view = EquipmentView(self.cog, self.view.profile, self.view.user)
        embed = await updated_view.build_embed()
        await interaction.response.edit_message(embed=embed, view=updated_view)
        updated_view.attach_message(interaction.message)

        await interaction.followup.send(
            embed=build_success_embed(
                "Equipment Assigned",
                f"Equipped {equipment.name} to {vehicle.name}.",
            ),
            ephemeral=True,
        )


class EquipmentEquipStaffSelect(discord.ui.Select):
    def __init__(self, cog, profile: PlayerProfile):
        self.cog = cog
        options = []
        for equipment_id, qty in profile.equipment_inventory.items():
            equipment = cog.content_loader.equipment.get(equipment_id)
            free_qty = profile.get_unassigned_equipment(equipment_id)
            if not equipment or free_qty <= 0:
                continue
            for staff_id, staff in cog.content_loader.staff.items():
                usage = profile.get_staff_slot_usage(staff_id, cog.content_loader.staff, cog.content_loader.equipment)
                available_slots = max(0, usage["total"] - usage["used"])
                if available_slots <= 0 or not equipment.applies_to_staff(staff.staff_type):
                    continue
                options.append(
                    discord.SelectOption(
                        label=f"Equip {equipment.name} -> {staff.name}",
                        value=f"{equipment.id}|{staff.id}",
                        description=f"Free slots: {available_slots} | Unassigned: {free_qty}",
                        emoji="👮",
                    )
                )
        super().__init__(
            placeholder="Assign equipment to a staff type...",
            options=options[:25],
            custom_id="pc:equipment:equip_staff:",
        )

    async def callback(self, interaction: discord.Interaction):
        equipment_id, staff_id = self.values[0].split("|")
        equipment = self.cog.content_loader.equipment.get(equipment_id)
        staff = self.cog.content_loader.staff.get(staff_id)
        if not equipment or not staff:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Equipment or staff not found."),
                ephemeral=True,
            )
            return

        if not equipment.applies_to_staff(staff.staff_type):
            await interaction.response.send_message(
                embed=build_error_embed("Invalid", f"{equipment.name} cannot be used by {staff.name}."),
                ephemeral=True,
            )
            return

        success = self.view.profile.assign_equipment_to_staff(
            staff_id,
            equipment_id,
            1,
            self.cog.content_loader.staff,
            self.cog.content_loader.equipment,
        )
        if not success:
            await interaction.response.send_message(
                embed=build_error_embed("Unavailable", "No free slots or items to assign."),
                ephemeral=True,
            )
            return

        await self.cog.repository.save_profile(self.view.profile)
        updated_view = EquipmentView(self.cog, self.view.profile, self.view.user)
        embed = await updated_view.build_embed()
        await interaction.response.edit_message(embed=embed, view=updated_view)
        updated_view.attach_message(interaction.message)

        await interaction.followup.send(
            embed=build_success_embed(
                "Equipment Assigned",
                f"Equipped {equipment.name} to {staff.name}.",
            ),
            ephemeral=True,
        )


class EquipmentUnequipSelect(discord.ui.Select):
    def __init__(self, cog, profile: PlayerProfile):
        self.cog = cog
        options = []
        for vehicle_id, assignments in profile.equipment_assignments.get("vehicles", {}).items():
            vehicle = cog.content_loader.vehicles.get(vehicle_id)
            if not vehicle:
                continue
            for equipment_id, qty in assignments.items():
                equipment = cog.content_loader.equipment.get(equipment_id)
                if not equipment:
                    continue
                options.append(
                    discord.SelectOption(
                        label=f"Remove {equipment.name} from {vehicle.name}",
                        value=f"vehicles|{vehicle_id}|{equipment_id}",
                        description=f"Equipped: {qty}",
                        emoji="↩️",
                    )
                )

        for staff_id, assignments in profile.equipment_assignments.get("staff", {}).items():
            staff = cog.content_loader.staff.get(staff_id)
            if not staff:
                continue
            for equipment_id, qty in assignments.items():
                equipment = cog.content_loader.equipment.get(equipment_id)
                if not equipment:
                    continue
                options.append(
                    discord.SelectOption(
                        label=f"Remove {equipment.name} from {staff.name}",
                        value=f"staff|{staff_id}|{equipment_id}",
                        description=f"Equipped: {qty}",
                        emoji="↩️",
                    )
                )

        super().__init__(
            placeholder="Unequip equipment...",
            options=options[:25],
            custom_id="pc:equipment:unequip:",
        )

    async def callback(self, interaction: discord.Interaction):
        target, target_id, equipment_id = self.values[0].split("|")
        equipment = self.cog.content_loader.equipment.get(equipment_id)
        if not equipment:
            await interaction.response.send_message(
                embed=build_error_embed("Not Found", "Equipment not found."),
                ephemeral=True,
            )
            return

        success = self.view.profile.unassign_equipment(target, target_id, equipment_id, 1)
        if not success:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Nothing to unequip."),
                ephemeral=True,
            )
            return

        await self.cog.repository.save_profile(self.view.profile)
        refreshed = EquipmentView(self.cog, self.view.profile, self.view.user)
        embed = await refreshed.build_embed()
        await interaction.response.edit_message(embed=embed, view=refreshed)
        refreshed.attach_message(interaction.message)

        await interaction.followup.send(
            embed=build_success_embed(
                "Equipment Removed",
                f"Returned {equipment.name} to storage.",
            ),
            ephemeral=True,
        )


class BackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Back to Dashboard",
            custom_id="pc:equipment:back:",
            emoji="🏠",
        )

    async def callback(self, interaction: discord.Interaction):
        from .dashboard import DashboardView

        view = DashboardView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)
        view.attach_message(interaction.message)
