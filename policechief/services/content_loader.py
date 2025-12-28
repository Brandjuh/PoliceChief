"""
Content pack loader with JSON schema validation
Author: BrandjuhNL
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Type

import jsonschema

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
        schema = self._load_schema("mission.schema.json")
        await self._load_pack(
            pattern="missions_*.json",
            schema=schema,
            top_key="missions",
            model_cls=Mission,
            target=self.missions,
        )
    
    async def _load_vehicles(self):
        """Load vehicle packs."""
        self.vehicles = {}
        schema = self._load_schema("vehicle.schema.json")
        await self._load_pack(
            pattern="vehicles_*.json",
            schema=schema,
            top_key="vehicles",
            model_cls=Vehicle,
            target=self.vehicles,
        )
    
    async def _load_districts(self):
        """Load district packs."""
        self.districts = {}
        schema = self._load_schema("district.schema.json")
        await self._load_pack(
            pattern="districts_*.json",
            schema=schema,
            top_key="districts",
            model_cls=District,
            target=self.districts,
        )
    
    async def _load_staff(self):
        """Load staff packs."""
        self.staff = {}
        schema = self._load_schema("staff.schema.json")
        await self._load_pack(
            pattern="staff_*.json",
            schema=schema,
            top_key="staff",
            model_cls=Staff,
            target=self.staff,
        )
    
    async def _load_upgrades(self):
        """Load upgrade packs."""
        self.upgrades = {}
        schema = self._load_schema("upgrade.schema.json")
        await self._load_pack(
            pattern="upgrades_*.json",
            schema=schema,
            top_key="upgrades",
            model_cls=Upgrade,
            target=self.upgrades,
        )
    
    async def _load_policies(self):
        """Load policy packs."""
        self.policies = {}
        schema = self._load_schema("policy.schema.json")
        await self._load_pack(
            pattern="policies_*.json",
            schema=schema,
            top_key="policies",
            model_cls=Policy,
            target=self.policies,
        )

    def _load_schema(self, filename: str) -> dict:
        """Load a JSON schema file."""
        path = self.schema_dir / filename
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as exc:
            log.error(f"Failed to load schema {filename}: {exc}")
            return {}

    async def _load_pack(
        self,
        *,
        pattern: str,
        schema: dict,
        top_key: str,
        model_cls: Type,
        target: Dict[str, object],
    ):
        """
        Shared helper for loading and validating a pack file.

        Args:
            pattern: Glob pattern inside the data directory.
            schema: JSON schema dictionary for validation.
            top_key: Top-level key in the JSON data.
            model_cls: Dataclass to instantiate per entry.
            target: Dictionary to populate with ID -> model instances.
        """
        for pack_file in self.data_dir.glob(pattern):
            try:
                with open(pack_file, "r") as f:
                    data = json.load(f)

                # Validate content pack against schema when available
                if schema:
                    jsonschema.validate(instance=data, schema=schema)

                entries = data.get(top_key, [])
                loaded_count = 0

                for entry in entries:
                    try:
                        obj = model_cls(**entry)
                        target[obj.id] = obj
                        loaded_count += 1
                    except Exception as entry_exc:
                        log.error(
                            f"Failed to load {model_cls.__name__} from {pack_file.name}: {entry_exc}"
                        )

                log.info(f"Loaded {pack_file.name}: {loaded_count} {top_key}")
            except jsonschema.ValidationError as val_err:
                log.error(
                    f"Validation failed for {pack_file.name}: {val_err.message} at {list(val_err.absolute_path)}"
                )
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
