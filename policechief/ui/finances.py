"""Finances view - detailed financial breakdown."""

import discord

from .base import BaseView
from .helpers import build_info_embed, format_credits
from ..models import PlayerProfile


class FinancesView(BaseView):
    """View that surfaces income, expenses, and upgrade effects."""

    def __init__(self, cog, profile: PlayerProfile, user: discord.User):
        super().__init__(timeout=300)
        self.cog = cog
        self.profile = profile
        self.user = user

        self.add_item(BackButton())

    async def build_embed(self) -> discord.Embed:
        """Build a detailed financial overview embed."""
        balance = await self.cog.game_engine.get_balance(self.user.id)
        display_balance = balance if balance is not None else 0

        embed = build_info_embed(
            "💰 Financial Overview",
            (
                f"Balance: {format_credits(display_balance)} credits\n"
                "Breakdown of income, expenses, and upgrade effects"
            ),
        )

        # Lifetime performance
        net_total = self.profile.total_income_earned - self.profile.total_expenses_paid
        avg_income = 0
        if self.profile.total_missions_completed > 0:
            avg_income = int(
                self.profile.total_income_earned / self.profile.total_missions_completed
            )

        embed.add_field(
            name="Income",
            value=(
                f"Mission earnings: {format_credits(self.profile.total_income_earned)}\n"
                f"Average per mission: {format_credits(avg_income)}\n"
                f"Completed missions: {self.profile.total_missions_completed}"
            ),
            inline=False,
        )

        missions = self.cog.content_loader.get_missions_for_district(
            self.profile.current_district, self.profile.station_level
        )
        sample_mission = missions[0] if missions else None

        if sample_mission:
            mission_costs = self.cog.game_engine.calculate_mission_operating_costs(
                self.profile, sample_mission
            )
            embed.add_field(
                name=f"Costs per mission ({sample_mission.base_duration}m)",
                value=(
                    f"Fuel: {format_credits(mission_costs['fuel'])} credits\n"
                    f"Maintenance: {format_credits(mission_costs['maintenance'])} credits\n"
                    f"Salaries: {format_credits(mission_costs['salaries'])} credits\n"
                    f"Total operating cost: {format_credits(mission_costs['total'])} credits"
                ),
                inline=False,
            )

            staff_lines = self._build_staff_cost_lines(sample_mission.base_duration)
            embed.add_field(
                name="Staff costs (per mission)",
                value="\n".join(staff_lines) if staff_lines else "No staff employed",
                inline=False,
            )

            vehicle_lines = self._build_vehicle_cost_lines(sample_mission.base_duration)
            embed.add_field(
                name="Vehicle costs (per mission)",
                value="\n".join(vehicle_lines) if vehicle_lines else "No vehicles owned",
                inline=False,
            )

        dispatch_multiplier, cost_reduction_lines = self._build_dispatch_cost_details()
        income_boost_lines, has_income_boost = self._build_income_boost_details()

        embed.add_field(
            name="Fuel & dispatch costs",
            value=(
                f"Current fuel multiplier: x{dispatch_multiplier:.2f}\n"
                "Operating costs are paid when units are dispatched; failures yield no reward.\n"
                f"Upgrades lowering costs:\n{cost_reduction_lines}"
            ),
            inline=False,
        )

        embed.add_field(
            name="Upgrade effects on income",
            value=income_boost_lines
            if has_income_boost
            else "No income-boosting upgrades",
            inline=False,
        )

        embed.add_field(
            name="Net result",
            value=(
                f"Total expenses: {format_credits(self.profile.total_expenses_paid)}\n"
                f"Net profit/loss: {format_credits(net_total)}"
            ),
            inline=False,
        )

        embed.set_footer(text="All amounts are in credits")
        return embed

    def _build_staff_cost_lines(self, duration_minutes: int) -> list[str]:
        lines: list[str] = []
        duration_factor = duration_minutes / 5
        for staff_id, quantity in self.profile.staff_roster.items():
            staff = self.cog.content_loader.staff.get(staff_id)
            if not staff:
                continue
            total_salary = int(staff.salary_per_tick * duration_factor * quantity)
            lines.append(
                f"👮 {staff.name} x{quantity}: {format_credits(total_salary)} per mission"
            )
        return lines

    def _build_vehicle_cost_lines(self, duration_minutes: int) -> list[str]:
        lines: list[str] = []
        duration_factor = duration_minutes / 5
        for vehicle_id, quantity in self.profile.owned_vehicles.items():
            vehicle = self.cog.content_loader.vehicles.get(vehicle_id)
            if not vehicle:
                continue
            total_maintenance = int(vehicle.maintenance_cost * duration_factor * quantity)
            lines.append(
                f"🚓 {vehicle.name} x{quantity}: {format_credits(total_maintenance)} per mission"
            )
        return lines

    def _build_dispatch_cost_details(self) -> tuple[float, str]:
        """Return dispatch cost multiplier and formatted list of reductions."""
        multiplier = 1.0
        reductions: list[str] = []
        for upgrade_id in self.profile.owned_upgrades:
            upgrade = self.cog.content_loader.upgrades.get(upgrade_id)
            if upgrade and upgrade.effect_type == "cost_reduction":
                multiplier *= 1.0 - upgrade.effect_value
                reductions.append(
                    f"⬇️ {upgrade.name}: -{int(upgrade.effect_value * 100)}% fuel/dispatch"
                )

        if not reductions:
            reductions.append("No cost-reducing upgrades")

        return multiplier, "\n".join(reductions)

    def _build_income_boost_details(self) -> tuple[str, bool]:
        boosts: list[str] = []
        multiplier = 1.0
        for upgrade_id in self.profile.owned_upgrades:
            upgrade = self.cog.content_loader.upgrades.get(upgrade_id)
            if upgrade and upgrade.effect_type == "income_boost":
                multiplier *= 1.0 + upgrade.effect_value
                boosts.append(
                    f"📈 {upgrade.name}: +{int(upgrade.effect_value * 100)}% mission income"
                )

        if not boosts:
            return "", False

        boosts.append(f"Total income multipliers: x{multiplier:.2f}")
        return "\n".join(boosts), True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Validate interaction."""
        return await self.cog.controller.validate_interaction(interaction, self.profile.user_id)


class BackButton(discord.ui.Button):
    """Back to dashboard button."""

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Back",
            custom_id="pc:finances:back:",
            emoji="◀️",
        )

    async def callback(self, interaction: discord.Interaction):
        from .dashboard import DashboardView

        view = DashboardView(self.view.cog, self.view.profile, self.view.user)
        embed = await view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)
        view.attach_message(interaction.message)
