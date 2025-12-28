# PoliceChief

An idle/management game cog for Red-DiscordBot where players build and manage their own police station.

**Author:** BrandjuhNL

## Features

- **Menu-Based UI**: Modern Discord UI with buttons, selects, and modals
- **Core Gameplay Loop**: Dispatch missions, earn credits, purchase vehicles and hire staff
- **Passive Income**: Automated mission dispatching every 5 minutes with catch-up system
- **Data-Driven Content**: Easily add new missions, vehicles, districts, and upgrades via JSON files
- **Full Economy Integration**: Uses Red's bank system with configurable minimum balance
- **Progression System**: Unlock districts, purchase upgrades, and level up your station

## Installation

1. Add the cog to your Red instance
2. Load it with `[p]load policechief`
3. Players can start with `[p]pc menu` or `[p]pc start`

## Player Commands

- `[p]pc menu` - Open your police station dashboard
- `[p]pc start` - Start your police station (alias for menu)

## Admin Commands

- `[p]pcadmin reloadpacks` - Reload all content packs from JSON files
- `[p]pcadmin resetprofile <user>` - Reset a user's profile
- `[p]pcadmin addcredits <user> <amount>` - Add credits to a user's bank account

## Gameplay Guide

### Getting Started

1. Use `[p]pc menu` to open your dashboard
2. Purchase your first vehicle and hire staff using the Fleet and Staff buttons
3. Navigate to Dispatch to select and run missions
4. Earn credits and expand your operation!

### Dashboard Menu

The dashboard provides access to all game features:

- **Status** - View detailed station statistics
- **Dispatch** - Select and execute missions manually
- **Fleet** - Purchase and manage vehicles
- **Staff** - Hire and manage personnel
- **Districts** - Unlock new districts for better rewards
- **Upgrades** - Purchase station upgrades for bonuses
- **Automation** - Enable/disable automatic mission dispatch (requires Dispatch Center upgrade)
- **Help** - In-game help information
- **Refresh** - Reload dashboard and process catch-up ticks

### Core Mechanics

**Missions:**
- Each mission requires specific vehicles and staff
- Success chance varies based on staff quality, upgrades, and reputation
- Successful missions earn credits and reputation
- Failed missions cost fuel and may reduce reputation

**Resources:**
- **Credits**: Currency used for all purchases (from Red's bank)
- **Reputation**: Affects mission success rates (0-100)
- **Heat**: Represents police attention; higher heat means harder missions (0-100)

**Cooldowns:**
- Vehicles and staff go on cooldown after missions
- Cooldown duration depends on the mission and unit type
- Units recover automatically after cooldown expires

**Station Capacity:**
- Level 1 stations can only house 2 vehicles
- Each patrol car seats 2 officers and can transport 1 prisoner
- The starter station has no holding cells, so prisoners must be transferred to a jail facility

**Passive Income (Automation):**
- Purchase the "Dispatch Center" upgrade to unlock automation
- Enable automation in the Automation menu
- Every 5 minutes, available missions are automatically dispatched
- Catch-up system processes up to 24 hours of missed ticks when you return

### Economy

- **Minimum Balance**: Players must maintain at least 100 credits to dispatch missions
- **Negative Balance Allowed**: Players can go into debt
- **Recurring Costs**: Every 5 minutes (tick), salaries and maintenance are paid
- **Bank Integration**: All transactions use Red's bank system

## Content Packs

Content is loaded from JSON files in the `data/` directory:

- `missions_core.json` - Mission definitions
- `vehicles_core.json` - Vehicle types
- `staff_core.json` - Staff types
- `districts_core.json` - District/zone definitions
- `upgrades_core.json` - Station upgrades
- `policies_core.json` - Automation policies

### Adding New Content

1. Create a new JSON file following the naming pattern (e.g., `missions_custom.json`)
2. Follow the schema structure (see `schemas/` directory)
3. Use `[p]pcadmin reloadpacks` to load new content

Example mission:
```json
{
  "id": "my_mission",
  "name": "Custom Mission",
  "description": "A custom mission",
  "district": "downtown",
  "required_vehicle_types": ["patrol"],
  "required_staff_types": ["officer"],
  "base_reward": 200,
  "base_duration": 20,
  "base_success_chance": 75,
  "fuel_cost": 30,
  "heat_change": 2,
  "reputation_change_success": 3,
  "reputation_change_failure": -2,
  "min_station_level": 1
}
```

## Architecture

The cog follows a clean modular architecture:

- **Models** (`models/`) - Data classes for game entities
- **Database** (`db/`) - SQLite persistence with migrations
- **Services** (`services/`) - Game logic, content loading, tick engine
- **UI** (`ui/`) - Discord UI views and interaction handling
- **Data** (`data/`) - JSON content packs
- **Schemas** (`schemas/`) - JSON Schema validation

### Modular Design

Adding new features doesn't require editing core logic:
- New missions/vehicles/districts → Add to JSON files
- New upgrade effects → Extend game engine calculations
- New UI features → Add new View classes

## Technical Details

- **Python**: 3.11+
- **Red-DiscordBot**: 3.5+
- **Database**: SQLite with aiosqlite
- **Concurrency**: Per-user async locks prevent race conditions
- **Tick System**: Background task loop with timestamp-based catch-up (capped at 24 hours)
- **UI**: discord.py Views, Buttons, Selects, and Modals

## Support

For issues, feature requests, or questions, contact the developer or create an issue in the repository.

## License

See Red-DiscordBot's license for usage terms.
