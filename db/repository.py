"""
Repository pattern for data access
Author: BrandjuhNL
"""

import aiosqlite
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

from ..models import PlayerProfile

log = logging.getLogger("red.policechief.repository")


class Repository:
    """Data access layer with concurrency safety."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._locks: Dict[int, asyncio.Lock] = {}  # user_id -> lock
        self._global_lock = asyncio.Lock()
    
    def _get_user_lock(self, user_id: int) -> asyncio.Lock:
        """Get or create a lock for a specific user."""
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]
    
    async def get_profile(self, user_id: int) -> Optional[PlayerProfile]:
        """Get a player profile by user ID."""
        async with self._get_user_lock(user_id):
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT * FROM player_profiles WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row is None:
                        return None
                    return self._row_to_profile(row)
    
    async def create_profile(self, user_id: int) -> PlayerProfile:
        """Create a new player profile."""
        async with self._get_user_lock(user_id):
            profile = PlayerProfile(user_id=user_id)
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO player_profiles (
                        user_id, station_level, station_name, current_district,
                        unlocked_districts, owned_vehicles, staff_roster,
                        owned_upgrades, active_policies, heat_level, reputation,
                        last_tick_ts, automation_enabled
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id, profile.station_level, profile.station_name,
                        profile.current_district,
                        json.dumps(profile.unlocked_districts),
                        json.dumps(profile.owned_vehicles),
                        json.dumps(profile.staff_roster),
                        json.dumps(profile.owned_upgrades),
                        json.dumps(profile.active_policies),
                        profile.heat_level, profile.reputation,
                        None,  # last_tick_ts
                        0  # automation_enabled
                    )
                )
                await db.commit()
            log.info(f"Created new profile for user {user_id}")
            return profile
    
    async def get_or_create_profile(self, user_id: int) -> PlayerProfile:
        """Get existing profile or create new one."""
        profile = await self.get_profile(user_id)
        if profile is None:
            profile = await self.create_profile(user_id)
        return profile
    
    async def save_profile(self, profile: PlayerProfile):
        """Save a player profile."""
        async with self._get_user_lock(profile.user_id):
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    UPDATE player_profiles SET
                        station_level = ?,
                        station_name = ?,
                        current_district = ?,
                        unlocked_districts = ?,
                        owned_vehicles = ?,
                        staff_roster = ?,
                        owned_upgrades = ?,
                        active_policies = ?,
                        heat_level = ?,
                        reputation = ?,
                        last_tick_ts = ?,
                        automation_enabled = ?,
                        dashboard_message_id = ?,
                        dashboard_channel_id = ?,
                        vehicle_cooldowns = ?,
                        staff_cooldowns = ?,
                        total_missions_completed = ?,
                        total_missions_failed = ?,
                        total_income_earned = ?,
                        total_expenses_paid = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (
                        profile.station_level,
                        profile.station_name,
                        profile.current_district,
                        json.dumps(profile.unlocked_districts),
                        json.dumps(profile.owned_vehicles),
                        json.dumps(profile.staff_roster),
                        json.dumps(profile.owned_upgrades),
                        json.dumps(profile.active_policies),
                        profile.heat_level,
                        profile.reputation,
                        profile.last_tick_ts.isoformat() if profile.last_tick_ts else None,
                        1 if profile.automation_enabled else 0,
                        profile.dashboard_message_id,
                        profile.dashboard_channel_id,
                        json.dumps({k: v.isoformat() for k, v in profile.vehicle_cooldowns.items()}),
                        json.dumps({k: v.isoformat() for k, v in profile.staff_cooldowns.items()}),
                        profile.total_missions_completed,
                        profile.total_missions_failed,
                        profile.total_income_earned,
                        profile.total_expenses_paid,
                        profile.user_id
                    )
                )
                await db.commit()
    
    def _row_to_profile(self, row) -> PlayerProfile:
        """Convert database row to PlayerProfile object."""
        # Parse JSON fields
        unlocked_districts = json.loads(row[4]) if row[4] else ["downtown"]
        owned_vehicles = json.loads(row[5]) if row[5] else {}
        staff_roster = json.loads(row[6]) if row[6] else {}
        owned_upgrades = json.loads(row[7]) if row[7] else []
        active_policies = json.loads(row[8]) if row[8] else []
        
        # Parse datetime fields
        last_tick_ts = datetime.fromisoformat(row[11]) if row[11] else None
        
        # Parse cooldown fields
        vehicle_cooldowns = {}
        if row[15]:
            vehicle_cooldowns_data = json.loads(row[15])
            vehicle_cooldowns = {k: datetime.fromisoformat(v) for k, v in vehicle_cooldowns_data.items()}
        
        staff_cooldowns = {}
        if row[16]:
            staff_cooldowns_data = json.loads(row[16])
            staff_cooldowns = {k: datetime.fromisoformat(v) for k, v in staff_cooldowns_data.items()}
        
        return PlayerProfile(
            user_id=row[0],
            station_level=row[1],
            station_name=row[2],
            current_district=row[3],
            unlocked_districts=unlocked_districts,
            owned_vehicles=owned_vehicles,
            staff_roster=staff_roster,
            owned_upgrades=owned_upgrades,
            active_policies=active_policies,
            heat_level=row[9],
            reputation=row[10],
            last_tick_ts=last_tick_ts,
            automation_enabled=bool(row[12]),
            dashboard_message_id=row[13],
            dashboard_channel_id=row[14],
            vehicle_cooldowns=vehicle_cooldowns,
            staff_cooldowns=staff_cooldowns,
            total_missions_completed=row[17],
            total_missions_failed=row[18],
            total_income_earned=row[19],
            total_expenses_paid=row[20]
        )
