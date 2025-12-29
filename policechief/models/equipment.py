"""
Equipment model
Author: BrandjuhNL
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Equipment:
    """Represents an equipment item that can be slotted on vehicles or staff."""

    id: str
    name: str
    description: str
    target: str  # vehicle, staff, or any
    purchase_cost: int
    sell_value: int
    effect_type: str  # duration_multiplier, success_bonus
    effect_value: float
    slot_size: int = 1
    min_station_level: int = 1
    allowed_vehicle_types: List[str] = field(default_factory=list)
    allowed_staff_types: List[str] = field(default_factory=list)

    def applies_to_vehicle(self, vehicle_type: str) -> bool:
        """Return True if this equipment can be slotted on the given vehicle type."""
        if self.target not in ("vehicle", "any"):
            return False

        if self.allowed_vehicle_types and vehicle_type not in self.allowed_vehicle_types:
            return False

        return True

    def applies_to_staff(self, staff_type: str) -> bool:
        """Return True if this equipment can be slotted on the given staff type."""
        if self.target not in ("staff", "any"):
            return False

        if self.allowed_staff_types and staff_type not in self.allowed_staff_types:
            return False

        return True

    def is_duration_modifier(self) -> bool:
        """Check if this equipment modifies mission durations."""
        return self.effect_type == "duration_multiplier"

    def is_success_modifier(self) -> bool:
        """Check if this equipment modifies mission success chance."""
        return self.effect_type == "success_bonus"

