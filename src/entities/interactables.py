from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pygame


ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
DEFAULT_NPC_SPRITE = ASSETS_DIR / "characters" / "cloaked-figure.png"


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
    _sprite_cache: dict[tuple[Path, int, int], pygame.Surface] = {}

    def __init__(
        self,
        object_id: str,
        rect: pygame.Rect,
        dialogue_id: str,
        sprite_path: Path | None = None,
        *,
        sprite_columns: int = 3,
        sprite_rows: int = 4,
    ) -> None:
        super().__init__(object_id, rect)
        self.dialogue_id = dialogue_id
        self.sprite_path = sprite_path if sprite_path is not None else DEFAULT_NPC_SPRITE
        self.sprite_columns = sprite_columns
        self.sprite_rows = sprite_rows

    def set_dialogue(self, dialogue_id: str) -> None:
        self.dialogue_id = dialogue_id

    def interact(self, play_state: PlayStateLike) -> None:
        play_state.begin_dialogue(self.dialogue_id)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        sprite = self._load_sprite(self.sprite_path, self.sprite_columns, self.sprite_rows)
        world_rect = self.rect.move(-camera_offset.x, -camera_offset.y)
        sprite_rect = sprite.get_rect(midbottom=world_rect.midbottom)
        surface.blit(sprite, sprite_rect)

    @classmethod
    def _load_sprite(cls, path: Path, columns: int, rows: int) -> pygame.Surface:
        cache_key = (path, columns, rows)
        sprite = cls._sprite_cache.get(cache_key)
        if sprite is None:
            if not path.exists():
                raise FileNotFoundError(f"NPC sprite not found at {path}")
            sheet = pygame.image.load(str(path)).convert_alpha()
            frame_width = sheet.get_width() // columns
            frame_height = sheet.get_height() // rows
            sprite = sheet.subsurface(pygame.Rect(0, 0, frame_width, frame_height)).copy()
            cls._sprite_cache[cache_key] = sprite
        return sprite


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
    def __init__(
        self,
        object_id: str,
        rect: pygame.Rect,
        dialogue_id: str,
        quest_event: str,
        *,
        visible: bool = False,
    ) -> None:
        super().__init__(object_id, rect)
        self.dialogue_id = dialogue_id
        self.quest_event = quest_event
        self.visible = visible
        self.color = (220, 180, 80)

    def interact(self, play_state: PlayStateLike) -> None:
        play_state.begin_dialogue(self.dialogue_id)
        play_state.notify_event(self.quest_event, {"object_id": self.object_id})
        self.enabled = False

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        if not self.visible:
            return
        draw_rect = self.rect.move(-camera_offset.x, -camera_offset.y)
        pygame.draw.rect(surface, self.color, draw_rect)
        return


class LoreObject(Interactable):
    def __init__(
        self,
        object_id: str,
        rect: pygame.Rect,
        dialogue_id: str,
        *,
        visible: bool = True,
    ) -> None:
        super().__init__(object_id, rect)
        self.dialogue_id = dialogue_id
        self.visible = visible
        self.color = (180, 180, 220)

    def interact(self, play_state: PlayStateLike) -> None:
        play_state.begin_dialogue(self.dialogue_id)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        if not self.visible:
            return
        draw_rect = self.rect.move(-camera_offset.x, -camera_offset.y)
        pygame.draw.rect(surface, self.color, draw_rect)

