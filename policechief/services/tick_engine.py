"""
Tick engine for passive income and automation
Author: BrandjuhNL
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from discord.ext import tasks

from ..models import PlayerProfile

log = logging.getLogger("red.policechief.tick_engine")


class TickEngine:
    """Handles passive income, automation, and recurring costs."""
    
    TICK_INTERVAL_MINUTES = 5
    MAX_CATCHUP_HOURS = 24
    
    def __init__(self, bot, repository, game_engine, content_loader):
        self.bot = bot
        self.repository = repository
        self.game_engine = game_engine
        self.content = content_loader
        self._task = None
    
    def start(self):
        """Start the tick engine."""
        if self._task is None or self._task.done():
            self._task = self.tick_loop.start()
            log.info("Tick engine started")
    
    def stop(self):
        """Stop the tick engine."""
        if self._task and not self._task.done():
            self._task.cancel()
            log.info("Tick engine stopped")
    
    @tasks.loop(minutes=TICK_INTERVAL_MINUTES)
    async def tick_loop(self):
        """Main tick loop - runs every 5 minutes."""
        try:
            log.debug("Running tick engine...")
            # This would ideally get all profiles, but for now we'll rely on
            # catch-up when users interact
            # In production, you'd want to fetch all profiles and process them
        except Exception as e:
            log.error(f"Error in tick loop: {e}", exc_info=True)
    
    async def process_catchup(self, profile: PlayerProfile) -> List[str]:
        """
        Process catch-up ticks for a profile that hasn't been updated.
        Returns list of messages about what happened.
        """
        messages = []
        
        if profile.last_tick_ts is None:
            # First time, initialize
            profile.last_tick_ts = datetime.utcnow()
            await self.repository.save_profile(profile)
            return messages
        
        now = datetime.utcnow()
        time_since_last = now - profile.last_tick_ts
        
        # Calculate how many ticks to catch up (capped at 24 hours)
        max_catchup_time = timedelta(hours=self.MAX_CATCHUP_HOURS)
        if time_since_last > max_catchup_time:
            time_since_last = max_catchup_time
            messages.append(f"⚠️ Catch-up capped at {self.MAX_CATCHUP_HOURS} hours")
        
        ticks_to_process = int(time_since_last.total_seconds() / (self.TICK_INTERVAL_MINUTES * 60))
        
        if ticks_to_process == 0:
            return messages
        
        log.info(f"Processing {ticks_to_process} catch-up ticks for user {profile.user_id}")
        
        # Process each tick
        total_income = 0
        total_expenses = 0
        missions_completed = 0
        missions_failed = 0
        
        for i in range(ticks_to_process):
            # Calculate recurring costs
            costs = self.game_engine.calculate_tick_costs(profile)
            total_expenses += costs["total"]
            
            # If automation is enabled and dispatch center is available (upgrade or special access)
            if profile.automation_enabled and profile.has_automation_access():
                # Auto-dispatch missions based on policies
                auto_results = await self._auto_dispatch_missions(profile)
                total_income += auto_results["income"]
                total_expenses += auto_results["expenses"]
                missions_completed += auto_results["completed"]
                missions_failed += auto_results["failed"]
        
        # Apply bank transactions
        net_change = total_income - total_expenses
        
        if net_change != 0:
            user_obj = self.bot.get_user(profile.user_id)
            if user_obj:
                success, new_balance = await self.game_engine.apply_bank_transaction(
                    profile.user_id,
                    net_change,
                    f"Passive income/costs for {ticks_to_process} ticks"
                )
                
                if success:
                    profile.total_income_earned += max(0, total_income)
                    profile.total_expenses_paid += max(0, total_expenses)
                    
                    if net_change > 0:
                        messages.append(f"💰 Earned {net_change} credits while away!")
                    else:
                        messages.append(f"💸 Paid {abs(net_change)} credits in expenses while away")
                    
                    if missions_completed > 0:
                        messages.append(f"✅ Automation completed {missions_completed} missions")
                    if missions_failed > 0:
                        messages.append(f"❌ Automation failed {missions_failed} missions")
        
        # Update last tick timestamp
        profile.last_tick_ts = now
        await self.repository.save_profile(profile)
        
        return messages
    
    async def _auto_dispatch_missions(self, profile: PlayerProfile) -> dict:
        """
        Automatically dispatch missions based on policies.
        Returns dict with income, expenses, completed, failed counts.
        """
        results = {
            "income": 0,
            "expenses": 0,
            "completed": 0,
            "failed": 0
        }
        
        # Get available missions in current district
        missions = self.content.get_missions_for_district(
            profile.current_district,
            profile.station_level
        )
        
        ready, _, available_slots = self.game_engine.describe_automation_status(profile)
        if not ready:
            return results

        # Respect dispatch table capacity for automation
        if available_slots <= 0:
            return results

        dispatched = 0

        # Try to dispatch missions based on active policies
        for mission in missions:
            if dispatched >= available_slots:
                break

            # Check if we can dispatch
            can_dispatch, _ = self.game_engine.can_dispatch_mission(profile, mission)
            if not can_dispatch:
                continue

            # Check if mission matches any active policy
            if not self._matches_policy(mission, profile.active_policies):
                continue

            # Calculate cost and check balance
            cost = self.game_engine.calculate_dispatch_cost(profile, mission)
            balance = await self.game_engine.get_balance(profile.user_id)
            if balance is None:
                continue

            if balance < max(cost, self.game_engine.MINIMUM_BALANCE):
                continue

            # Dispatch the mission
            success, amount, message = self.game_engine.dispatch_mission(profile, mission)

            if success:
                results["income"] += amount
                results["completed"] += 1
            else:
                results["expenses"] += abs(amount)
                results["failed"] += 1

            dispatched += 1
        
        return results
    
    def _matches_policy(self, mission, active_policies: List[str]) -> bool:
        """Check if a mission matches any active policy."""
        if not active_policies:
            return True
        
        for policy_id in active_policies:
            policy = self.content.policies.get(policy_id)
            if policy and self._mission_matches_filters(mission, policy.mission_filters):
                return True
        
        return False
    
    def _mission_matches_filters(self, mission, filters: dict) -> bool:
        """Check if a mission matches policy filters."""
        # Simple filter matching - can be expanded
        if "min_reward" in filters and mission.base_reward < filters["min_reward"]:
            return False
        if "max_reward" in filters and mission.base_reward > filters["max_reward"]:
            return False
        if "districts" in filters and mission.district not in filters["districts"]:
            return False
        
        return True
