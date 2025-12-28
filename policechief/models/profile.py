"""
Player profile model
Author: BrandjuhNL
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:  # pragma: no cover - only for type hints
    from .vehicle import Vehicle


VEHICLE_CAPACITY_BY_LEVEL = {1: 2}
HOLDING_CELL_CAPACITY_BY_LEVEL = {1: 0}

@dataclass
class PlayerProfile:
    """Represents a player's police station profile."""
    
    user_id: int
    station_level: int = 1
    station_name: str = "Metro Police Department"
    current_district: str = "downtown"
    unlocked_districts: List[str] = field(default_factory=lambda: ["downtown"])
    owned_vehicles: Dict[str, int] = field(default_factory=dict)  # vehicle_id -> quantity
    staff_roster: Dict[str, int] = field(default_factory=dict)  # staff_id -> quantity
    owned_upgrades: List[str] = field(default_factory=list)  # upgrade_ids
    active_policies: List[str] = field(default_factory=list)  # policy_ids
    heat_level: int = 0  # 0-100
    reputation: int = 50  # 0-100
    last_tick_ts: Optional[datetime] = None
    automation_enabled: bool = False
    dashboard_message_id: Optional[int] = None
    dashboard_channel_id: Optional[int] = None
    
    # Cooldowns and downtime tracking
    vehicle_cooldowns: Dict[str, datetime] = field(default_factory=dict)  # vehicle_id -> ready_time
    staff_cooldowns: Dict[str, datetime] = field(default_factory=dict)  # staff_id -> ready_time
    
    # Statistics
    total_missions_completed: int = 0
    total_missions_failed: int = 0
    total_income_earned: int = 0
    total_expenses_paid: int = 0
    
    def has_upgrade(self, upgrade_id: str) -> bool:
        """Check if player owns an upgrade."""
        return upgrade_id in self.owned_upgrades
    
    def has_district(self, district_id: str) -> bool:
        """Check if player has unlocked a district."""
        return district_id in self.unlocked_districts
    
    def get_vehicle_count(self, vehicle_id: str) -> int:
        """Get count of owned vehicles of a type."""
        return self.owned_vehicles.get(vehicle_id, 0)
    
    def get_staff_count(self, staff_id: str) -> int:
        """Get count of staff of a type."""
        return self.staff_roster.get(staff_id, 0)

    @property
    def total_vehicle_count(self) -> int:
        """Total number of vehicles owned across all types."""
        return sum(self.owned_vehicles.values())

    @property
    def total_staff_count(self) -> int:
        """Total number of staff across all roles."""
        return sum(self.staff_roster.values())

    def get_vehicle_capacity_limit(self) -> Optional[int]:
        """Maximum vehicles allowed at the current station level."""
        return VEHICLE_CAPACITY_BY_LEVEL.get(self.station_level)

    def has_vehicle_capacity(self) -> bool:
        """Check if another vehicle can be purchased under the current limit."""
        limit = self.get_vehicle_capacity_limit()
        return limit is None or self.total_vehicle_count < limit

    def get_staff_capacity(self, vehicles: Dict[str, "Vehicle"]) -> int:
        """Calculate total staff that can be seated based on owned vehicles."""
        capacity = 0
        for vehicle_id, quantity in self.owned_vehicles.items():
            vehicle = vehicles.get(vehicle_id)
            if vehicle:
                capacity += vehicle.seating_capacity * quantity
        return capacity

    def get_prisoner_capacity(self, vehicles: Dict[str, "Vehicle"]) -> int:
        """Calculate total prisoner transport capacity based on owned vehicles."""
        capacity = 0
        for vehicle_id, quantity in self.owned_vehicles.items():
            vehicle = vehicles.get(vehicle_id)
            if vehicle:
                capacity += vehicle.prisoner_capacity * quantity
        return capacity

    def get_holding_cell_capacity(self) -> int:
        """Holding cell capacity for the current station level."""
        return HOLDING_CELL_CAPACITY_BY_LEVEL.get(self.station_level, 0)
    
    def add_vehicle(self, vehicle_id: str, quantity: int = 1):
        """Add vehicles to the fleet."""
        current = self.owned_vehicles.get(vehicle_id, 0)
        self.owned_vehicles[vehicle_id] = current + quantity
    
    def add_staff(self, staff_id: str, quantity: int = 1):
        """Add staff to the roster."""
        current = self.staff_roster.get(staff_id, 0)
        self.staff_roster[staff_id] = current + quantity
    
    def is_vehicle_available(self, vehicle_id: str) -> bool:
        """Check if at least one vehicle of this type is available (not on cooldown)."""
        if self.get_vehicle_count(vehicle_id) == 0:
            return False
        cooldown = self.vehicle_cooldowns.get(vehicle_id)
        if cooldown is None:
            return True
        return datetime.utcnow() >= cooldown
    
    def is_staff_available(self, staff_id: str) -> bool:
        """Check if at least one staff member of this type is available."""
        if self.get_staff_count(staff_id) == 0:
            return False
        cooldown = self.staff_cooldowns.get(staff_id)
        if cooldown is None:
            return True
        return datetime.utcnow() >= cooldown
