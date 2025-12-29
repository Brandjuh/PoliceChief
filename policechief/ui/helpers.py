"""
UI helper functions
Author: BrandjuhNL
"""

import discord
from datetime import datetime, timedelta
from typing import Iterable, Optional, Union


def build_error_embed(title: str, description: str) -> discord.Embed:
    """Build a standard error embed."""
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=discord.Color.red()
    )
    return embed


def build_success_embed(title: str, description: str) -> discord.Embed:
    """Build a standard success embed."""
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=discord.Color.green()
    )
    return embed


def build_info_embed(title: str, description: str) -> discord.Embed:
    """Build a standard info embed."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()
    )
    return embed


def _next_timestamp(targets: Iterable[datetime]) -> Optional[datetime]:
    """Return the soonest timestamp in the iterable that is still in the future."""
    now = datetime.utcnow()
    upcoming = [ts for ts in targets if ts and ts > now]
    if not upcoming:
        return None
    return min(upcoming)


def format_time_remaining(target_time: Union[datetime, Iterable[datetime]]) -> str:
    """Format remaining time until target_time.

    Supports a single datetime or an iterable of datetimes (e.g., multiple cooldowns).
    """
    now = datetime.utcnow()

    if isinstance(target_time, datetime):
        target = target_time
    else:
        target = _next_timestamp(target_time)
        if target is None:
            return "Ready"

    if now >= target:
        return "Ready"

    delta = target - now
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def format_credits(amount: int) -> str:
    """Format credits amount with commas."""
    return f"{amount:,}"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
