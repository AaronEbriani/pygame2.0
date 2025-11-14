from __future__ import annotations

import pygame

from core.dialogue import DialogueSession
from core.settings import (
    DIALOGUE_BG_COLOR,
    DIALOGUE_FONT_NAME,
    DIALOGUE_FONT_SIZE,
    DIALOGUE_PADDING,
    DIALOGUE_TEXT_COLOR,
)


class DialogueBox:
    """Renders dialogue text and choices."""

    def __init__(self) -> None:
        self.font = pygame.font.Font(
            pygame.font.match_font(DIALOGUE_FONT_NAME), DIALOGUE_FONT_SIZE
        )
        self.margin = DIALOGUE_PADDING
        self.speaker_surface: pygame.Surface | None = None

    def draw(self, target: pygame.Surface, session: DialogueSession) -> None:
        width, height = target.get_size()
        box_height = height // 3
        surface_rect = pygame.Rect(
            self.margin,
            height - box_height,
            width - self.margin * 2,
            box_height - self.margin,
        )

        pygame.draw.rect(target, DIALOGUE_BG_COLOR, surface_rect, border_radius=8)
        pygame.draw.rect(target, (80, 80, 80), surface_rect, width=2, border_radius=8)

        text_area = surface_rect.inflate(-self.margin * 2, -self.margin * 2)
        node = session.current_node

        self._render_text(target, node.text, text_area, DIALOGUE_TEXT_COLOR)

        if node.choices:
            self._render_choices(target, node.choices, session.choice_index, text_area)

    def _render_text(self, surface: pygame.Surface, text: str, area: pygame.Rect, color: tuple[int, int, int]) -> None:
        words = text.split(" ")
        lines: list[str] = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            if self.font.size(test_line)[0] <= area.width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        y = area.top
        for line in lines[:4]:
            rendered = self.font.render(line, True, color)
            surface.blit(rendered, (area.left, y))
            y += rendered.get_height() + 4

    def _render_choices(self, surface: pygame.Surface, choices, selected_index: int, area: pygame.Rect) -> None:
        y = area.bottom - (len(choices) * (self.font.get_height() + 6))
        for idx, choice in enumerate(choices):
            prefix = "> " if idx == selected_index else "  "
            color = (255, 255, 0) if idx == selected_index else (180, 180, 180)
            rendered = self.font.render(prefix + choice.text, True, color)
            surface.blit(rendered, (area.left, y))
            y += rendered.get_height() + 6

