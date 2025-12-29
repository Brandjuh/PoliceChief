"""
Core game engine - handles game logic and calculations
Author: BrandjuhNL
"""

import logging
import random
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from .tick_engine import TickEngine
from redbot.core import bank
from redbot.core.bot import Red
import discord

from ..models import (
    ActiveMission,
    PlayerProfile,
    Mission,
    Vehicle,
    Staff,
    District,
    DISPATCH_BASE_TABLES,
    DISPATCHER_STAFF_ID,
)

log = logging.getLogger("red.policechief.game_engine")


class GameEngine:
    """Core game logic and calculations."""
    
    MINIMUM_BALANCE = 100  # Minimum credits required to dispatch
    FAILURE_PENALTY_MULTIPLIER = 1.0  # Percentage of dispatch cost lost on failure
    PROFIT_MARGIN = 0.1  # Minimum profit margin versus dispatch cost on success
    PROFIT_PER_LEVEL = 0.015  # 1.5% extra reward per station level above 1
    FAILURE_CHANCE_PENALTY = 3  # Flat reduction to final success chance to make failures slightly more likely

    def __init__(self, bot: Red, content_loader):
        self.bot = bot
        self.content = content_loader
    
    def can_dispatch_mission(self, profile: PlayerProfile, mission: Mission) -> Tuple[bool, str]:
        """
        Check if a mission can be dispatched.
        Returns (can_dispatch, reason_if_not)
        """
        # Ensure a dispatcher is available to operate the center
        if not self.has_active_dispatcher(profile):
            return False, "Dispatch Center requires a dispatcher on duty"

        # Check station level
        if profile.station_level < mission.min_station_level:
            return False, f"Requires station level {mission.min_station_level}"
        
        # Check vehicle requirements (respecting quantity needed per type)
        vehicle_requirements = Counter(mission.required_vehicle_types)
        for vehicle_type, quantity_needed in vehicle_requirements.items():
            available_quantity = 0
            for vehicle_id, vehicle in self.content.vehicles.items():
                if vehicle.vehicle_type == vehicle_type:
                    available_quantity += profile.get_available_vehicle_count(vehicle_id)

            if available_quantity < quantity_needed:
                return False, f"Need {quantity_needed} available {vehicle_type} vehicle(s)"

        # Check staff requirements (respecting quantity needed per type)
        staff_requirements = Counter(mission.required_staff_types)
        for staff_type, quantity_needed in staff_requirements.items():
            available_quantity = 0
            for staff_id, staff in self.content.staff.items():
                if staff.staff_type == staff_type:
                    available_quantity += profile.get_available_staff_count(staff_id)

            if available_quantity < quantity_needed:
                return False, f"Need {quantity_needed} available {staff_type} staff"

        return True, ""

    def has_active_dispatcher(self, profile: PlayerProfile) -> bool:
        """Return True if the dispatch center has a dispatcher assigned and available."""
        return self.get_available_dispatcher_count(profile) > 0

    def get_available_dispatcher_count(self, profile: PlayerProfile) -> int:
        """Return the number of dispatchers currently available."""
        return profile.get_available_staff_count(DISPATCHER_STAFF_ID)

    def get_dispatch_table_count(self, profile: PlayerProfile) -> int:
        """Number of dispatch tables available, including expansions."""
        tables = DISPATCH_BASE_TABLES

        # Each dispatcher adds another active table slot
        tables = max(tables, self.get_available_dispatcher_count(profile))

        for upgrade_id in profile.owned_upgrades:
            upgrade = self.content.upgrades.get(upgrade_id)
            if upgrade and upgrade.effect_type == "dispatch_capacity":
                tables += int(upgrade.effect_value)

        return max(1, tables)

    def get_available_dispatch_slots(self, profile: PlayerProfile) -> int:
        """
        Calculate how many dispatch slots are currently free for automation.
        Limited by dispatch tables and active missions already running.
        """
        if not self.has_active_dispatcher(profile):
            return 0

        tables = self.get_dispatch_table_count(profile)
        occupied = len(profile.active_missions)
        return max(0, tables - occupied)

    def describe_automation_status(self, profile: PlayerProfile) -> Tuple[bool, str, int]:
        """Return (ready, message, available_slots) for automation state."""
        if not profile.automation_enabled:
            return False, "Automation is disabled", 0

        if not profile.has_automation_access():
            return False, "Dispatch Center upgrade required", 0

        if not self.has_active_dispatcher(profile):
            return False, "No dispatcher on duty", 0

        slots = self.get_available_dispatch_slots(profile)
        if slots <= 0:
            return False, "All dispatch tables are currently busy", 0

        return True, f"{slots} dispatch slot(s) available", slots
    
    def calculate_mission_operating_costs(self, profile: PlayerProfile, mission: Mission) -> Dict[str, int]:
        """Calculate mission-specific operating costs (fuel, maintenance, salaries)."""
        costs = {
            "fuel": mission.fuel_cost,
            "maintenance": 0,
            "salaries": 0,
            "total": 0,
        }

        # Apply cost reduction upgrades to fuel only
        cost_multiplier = 1.0
        for upgrade_id in profile.owned_upgrades:
            upgrade = self.content.upgrades.get(upgrade_id)
            if upgrade and upgrade.effect_type == "cost_reduction":
                cost_multiplier *= (1.0 - upgrade.effect_value)

        costs["fuel"] = max(1, int(costs["fuel"] * cost_multiplier))

        # Mission duration is used to translate per-tick costs into per-mission costs
        duration_factor = mission.base_duration / TickEngine.TICK_INTERVAL_MINUTES

        # Calculate maintenance based on vehicles actually required
        vehicle_requirements = Counter(mission.required_vehicle_types)
        for vehicle_type, quantity_needed in vehicle_requirements.items():
            for vehicle_id, vehicle in self.content.vehicles.items():
                if vehicle.vehicle_type != vehicle_type:
                    continue
                owned = profile.get_vehicle_count(vehicle_id)
                if owned <= 0:
                    continue
                used = min(quantity_needed, owned)
                costs["maintenance"] += int(vehicle.maintenance_cost * duration_factor * used)
                quantity_needed -= used
                if quantity_needed <= 0:
                    break

        # Calculate salary costs for staff assigned
        staff_requirements = Counter(mission.required_staff_types)
        for staff_type, quantity_needed in staff_requirements.items():
            for staff_id, staff in self.content.staff.items():
                if staff.staff_type != staff_type:
                    continue
                owned = profile.get_staff_count(staff_id)
                if owned <= 0:
                    continue
                used = min(quantity_needed, owned)
                costs["salaries"] += int(staff.salary_per_tick * duration_factor * used)
                quantity_needed -= used
                if quantity_needed <= 0:
                    break

        costs["total"] = max(1, costs["fuel"] + costs["maintenance"] + costs["salaries"])
        return costs

    def calculate_dispatch_cost(self, profile: PlayerProfile, mission: Mission) -> int:
        """Calculate the total cost to dispatch a mission."""
        costs = self.calculate_mission_operating_costs(profile, mission)
        return costs["total"]
    
    def calculate_success_chance(self, profile: PlayerProfile, mission: Mission) -> int:
        """Calculate mission success chance (0-100)."""
        base_chance = mission.base_success_chance
        
        # Apply district modifier
        district = self.content.districts.get(profile.current_district)
        if district:
            base_chance -= district.mission_difficulty_modifier
        
        # Apply staff bonuses
        staff_bonus = 0.0
        for staff_type in mission.required_staff_types:
            for staff_id, staff in self.content.staff.items():
                if staff.staff_type == staff_type and profile.is_staff_available(staff_id):
                    staff_bonus += (staff.success_bonus - 1.0)
                    break
        
        # Apply upgrade bonuses
        upgrade_bonus = 0.0
        for upgrade_id in profile.owned_upgrades:
            upgrade = self.content.upgrades.get(upgrade_id)
            if upgrade and upgrade.effect_type == "success_boost":
                upgrade_bonus += upgrade.effect_value
        
        # Calculate final chance
        final_chance = base_chance * (1.0 + staff_bonus + upgrade_bonus)

        # Apply reputation modifier
        reputation_modifier = (profile.reputation - 50) / 100.0  # -0.5 to +0.5
        final_chance += (reputation_modifier * 10)  # +/- 5% at extremes

        # Make failures slightly more likely overall
        final_chance -= self.FAILURE_CHANCE_PENALTY

        return max(5, min(95, int(final_chance)))  # Clamp between 5-95%
    
    def calculate_mission_reward(self, profile: PlayerProfile, mission: Mission) -> int:
        """Calculate mission reward amount."""
        base_reward = mission.base_reward

        # Scale rewards by station level so higher-level stations earn more
        level_multiplier = 1.0 + max(0, profile.station_level - 1) * self.PROFIT_PER_LEVEL
        base_reward = int(base_reward * level_multiplier)

        # Apply district multiplier
        district = self.content.districts.get(profile.current_district)
        if district:
            base_reward = int(base_reward * district.mission_reward_multiplier)
        
        # Apply income boost upgrades
        income_multiplier = 1.0
        for upgrade_id in profile.owned_upgrades:
            upgrade = self.content.upgrades.get(upgrade_id)
            if upgrade and upgrade.effect_type == "income_boost":
                income_multiplier *= (1.0 + upgrade.effect_value)

        base_reward = int(base_reward * income_multiplier)
        # Ensure successful missions are always profitable relative to dispatch cost
        dispatch_cost = self.calculate_dispatch_cost(profile, mission)
        minimum_profitable_reward = int(dispatch_cost * (1 + self.PROFIT_MARGIN))

        base_reward = max(base_reward, minimum_profitable_reward)
        return max(1, base_reward)
    
    def dispatch_mission(
        self,
        profile: PlayerProfile,
        mission: Mission
    ) -> Tuple[ActiveMission, int, str]:
        """
        Execute a mission dispatch.
        Returns (active_mission, cost_change, message)
        """
        now = datetime.utcnow()

        # Calculate costs and success odds up front
        operating_costs = self.calculate_mission_operating_costs(profile, mission)
        success_chance = self.calculate_success_chance(profile, mission)
        reward = self.calculate_mission_reward(profile, mission)

        # Apply cooldowns to used resources
        vehicle_requirements = Counter(mission.required_vehicle_types)
        for vehicle_type, needed in vehicle_requirements.items():
            for vehicle_id, vehicle in self.content.vehicles.items():
                if vehicle.vehicle_type != vehicle_type:
                    continue

                if needed <= 0:
                    break

                available = profile.get_available_vehicle_count(vehicle_id)
                if available <= 0:
                    continue

                assign = min(needed, available)
                cooldown_end = now + timedelta(minutes=vehicle.cooldown_minutes)
                profile.allocate_vehicles(Counter({vehicle_id: assign}), cooldown_end)
                needed -= assign

        staff_requirements = Counter(mission.required_staff_types)
        for staff_type, needed in staff_requirements.items():
            for staff_id, staff in self.content.staff.items():
                if staff.staff_type != staff_type:
                    continue

                if needed <= 0:
                    break

                available = profile.get_available_staff_count(staff_id)
                if available <= 0:
                    continue

                assign = min(needed, available)
                cooldown_end = now + timedelta(minutes=staff.cooldown_minutes)
                profile.allocate_staff(Counter({staff_id: assign}), cooldown_end)
                needed -= assign

        mission_end_time = now + timedelta(minutes=mission.base_duration)
        active_mission = ActiveMission(
            mission_id=mission.id,
            name=mission.name,
            ends_at=mission_end_time,
            dispatched_at=now,
            operating_cost=operating_costs["total"],
            potential_reward=reward,
            success_chance=success_chance,
            heat_change=mission.heat_change,
            reputation_success=mission.reputation_change_success,
            reputation_failure=mission.reputation_change_failure,
        )
        profile.add_active_mission(active_mission)
        profile.total_expenses_paid += operating_costs["total"]

        message = (
            f"🚨 Units dispatched for {mission.name}. "
            f"Estimated completion in {mission.base_duration} minutes."
        )

        return active_mission, -operating_costs["total"], message

    def resolve_completed_missions(self, profile: PlayerProfile) -> Dict[str, int | list]:
        """Resolve missions that have reached their end time."""
        now = datetime.utcnow()
        completed_messages: list[str] = []
        income = 0
        expenses = 0
        completed = 0
        failed = 0

        remaining_missions = []
        for mission_state in profile.active_missions:
            if mission_state.ends_at > now:
                remaining_missions.append(mission_state)
                continue

            roll = random.randint(1, 100)
            success = roll <= mission_state.success_chance

            if success:
                reward = mission_state.potential_reward
                income += reward
                profile.total_missions_completed += 1
                profile.total_income_earned += reward
                profile.reputation = min(100, profile.reputation + mission_state.reputation_success)
                profile.heat_level = max(0, min(100, profile.heat_level + mission_state.heat_change))
                completed += 1
                completed_messages.append(
                    f"✅ {mission_state.name} completed (+{reward} credits)"
                )
            else:
                # Costs were already paid upfront; failure just wastes the effort
                profile.total_missions_failed += 1
                profile.reputation = max(0, profile.reputation + mission_state.reputation_failure)
                profile.heat_level = max(0, min(100, profile.heat_level + abs(mission_state.heat_change)))
                failed += 1
                completed_messages.append(
                    f"❌ {mission_state.name} failed (no reward)"
                )

        profile.active_missions = remaining_missions

        return {
            "income": income,
            "expenses": expenses,
            "completed": completed,
            "failed": failed,
            "messages": completed_messages,
        }
    
    async def _resolve_bank_user(self, user_id: int) -> Optional[discord.abc.User]:
        """Return a Discord user object for bank operations."""
        user = self.bot.get_user(user_id)
        if user:
            return user

        try:
            return await self.bot.fetch_user(user_id)
        except Exception as e:
            log.error(f"Failed to resolve user {user_id} for bank operations: {e}")
            return None

    async def check_sufficient_balance(self, user_id: int, amount: int) -> Tuple[bool, int]:
        """
        Check if user has sufficient balance for a transaction.
        Returns (has_sufficient, current_balance)
        """
        user = await self._resolve_bank_user(user_id)
        if not user:
            return False, 0

        try:
            balance = await bank.get_balance(user)
            # Allow going into debt, but check minimum for dispatch
            return balance >= amount, balance
        except Exception as e:
            log.error(f"Error fetching balance for user {user_id}: {e}")
            return None
    
    async def apply_bank_transaction(
        self,
        user_id: int,
        amount: int,
        reason: str
    ) -> Tuple[bool, Optional[int]]:
        """
        Apply a bank transaction (positive = deposit, negative = withdraw).
        Returns (success, new_balance)
        """
        user = await self._resolve_bank_user(user_id)
        if not user:
            return False, None

        try:
            if amount > 0:
                # Deposit
                await bank.deposit_credits(user, amount)
                new_balance = await bank.get_balance(user)
                log.info(f"Deposited {amount} credits to user {user_id} - {reason}")
                return True, new_balance
            elif amount < 0:
                # Withdraw
                await bank.withdraw_credits(user, abs(amount))
                new_balance = await bank.get_balance(user)
                log.info(f"Withdrew {abs(amount)} credits from user {user_id} - {reason}")
                return True, new_balance
            else:
                # No transaction
                balance = await bank.get_balance(user)
                return True, balance
        except Exception as e:
            log.error(f"Bank transaction failed for user {user_id} ({reason}): {e}")
            return False, None

    async def get_balance(self, user_id: int) -> Optional[int]:
        """Return the user's current bank balance."""
        user = await self._resolve_bank_user(user_id)
        if not user:
            return None

        try:
            return await bank.get_balance(user)
        except Exception as e:
            log.error(f"Error fetching balance for user {user_id}: {e}")
            return None
