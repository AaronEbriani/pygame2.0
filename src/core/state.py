from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame
    from game.game import Game


class GameState:
    """Base class for a game state."""

    def __init__(self, game: "Game"):
        self.game = game
        self.next_state: str | None = None

    def enter(self, previous_state: str | None = None) -> None:
        """Called when the state is pushed onto the stack."""

    def exit(self) -> None:
        """Called when the state is popped off the stack."""

    def handle_event(self, event: "pygame.event.Event") -> None:
        """Process a pygame event."""

    def update(self, dt: float) -> None:
        """Update state logic."""

    def draw(self, surface: "pygame.Surface") -> None:
        """Render state contents."""

