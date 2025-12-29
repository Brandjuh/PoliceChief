"""
Mission model
Author: BrandjuhNL
"""

from collections import Counter
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Mission:
    """Represents a dispatchable mission/call."""
    
    id: str
    name: str
    description: str
    district: str  # Which district this mission appears in
    required_vehicle_types: List[str]  # Vehicle type IDs required
    required_staff_types: List[str]  # Staff type IDs required
    base_reward: int  # Base credit reward
    base_duration: int  # Base duration in minutes
    base_success_chance: int  # Base success % (0-100)
    fuel_cost: int  # Fuel cost per dispatch
    heat_change: int  # Heat change on completion (can be negative)
    reputation_change_success: int  # Reputation change on success
    reputation_change_failure: int  # Reputation change on failure
    min_station_level: int = 1  # Minimum station level to unlock
    
    def get_display_name(self) -> str:
        """Get formatted display name."""
        return self.name

    def get_requirements_text(self) -> str:
        """Get human-readable requirements."""
        parts = []
        if self.required_vehicle_types:
            vehicle_counts = Counter(self.required_vehicle_types)
            vehicle_text = ", ".join(
                f"{count}x {vehicle_type}" if count > 1 else vehicle_type
                for vehicle_type, count in vehicle_counts.items()
            )
            parts.append(f"Vehicles: {vehicle_text}")
        if self.required_staff_types:
            staff_counts = Counter(self.required_staff_types)
            staff_text = ", ".join(
                f"{count}x {staff_type}" if count > 1 else staff_type
                for staff_type, count in staff_counts.items()
            )
            parts.append(f"Staff: {staff_text}")
        parts.append(f"Min Level: {self.min_station_level}")
        return " | ".join(parts)
