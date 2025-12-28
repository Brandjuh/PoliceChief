"""Shared UI base classes for PoliceChief views."""

import logging
import discord

log = logging.getLogger("red.policechief.ui")


class BaseView(discord.ui.View):
    """Base view that removes components after timing out."""

    def __init__(self, *, timeout: float | None = 300):
        super().__init__(timeout=timeout)

    async def on_timeout(self) -> None:
        """Clear interactive components when the view expires."""
        if not getattr(self, "message", None):
            return

        try:
            await self.message.edit(view=None)
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            log.debug(f"Failed to clear timed out view: {exc}")
