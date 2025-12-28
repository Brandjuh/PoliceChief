"""
UI helper functions
Author: BrandjuhNL
"""

import discord
from datetime import datetime, timedelta
from typing import Optional


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


def format_time_remaining(target_time: datetime) -> str:
    """Format remaining time until target_time."""
    now = datetime.utcnow()
    if now >= target_time:
        return "Ready"
    
    delta = target_time - now
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
