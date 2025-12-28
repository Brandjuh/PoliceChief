"""
District model
Author: BrandjuhNL
"""

from dataclasses import dataclass


@dataclass
class District:
    """Represents an unlockable district/zone."""
    
    id: str
    name: str
    description: str
    unlock_cost: int
    mission_reward_multiplier: float  # Multiplier for mission rewards (e.g., 1.2 = +20%)
    mission_difficulty_modifier: int  # Added to base difficulty (negative = easier)
    min_station_level: int = 1
    
    def get_display_name(self) -> str:
        """Get formatted display name."""
        return self.name
