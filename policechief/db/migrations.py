"""
Database migrations manager
Author: BrandjuhNL
"""

import aiosqlite
import logging
from pathlib import Path

log = logging.getLogger("red.policechief.migrations")


class MigrationManager:
    """Manages database schema migrations."""
    
    CURRENT_VERSION = 1
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
    
    async def initialize(self):
        """Initialize database and run migrations if needed."""
        async with aiosqlite.connect(self.db_path) as db:
            # Create version table if it doesn't exist
            await db.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            
            # Get current version
            async with db.execute("SELECT MAX(version) FROM schema_version") as cursor:
                row = await cursor.fetchone()
                current_version = row[0] if row[0] is not None else 0
            
            # Run migrations
            if current_version < self.CURRENT_VERSION:
                log.info(f"Migrating database from version {current_version} to {self.CURRENT_VERSION}")
                await self._run_migrations(db, current_version)
            else:
                log.info(f"Database schema is up to date (version {current_version})")
    
    async def _run_migrations(self, db: aiosqlite.Connection, from_version: int):
        """Run all migrations from from_version to CURRENT_VERSION."""
        for version in range(from_version + 1, self.CURRENT_VERSION + 1):
            log.info(f"Applying migration to version {version}")
            migration_method = getattr(self, f"_migrate_to_v{version}", None)
            if migration_method:
                await migration_method(db)
                await db.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
                await db.commit()
            else:
                log.warning(f"No migration method found for version {version}")
    
    async def _migrate_to_v1(self, db: aiosqlite.Connection):
        """Initial schema creation."""
        # Player profiles table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS player_profiles (
                user_id INTEGER PRIMARY KEY,
                station_level INTEGER DEFAULT 1,
                station_name TEXT DEFAULT 'Metro Police Department',
                current_district TEXT DEFAULT 'downtown',
                unlocked_districts TEXT,  -- JSON array
                owned_vehicles TEXT,  -- JSON object
                staff_roster TEXT,  -- JSON object
                owned_upgrades TEXT,  -- JSON array
                active_policies TEXT,  -- JSON array
                heat_level INTEGER DEFAULT 0,
                reputation INTEGER DEFAULT 50,
                last_tick_ts TEXT,  -- ISO timestamp
                automation_enabled INTEGER DEFAULT 0,
                dashboard_message_id INTEGER,
                dashboard_channel_id INTEGER,
                vehicle_cooldowns TEXT,  -- JSON object
                staff_cooldowns TEXT,  -- JSON object
                total_missions_completed INTEGER DEFAULT 0,
                total_missions_failed INTEGER DEFAULT 0,
                total_income_earned INTEGER DEFAULT 0,
                total_expenses_paid INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for faster lookups
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_profiles_user_id 
            ON player_profiles(user_id)
        """)
        
        log.info("Created initial database schema (v1)")
