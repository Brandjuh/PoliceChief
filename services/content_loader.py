"""
Content pack loader with JSON schema validation
Author: BrandjuhNL
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

from ..models import Mission, Vehicle, District, Staff, Upgrade, Policy

log = logging.getLogger("red.policechief.content_loader")


class ContentLoader:
    """Loads and validates content packs from JSON files."""
    
    def __init__(self, data_dir: Path, schema_dir: Path):
        self.data_dir = data_dir
        self.schema_dir = schema_dir
        
        self.missions: Dict[str, Mission] = {}
        self.vehicles: Dict[str, Vehicle] = {}
        self.districts: Dict[str, District] = {}
        self.staff: Dict[str, Staff] = {}
        self.upgrades: Dict[str, Upgrade] = {}
        self.policies: Dict[str, Policy] = {}
    
    async def load_all(self):
        """Load all content packs."""
        log.info("Loading content packs...")
        
        await self._load_missions()
        await self._load_vehicles()
        await self._load_districts()
        await self._load_staff()
        await self._load_upgrades()
        await self._load_policies()
        
        log.info(
            f"Loaded content: {len(self.missions)} missions, "
            f"{len(self.vehicles)} vehicles, {len(self.districts)} districts, "
            f"{len(self.staff)} staff types, {len(self.upgrades)} upgrades, "
            f"{len(self.policies)} policies"
        )
    
    async def _load_missions(self):
        """Load mission packs."""
        self.missions = {}
        for pack_file in self.data_dir.glob("missions_*.json"):
            try:
                with open(pack_file, 'r') as f:
                    data = json.load(f)
                
                for mission_data in data.get("missions", []):
                    mission = Mission(**mission_data)
                    self.missions[mission.id] = mission
                
                log.info(f"Loaded {pack_file.name}: {len(data.get('missions', []))} missions")
            except Exception as e:
                log.error(f"Error loading {pack_file.name}: {e}")
    
    async def _load_vehicles(self):
        """Load vehicle packs."""
        self.vehicles = {}
        for pack_file in self.data_dir.glob("vehicles_*.json"):
            try:
                with open(pack_file, 'r') as f:
                    data = json.load(f)
                
                for vehicle_data in data.get("vehicles", []):
                    vehicle = Vehicle(**vehicle_data)
                    self.vehicles[vehicle.id] = vehicle
                
                log.info(f"Loaded {pack_file.name}: {len(data.get('vehicles', []))} vehicles")
            except Exception as e:
                log.error(f"Error loading {pack_file.name}: {e}")
    
    async def _load_districts(self):
        """Load district packs."""
        self.districts = {}
        for pack_file in self.data_dir.glob("districts_*.json"):
            try:
                with open(pack_file, 'r') as f:
                    data = json.load(f)
                
                for district_data in data.get("districts", []):
                    district = District(**district_data)
                    self.districts[district.id] = district
                
                log.info(f"Loaded {pack_file.name}: {len(data.get('districts', []))} districts")
            except Exception as e:
                log.error(f"Error loading {pack_file.name}: {e}")
    
    async def _load_staff(self):
        """Load staff packs."""
        self.staff = {}
        for pack_file in self.data_dir.glob("staff_*.json"):
            try:
                with open(pack_file, 'r') as f:
                    data = json.load(f)
                
                for staff_data in data.get("staff", []):
                    staff_obj = Staff(**staff_data)
                    self.staff[staff_obj.id] = staff_obj
                
                log.info(f"Loaded {pack_file.name}: {len(data.get('staff', []))} staff types")
            except Exception as e:
                log.error(f"Error loading {pack_file.name}: {e}")
    
    async def _load_upgrades(self):
        """Load upgrade packs."""
        self.upgrades = {}
        for pack_file in self.data_dir.glob("upgrades_*.json"):
            try:
                with open(pack_file, 'r') as f:
                    data = json.load(f)
                
                for upgrade_data in data.get("upgrades", []):
                    upgrade = Upgrade(**upgrade_data)
                    self.upgrades[upgrade.id] = upgrade
                
                log.info(f"Loaded {pack_file.name}: {len(data.get('upgrades', []))} upgrades")
            except Exception as e:
                log.error(f"Error loading {pack_file.name}: {e}")
    
    async def _load_policies(self):
        """Load policy packs."""
        self.policies = {}
        for pack_file in self.data_dir.glob("policies_*.json"):
            try:
                with open(pack_file, 'r') as f:
                    data = json.load(f)
                
                for policy_data in data.get("policies", []):
                    policy = Policy(**policy_data)
                    self.policies[policy.id] = policy
                
                log.info(f"Loaded {pack_file.name}: {len(data.get('policies', []))} policies")
            except Exception as e:
                log.error(f"Error loading {pack_file.name}: {e}")
    
    def get_missions_for_district(self, district_id: str, min_level: int) -> List[Mission]:
        """Get all missions available in a district for a given station level."""
        return [
            m for m in self.missions.values()
            if m.district == district_id and m.min_station_level <= min_level
        ]
    
    def get_available_vehicles(self, min_level: int) -> List[Vehicle]:
        """Get all vehicles available for purchase at given station level."""
        return [
            v for v in self.vehicles.values()
            if v.min_station_level <= min_level
        ]
    
    def get_available_staff(self, min_level: int) -> List[Staff]:
        """Get all staff types available for hire at given station level."""
        return [
            s for s in self.staff.values()
            if s.min_station_level <= min_level
        ]
    
    def get_available_districts(self, min_level: int) -> List[District]:
        """Get all districts available to unlock at given station level."""
        return [
            d for d in self.districts.values()
            if d.min_station_level <= min_level
        ]
    
    def get_available_upgrades(self, min_level: int, owned_upgrades: List[str]) -> List[Upgrade]:
        """Get all upgrades available for purchase."""
        available = []
        for upgrade in self.upgrades.values():
            if upgrade.min_station_level > min_level:
                continue
            if upgrade.id in owned_upgrades:
                continue
            if upgrade.required_upgrade and upgrade.required_upgrade not in owned_upgrades:
                continue
            available.append(upgrade)
        return available
