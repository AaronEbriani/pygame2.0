from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from core.settings import FPS, RENDER_SCALE, SCREEN_HEIGHT, SCREEN_WIDTH, VIEW_HEIGHT, VIEW_WIDTH
from states.main_menu import MainMenuState

if TYPE_CHECKING:
    from core.state import GameState


class Game:
    """Root game object coordinating global systems and the state stack."""

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Monsters & Maps - Template")

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.render_scale = RENDER_SCALE
        self.view_size = (VIEW_WIDTH, VIEW_HEIGHT)
        self.render_surface = pygame.Surface(self.view_size).convert_alpha()
        self.clock = pygame.time.Clock()

        self.states: dict[str, type["GameState"]] = {}
        self.state_stack: list["GameState"] = []

        self.running = True

        self._register_default_states()
        self.change_state("main_menu")

    def _register_default_states(self) -> None:
        self.register_state("main_menu", MainMenuState)

    def register_state(self, name: str, state_cls: type["GameState"]) -> None:
        self.states[name] = state_cls

    def change_state(self, name: str) -> None:
        if self.state_stack:
            self.state_stack.pop().exit()

        state_cls = self.states[name]
        state = state_cls(self)
        self.state_stack.append(state)
        state.enter()

    def push_state(self, name: str) -> None:
        state_cls = self.states[name]
        state = state_cls(self)
        self.state_stack.append(state)
        state.enter()

    def pop_state(self) -> None:
        if self.state_stack:
            self.state_stack.pop().exit()

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()

        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if self.state_stack:
                self.state_stack[-1].handle_event(event)

    def _update(self, dt: float) -> None:
        if self.state_stack:
            self.state_stack[-1].update(dt)

    def _draw(self) -> None:
        if self.state_stack:
            self.render_surface.fill((0, 0, 0))
            self.state_stack[-1].draw(self.render_surface)
            scaled = pygame.transform.scale(self.render_surface, self.screen.get_size())
            self.screen.blit(scaled, (0, 0))
            pygame.display.flip()

