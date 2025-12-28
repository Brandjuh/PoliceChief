"""
Vehicle model
Author: BrandjuhNL
"""

from dataclasses import dataclass


@dataclass
class Vehicle:
    """Represents a vehicle type that can be purchased."""
    
    id: str
    name: str
    description: str
    vehicle_type: str  # Type identifier for mission requirements
    purchase_cost: int
    maintenance_cost: int  # Per tick
    fuel_efficiency: float  # Multiplier for fuel costs (1.0 = normal, 0.8 = 20% less fuel)
    cooldown_minutes: int  # How long vehicle is unavailable after dispatch
    min_station_level: int = 1
    
    def get_display_name(self) -> str:
        """Get formatted display name."""
        return f"{self.name} ({self.vehicle_type})"
