# PoliceChief Installation & Quick Start

## Installation Steps

1. Copy the entire `policechief` directory to your Red bot's `cogs` directory
2. Restart your bot or use `[p]load policechief` to load the cog
3. The cog will automatically initialize the database and load content packs

## Directory Structure

```
policechief/
├── __init__.py              # Cog entry point
├── policechief.py           # Main cog class
├── info.json                # Cog metadata
├── README.md                # Full documentation
├── models/                  # Data models
├── db/                      # Database layer with migrations
├── services/                # Game logic and content loading
├── ui/                      # Discord UI components
├── data/                    # JSON content packs
└── schemas/                 # JSON schemas for validation
```

## First Time Setup

1. **Load the cog:**
   ```
   [p]load policechief
   ```

2. **Ensure Red's bank is configured:**
   ```
   [p]bankset registeramount 1000
   ```
   (This gives new users starting credits)

3. **Start playing:**
   ```
   [p]pc menu
   ```

## Testing the Cog

As a player:
1. Use `[p]pc menu` to open your dashboard
2. Navigate to Fleet and purchase a "Standard Patrol Car" (500 credits)
3. Navigate to Staff and hire a "Patrol Officer" (300 credits)
4. Navigate to Dispatch and run the "Traffic Stop" mission
5. Watch your credits grow!

As an admin:
1. Use `[p]pcadmin reloadpacks` to reload content
2. Use `[p]pcadmin addcredits @user 5000` to give credits
3. Use `[p]pcadmin resetprofile @user` to reset a profile

## Customizing Content

Edit the JSON files in `data/` directory:
- Add new missions to existing files or create `missions_custom.json`
- Add new vehicles to `vehicles_core.json` or create new vehicle packs
- Modify rewards, costs, and difficulty to balance gameplay

After editing, use `[p]pcadmin reloadpacks` to reload without restarting the bot.

## Configuration Options

The cog uses these constants that can be modified in the code:

**game_engine.py:**
- `MINIMUM_BALANCE = 100` - Minimum credits required to dispatch

**tick_engine.py:**
- `TICK_INTERVAL_MINUTES = 5` - How often automation runs
- `MAX_CATCHUP_HOURS = 24` - Maximum catch-up time

## Troubleshooting

**Dashboard not opening?**
- Check bot permissions (needs to send embeds and use buttons)
- Verify Red's bank is set up

**Missions not working?**
- Ensure you have the required vehicles and staff
- Check your balance is above 100 credits
- Verify resources aren't on cooldown

**Automation not working?**
- Purchase the "Dispatch Center" upgrade first
- Enable automation in the Automation menu
- Ensure you have available vehicles and staff

## Support

For issues or questions, check:
1. README.md for full documentation
2. Log files for error messages
3. Content pack JSON files for data issues

Happy managing! 🚔
