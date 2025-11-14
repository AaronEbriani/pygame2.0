from __future__ import annotations

import pygame

from core.settings import MENU_FONT_SIZE, MENU_SELECTED_COLOR, MENU_UNSELECTED_COLOR
from core.state import GameState
from states.play_state import PlayState


class MainMenuState(GameState):
    def __init__(self, game: "Game"):
        super().__init__(game)
        self.options = ["Play Game", "Quit Game"]
        self.selected_index = 0
        self.font = pygame.font.Font(None, MENU_FONT_SIZE)

        # Ensure play state is registered exactly once
        if "play" not in self.game.states:
            self.game.register_state("play", PlayState)

    def enter(self, previous_state: str | None = None) -> None:
        self.selected_index = 0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_index = (self.selected_index + 1) % len(self.options)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selected_index = (self.selected_index - 1) % len(self.options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_selected_option()

    def _activate_selected_option(self) -> None:
        option = self.options[self.selected_index]
        if option == "Play Game":
            self.game.change_state("play")
        elif option == "Quit Game":
            self.game.running = False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((0, 0, 0))

        width, height = surface.get_size()
        title_font = pygame.font.Font(None, MENU_FONT_SIZE + 12)
        title_surface = title_font.render("Monsters & Maps", True, (255, 255, 255))
        title_rect = title_surface.get_rect(center=(width // 2, height // 4))
        surface.blit(title_surface, title_rect)

        for idx, option in enumerate(self.options):
            color = MENU_SELECTED_COLOR if idx == self.selected_index else MENU_UNSELECTED_COLOR
            text_surface = self.font.render(option, True, color)
            text_rect = text_surface.get_rect(center=(width // 2, height // 2 + idx * 40))
            surface.blit(text_surface, text_rect)

