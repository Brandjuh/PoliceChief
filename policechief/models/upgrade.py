"""
Upgrade model
Author: BrandjuhNL
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Upgrade:
    """Represents a purchasable station upgrade."""
    
    id: str
    name: str
    description: str
    cost: int
    effect_type: str  # Type of effect (automation, cost_reduction, income_boost, etc.)
    effect_value: float  # Value of the effect
    min_station_level: int = 1
    required_upgrade: Optional[str] = None  # ID of upgrade that must be owned first
    
    def get_display_name(self) -> str:
        """Get formatted display name."""
        return self.name
    
    def get_effect_description(self) -> str:
        """Get human-readable effect description."""
        if self.effect_type == "automation":
            return "Unlocks automation features"
        elif self.effect_type == "cost_reduction":
            return f"Reduces costs by {int(self.effect_value * 100)}%"
        elif self.effect_type == "income_boost":
            return f"Increases income by {int(self.effect_value * 100)}%"
        elif self.effect_type == "success_boost":
            return f"Increases mission success by {int(self.effect_value * 100)}%"
        elif self.effect_type == "dispatch_capacity":
            tables = int(self.effect_value)
            table_text = "table" if tables == 1 else "tables"
            return f"Adds {tables} dispatch {table_text}"
        else:
            return "Special effect"
