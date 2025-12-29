"""
Player profile model
Author: BrandjuhNL
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - only for type hints
    from .staff import Staff
    from .vehicle import Vehicle


VEHICLE_CAPACITY_BY_LEVEL = {1: 2}
HOLDING_CELL_CAPACITY_BY_LEVEL = {1: 0}

# Dispatch center configuration
DISPATCH_BASE_TABLES = 1
DISPATCHER_STAFF_ID = "dispatcher"

# Special user ID with full feature access (e.g., automation without upgrade)
SPECIAL_FEATURE_ACCESS_USER_ID = 132620654087241729

@dataclass
class ActiveMission:
    """Represents a mission currently in progress."""

    mission_id: str
    name: str
    ends_at: datetime
    dispatched_at: datetime
    operating_cost: int
    potential_reward: int
    success_chance: int
    heat_change: int
    reputation_success: int
    reputation_failure: int

    def remaining_minutes(self, now: Optional[datetime] = None) -> int:
        """Return remaining minutes until completion (minimum 0)."""
        now = now or datetime.utcnow()
        remaining = self.ends_at - now
        return max(0, int(remaining.total_seconds() // 60))


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
    equipment_inventory: Dict[str, int] = field(default_factory=dict)  # equipment_id -> quantity
    equipment_assignments: Dict[str, Dict[str, Dict[str, int]]] = field(
        default_factory=lambda: {"vehicles": {}, "staff": {}}
    )  # target -> id -> equipment counts
    active_missions: List[ActiveMission] = field(default_factory=list)
    heat_level: int = 0  # 0-100
    reputation: int = 50  # 0-100
    last_tick_ts: Optional[datetime] = None
    automation_enabled: bool = False
    dashboard_message_id: Optional[int] = None
    dashboard_channel_id: Optional[int] = None
    
    # Cooldowns and downtime tracking
    vehicle_cooldowns: Dict[str, List[datetime]] = field(default_factory=dict)  # vehicle_id -> ready_times
    staff_cooldowns: Dict[str, List[datetime]] = field(default_factory=dict)  # staff_id -> ready_times
    
    # Statistics
    total_missions_completed: int = 0
    total_missions_failed: int = 0
    total_income_earned: int = 0
    total_expenses_paid: int = 0

    def has_automation_access(self) -> bool:
        """Check if automation features should be available for the profile."""
        return self.has_upgrade("dispatch_center") or self.user_id == SPECIAL_FEATURE_ACCESS_USER_ID
    
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

    def get_seated_staff_count(self, staff_catalog: Dict[str, "Staff"]) -> int:
        """Total staff that require vehicle seats."""
        seated = 0
        for staff_id, quantity in self.staff_roster.items():
            staff = staff_catalog.get(staff_id)
            if staff is None or staff.requires_vehicle:
                seated += quantity
        return seated

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

    def remove_vehicle(self, vehicle_id: str, quantity: int = 1):
        """Remove vehicles from the fleet, clearing cooldowns when depleted."""
        current = self.owned_vehicles.get(vehicle_id, 0)
        if quantity >= current:
            self.owned_vehicles.pop(vehicle_id, None)
            self.vehicle_cooldowns.pop(vehicle_id, None)
            self._ensure_assignment_buckets()
            self.equipment_assignments.get("vehicles", {}).pop(vehicle_id, None)
        elif current > 0:
            self.owned_vehicles[vehicle_id] = current - quantity

    def add_staff(self, staff_id: str, quantity: int = 1):
        """Add staff to the roster."""
        current = self.staff_roster.get(staff_id, 0)
        self.staff_roster[staff_id] = current + quantity

    def add_equipment(self, equipment_id: str, quantity: int = 1):
        """Add equipment pieces to the shared inventory."""
        current = self.equipment_inventory.get(equipment_id, 0)
        self.equipment_inventory[equipment_id] = current + quantity

    def remove_staff(self, staff_id: str, quantity: int = 1):
        """Remove staff from the roster, clearing cooldowns when depleted."""
        current = self.staff_roster.get(staff_id, 0)
        if quantity >= current:
            self.staff_roster.pop(staff_id, None)
            self.staff_cooldowns.pop(staff_id, None)
            self._ensure_assignment_buckets()
            self.equipment_assignments.get("staff", {}).pop(staff_id, None)
        elif current > 0:
            self.staff_roster[staff_id] = current - quantity

    def remove_equipment(self, equipment_id: str, quantity: int = 1):
        """Remove equipment from inventory without touching assignments."""
        current = self.equipment_inventory.get(equipment_id, 0)
        if quantity >= current:
            self.equipment_inventory.pop(equipment_id, None)
        elif current > 0:
            self.equipment_inventory[equipment_id] = current - quantity
    
    def _prune_cooldowns(self, cooldowns: Dict[str, List[datetime]]):
        """Remove expired cooldown entries from a cooldown mapping."""
        now = datetime.utcnow()
        for key, entries in list(cooldowns.items()):
            cooldowns[key] = [timestamp for timestamp in entries if timestamp > now]
            if not cooldowns[key]:
                cooldowns.pop(key, None)

    def get_available_vehicle_count(self, vehicle_id: str) -> int:
        """Number of ready vehicles of a given type."""
        owned = self.get_vehicle_count(vehicle_id)
        if owned == 0:
            return 0

        self._prune_cooldowns(self.vehicle_cooldowns)
        busy = len(self.vehicle_cooldowns.get(vehicle_id, []))
        return max(0, owned - busy)

    def get_available_staff_count(self, staff_id: str) -> int:
        """Number of ready staff of a given type."""
        owned = self.get_staff_count(staff_id)
        if owned == 0:
            return 0

        self._prune_cooldowns(self.staff_cooldowns)
        busy = len(self.staff_cooldowns.get(staff_id, []))
        return max(0, owned - busy)

    def _ensure_assignment_buckets(self):
        """Make sure the equipment assignment mapping exists."""
        if not self.equipment_assignments:
            self.equipment_assignments = {"vehicles": {}, "staff": {}}
        if "vehicles" not in self.equipment_assignments:
            self.equipment_assignments["vehicles"] = {}
        if "staff" not in self.equipment_assignments:
            self.equipment_assignments["staff"] = {}

    def get_total_assigned_equipment(self, equipment_id: str) -> int:
        """Total number of equipment pieces currently slotted anywhere."""
        self._ensure_assignment_buckets()
        total = 0
        for target_group in self.equipment_assignments.values():
            for equipment_counts in target_group.values():
                total += equipment_counts.get(equipment_id, 0)
        return total

    def get_unassigned_equipment(self, equipment_id: str) -> int:
        """Equipment available in storage that is not slotted."""
        owned = self.equipment_inventory.get(equipment_id, 0)
        return max(0, owned - self.get_total_assigned_equipment(equipment_id))

    def get_equipment_for_vehicle(self, vehicle_id: str) -> Dict[str, int]:
        """Get equipment assigned to a specific vehicle type."""
        self._ensure_assignment_buckets()
        return self.equipment_assignments["vehicles"].get(vehicle_id, {})

    def get_equipment_for_staff(self, staff_id: str) -> Dict[str, int]:
        """Get equipment assigned to a specific staff type."""
        self._ensure_assignment_buckets()
        return self.equipment_assignments["staff"].get(staff_id, {})

    def _get_used_slots(self, assignments: Dict[str, int], equipment_catalog) -> int:
        """Calculate used slot capacity from assigned items."""
        slots = 0
        for equipment_id, quantity in assignments.items():
            equipment = equipment_catalog.get(equipment_id)
            if equipment:
                slots += equipment.slot_size * quantity
        return slots

    def get_vehicle_slot_usage(self, vehicle_id: str, vehicles, equipment_catalog) -> Dict[str, int]:
        """Return used and total slots for a vehicle type."""
        vehicle = vehicles.get(vehicle_id)
        total_slots = vehicle.equipment_slots * self.get_vehicle_count(vehicle_id) if vehicle else 0
        assigned = self.get_equipment_for_vehicle(vehicle_id)
        used_slots = self._get_used_slots(assigned, equipment_catalog)
        return {"used": used_slots, "total": total_slots}

    def get_staff_slot_usage(self, staff_id: str, staff_catalog, equipment_catalog) -> Dict[str, int]:
        """Return used and total slots for a staff type."""
        staff = staff_catalog.get(staff_id)
        total_slots = staff.equipment_slots * self.get_staff_count(staff_id) if staff else 0
        assigned = self.get_equipment_for_staff(staff_id)
        used_slots = self._get_used_slots(assigned, equipment_catalog)
        return {"used": used_slots, "total": total_slots}

    def assign_equipment_to_vehicle(
        self,
        vehicle_id: str,
        equipment_id: str,
        quantity: int,
        vehicles,
        equipment_catalog,
    ) -> bool:
        """Assign equipment to a vehicle type if slots and inventory allow."""
        self._ensure_assignment_buckets()
        vehicle = vehicles.get(vehicle_id)
        equipment = equipment_catalog.get(equipment_id)
        if not vehicle or not equipment:
            return False

        current_assignments = self.get_equipment_for_vehicle(vehicle_id)
        usage = self.get_vehicle_slot_usage(vehicle_id, vehicles, equipment_catalog)
        available_slots = max(0, usage["total"] - usage["used"])
        needed_slots = equipment.slot_size * quantity
        if needed_slots > available_slots:
            return False

        if self.get_unassigned_equipment(equipment_id) < quantity:
            return False

        updated = dict(current_assignments)
        updated[equipment_id] = updated.get(equipment_id, 0) + quantity
        self.equipment_assignments["vehicles"][vehicle_id] = updated
        return True

    def assign_equipment_to_staff(
        self,
        staff_id: str,
        equipment_id: str,
        quantity: int,
        staff_catalog,
        equipment_catalog,
    ) -> bool:
        """Assign equipment to a staff type if slots and inventory allow."""
        self._ensure_assignment_buckets()
        staff = staff_catalog.get(staff_id)
        equipment = equipment_catalog.get(equipment_id)
        if not staff or not equipment:
            return False

        current_assignments = self.get_equipment_for_staff(staff_id)
        usage = self.get_staff_slot_usage(staff_id, staff_catalog, equipment_catalog)
        available_slots = max(0, usage["total"] - usage["used"])
        needed_slots = equipment.slot_size * quantity
        if needed_slots > available_slots:
            return False

        if self.get_unassigned_equipment(equipment_id) < quantity:
            return False

        updated = dict(current_assignments)
        updated[equipment_id] = updated.get(equipment_id, 0) + quantity
        self.equipment_assignments["staff"][staff_id] = updated
        return True

    def unassign_equipment(
        self, target: str, target_id: str, equipment_id: str, quantity: int = 1
    ) -> bool:
        """Remove equipment from a specific target and return it to storage."""
        self._ensure_assignment_buckets()
        if target not in self.equipment_assignments:
            return False

        target_map = self.equipment_assignments[target].get(target_id, {})
        current = target_map.get(equipment_id, 0)
        if current <= 0:
            return False

        if quantity >= current:
            target_map.pop(equipment_id, None)
        else:
            target_map[equipment_id] = current - quantity

        if not target_map:
            self.equipment_assignments[target].pop(target_id, None)
        else:
            self.equipment_assignments[target][target_id] = target_map

        return True

    def is_vehicle_available(self, vehicle_id: str) -> bool:
        """Check if at least one vehicle of this type is available (not on cooldown)."""
        return self.get_available_vehicle_count(vehicle_id) > 0

    def is_staff_available(self, staff_id: str) -> bool:
        """Check if at least one staff member of this type is available."""
        return self.get_available_staff_count(staff_id) > 0

    def allocate_vehicles(self, vehicle_counts: Counter, cooldown_end: datetime):
        """Mark the given vehicles as busy until the provided time."""
        for vehicle_id, quantity in vehicle_counts.items():
            if quantity <= 0:
                continue

            ready_slots = self.get_available_vehicle_count(vehicle_id)
            if quantity > ready_slots:
                quantity = ready_slots

            entries = self.vehicle_cooldowns.setdefault(vehicle_id, [])
            entries.extend([cooldown_end] * quantity)

    def allocate_staff(self, staff_counts: Counter, cooldown_end: datetime):
        """Mark the given staff members as busy until the provided time."""
        for staff_id, quantity in staff_counts.items():
            if quantity <= 0:
                continue

            ready_slots = self.get_available_staff_count(staff_id)
            if quantity > ready_slots:
                quantity = ready_slots

            entries = self.staff_cooldowns.setdefault(staff_id, [])
            entries.extend([cooldown_end] * quantity)

    def add_active_mission(self, mission: ActiveMission):
        """Add a mission to the active missions list without discarding pending entries."""
        self.active_missions.append(mission)

    def prune_expired_missions(self, reference_time: Optional[datetime] = None):
        """Remove missions that have already ended."""
        reference_time = reference_time or datetime.utcnow()
        self.active_missions = [mission for mission in self.active_missions if mission.ends_at > reference_time]
