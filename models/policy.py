"""
Policy model
Author: BrandjuhNL
"""

from dataclasses import dataclass


@dataclass
class Policy:
    """Represents an automation policy for auto-dispatch."""
    
    id: str
    name: str
    description: str
    mission_filters: dict  # Criteria for which missions to auto-dispatch
    priority: int  # Higher priority policies run first
    min_station_level: int = 1
    
    def get_display_name(self) -> str:
        """Get formatted display name."""
        return self.name
