"""Shared UI base classes for PoliceChief views."""

import logging
import discord

log = logging.getLogger("red.policechief.ui")


class BaseView(discord.ui.View):
    """Base view that removes components after timing out."""

    def __init__(self, *, timeout: float | None = 300):
        super().__init__(timeout=timeout)

        # The message this view is attached to. Used for timeout cleanup.
        self.message: discord.Message | None = None

    def attach_message(self, message: discord.Message) -> "BaseView":
        """Bind the view to a message so we can clean it up on timeout."""
        self.message = message
        return self

    async def on_timeout(self) -> None:
        """Clear interactive components when the view expires."""
        if not getattr(self, "message", None):
            return

        try:
            await self.message.edit(view=None)
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            log.debug(f"Failed to clear timed out view: {exc}")
