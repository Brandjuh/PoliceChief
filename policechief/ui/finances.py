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

        # Recurring costs per tick
        tick_costs = self.cog.game_engine.calculate_tick_costs(self.profile)
        embed.add_field(
            name="Expenses per 5 minutes",
            value=(
                f"Staff salaries: {format_credits(tick_costs['salaries'])} credits\n"
                f"Vehicle maintenance: {format_credits(tick_costs['maintenance'])} credits\n"
                f"Total burn rate: {format_credits(tick_costs['total'])} credits"
            ),
            inline=False,
        )

        staff_lines = self._build_staff_cost_lines()
        embed.add_field(
            name="Staff costs (per tick)",
            value="\n".join(staff_lines) if staff_lines else "No staff employed",
            inline=False,
        )

        vehicle_lines = self._build_vehicle_cost_lines()
        embed.add_field(
            name="Vehicle costs (per tick)",
            value="\n".join(vehicle_lines) if vehicle_lines else "No vehicles owned",
            inline=False,
        )

        dispatch_multiplier, cost_reduction_lines = self._build_dispatch_cost_details()
        income_boost_lines, has_income_boost = self._build_income_boost_details()

        embed.add_field(
            name="Fuel & dispatch costs",
            value=(
                f"Current fuel multiplier: x{dispatch_multiplier:.2f}\n"
                "Failed missions charge the full dispatch cost.\n"
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

    def _build_staff_cost_lines(self) -> list[str]:
        lines: list[str] = []
        for staff_id, quantity in self.profile.staff_roster.items():
            staff = self.cog.content_loader.staff.get(staff_id)
            if not staff:
                continue
            total_salary = staff.salary_per_tick * quantity
            lines.append(
                f"👮 {staff.name} x{quantity}: {format_credits(total_salary)} (per {staff.salary_per_tick} each)"
            )
        return lines

    def _build_vehicle_cost_lines(self) -> list[str]:
        lines: list[str] = []
        for vehicle_id, quantity in self.profile.owned_vehicles.items():
            vehicle = self.cog.content_loader.vehicles.get(vehicle_id)
            if not vehicle:
                continue
            total_maintenance = vehicle.maintenance_cost * quantity
            lines.append(
                f"🚓 {vehicle.name} x{quantity}: {format_credits(total_maintenance)} (per {vehicle.maintenance_cost} each)"
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
