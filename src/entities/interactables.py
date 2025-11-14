from __future__ import annotations

from typing import Protocol

import pygame


class PlayStateLike(Protocol):
    def begin_dialogue(self, dialogue_id: str, start_node: str | None = None) -> None: ...

    def request_map_change(self, map_id: str, spawn: tuple[int, int]) -> None: ...

    def notify_event(self, event_name: str, payload: dict | None = None) -> None: ...


class Interactable:
    def __init__(self, object_id: str, rect: pygame.Rect) -> None:
        self.object_id = object_id
        self.rect = rect
        self.enabled = True

    def can_interact(self, player_rect: pygame.Rect) -> bool:
        return self.enabled and self.rect.inflate(12, 12).colliderect(player_rect)

    def interact(self, play_state: PlayStateLike) -> None:
        raise NotImplementedError

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        # Placeholder visual representation
        draw_rect = self.rect.move(-camera_offset.x, -camera_offset.y)
        pygame.draw.rect(surface, (180, 180, 180), draw_rect, width=1)


class NPC(Interactable):
    def __init__(self, object_id: str, rect: pygame.Rect, dialogue_id: str) -> None:
        super().__init__(object_id, rect)
        self.dialogue_id = dialogue_id
        self.color = (255, 200, 120)

    def set_dialogue(self, dialogue_id: str) -> None:
        self.dialogue_id = dialogue_id

    def interact(self, play_state: PlayStateLike) -> None:
        play_state.begin_dialogue(self.dialogue_id)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        draw_rect = self.rect.move(-camera_offset.x, -camera_offset.y)
        pygame.draw.rect(surface, self.color, draw_rect)


class DoorInteractable(Interactable):
    def __init__(
        self,
        object_id: str,
        rect: pygame.Rect,
        target_map: str,
        target_spawn: tuple[int, int],
        dialogue_id: str | None = None,
    ) -> None:
        super().__init__(object_id, rect)
        self.target_map = target_map
        self.target_spawn = target_spawn
        self.dialogue_id = dialogue_id

    def interact(self, play_state: PlayStateLike) -> None:
        if self.dialogue_id:
            play_state.begin_dialogue(self.dialogue_id)
        play_state.request_map_change(self.target_map, self.target_spawn)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        # Doors are represented by map artwork; no additional overlay needed.
        return


class QuestItem(Interactable):
    def __init__(self, object_id: str, rect: pygame.Rect, dialogue_id: str, quest_event: str) -> None:
        super().__init__(object_id, rect)
        self.dialogue_id = dialogue_id
        self.quest_event = quest_event
        self.color = (120, 200, 255)

    def interact(self, play_state: PlayStateLike) -> None:
        play_state.begin_dialogue(self.dialogue_id)
        play_state.notify_event(self.quest_event, {"object_id": self.object_id})
        self.enabled = False

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        draw_rect = self.rect.move(-camera_offset.x, -camera_offset.y)
        pygame.draw.rect(surface, self.color, draw_rect)


class LoreObject(Interactable):
    def __init__(self, object_id: str, rect: pygame.Rect, dialogue_id: str) -> None:
        super().__init__(object_id, rect)
        self.dialogue_id = dialogue_id
        self.color = (180, 180, 220)

    def interact(self, play_state: PlayStateLike) -> None:
        play_state.begin_dialogue(self.dialogue_id)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        draw_rect = self.rect.move(-camera_offset.x, -camera_offset.y)
        pygame.draw.rect(surface, self.color, draw_rect)

