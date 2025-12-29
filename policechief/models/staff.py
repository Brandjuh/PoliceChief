"""
Staff model
Author: BrandjuhNL
"""

from dataclasses import dataclass


@dataclass
class Staff:
    """Represents a staff type that can be hired."""
    
    id: str
    name: str
    description: str
    staff_type: str  # Type identifier for mission requirements
    hire_cost: int
    salary_per_tick: int  # Salary paid per tick
    success_bonus: float  # Multiplier to mission success chance (e.g., 1.1 = +10%)
    cooldown_minutes: int  # How long staff is unavailable after dispatch
    min_station_level: int = 1
    requires_vehicle: bool = True  # Whether this staff type needs a vehicle seat
    equipment_slots: int = 0  # Equipment slots available to this staff type
    
    def get_display_name(self) -> str:
        """Get formatted display name."""
        return f"{self.name} ({self.staff_type})"
