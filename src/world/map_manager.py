from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pygame

from core.settings import (
    MAP_INTERIOR_HOME,
    MAP_OUTSIDE_FOREST,
    MAP_OUTSIDE_VILLAGE,
    TILE_SIZE,
)
from entities.interactables import DoorInteractable, Interactable, LoreObject, NPC, QuestItem
from world.tmx_loader import (
    extract_rects_from_object_layers,
    extract_rects_from_tile_layers,
    iter_objects_by_layer,
    load_tmx_surface,
)


ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"


@dataclass(slots=True)
class MapDefinition:
    spawn: tuple[int, int]
    interactables: list[Callable[[], Interactable]] = field(default_factory=list)
    colliders: list[pygame.Rect] = field(default_factory=list)
    size: tuple[int, int] | None = None
    color: tuple[int, int, int] | None = None
    tmx_path: Path | None = None
    collision_layers: tuple[str, ...] = ("collision", "collisions")
    interactable_layers: tuple[str, ...] = ()


class GameMap:
    def __init__(self, map_id: str, definition: MapDefinition) -> None:
        self.map_id = map_id
        self.definition = definition
        self.tmx_data = None
        self.colliders: list[pygame.Rect] = []

        if definition.tmx_path is not None:
            surface, tmx_data = load_tmx_surface(definition.tmx_path)
            self.surface = surface
            self.tmx_data = tmx_data
            self._size = surface.get_size()
            if definition.colliders:
                self.colliders.extend(rect.copy() for rect in definition.colliders)

            if definition.collision_layers:
                self.colliders.extend(
                    extract_rects_from_tile_layers(tmx_data, definition.collision_layers)
                )
                self.colliders.extend(
                    extract_rects_from_object_layers(tmx_data, definition.collision_layers)
                )

            if not self.colliders:
                tile_w = tmx_data.tilewidth
                tile_h = tmx_data.tileheight
                width, height = self._size
                self.colliders = [
                    pygame.Rect(0, 0, width, tile_h),  # top boundary
                    pygame.Rect(0, height - tile_h, width, tile_h),  # bottom boundary
                    pygame.Rect(0, 0, tile_w, height),  # left boundary
                    pygame.Rect(width - tile_w, 0, tile_w, height),  # right boundary
                ]
        else:
            if definition.size is None or definition.color is None:
                raise ValueError("Non-TMX maps require size and color.")
            self.surface = pygame.Surface(definition.size)
            self.surface.fill(definition.color)
            self._size = definition.size
            self.colliders = [rect.copy() for rect in definition.colliders]
            self._draw_collision_debug()

        self.interactables = [factory() for factory in definition.interactables]
        if definition.tmx_path is not None:
            tmx_interactables = self._load_tmx_interactables(definition)
            if tmx_interactables:
                if self.interactables:
                    self.interactables.extend(tmx_interactables)
                else:
                    self.interactables = tmx_interactables
        if definition.tmx_path is not None:
            definition.size = self._size

    def _draw_collision_debug(self) -> None:
        for rect in self.colliders:
            pygame.draw.rect(self.surface, (40, 60, 40), rect, 0)

    @property
    def rect(self) -> pygame.Rect:
        width, height = self.surface.get_size()
        return pygame.Rect(0, 0, width, height)

    def _load_tmx_interactables(self, definition: MapDefinition) -> list[Interactable]:
        if self.tmx_data is None or not definition.interactable_layers:
            return []

        interactables: list[Interactable] = []

        def parse_spawn(data: dict) -> tuple[int, int] | None:
            if "target_spawn" in data and isinstance(data["target_spawn"], str):
                bits = [part.strip() for part in data["target_spawn"].split(",")]
                if len(bits) == 2 and all(part.lstrip("-").isdigit() for part in bits):
                    return int(bits[0]), int(bits[1])
            if "spawn_x" in data and "spawn_y" in data:
                try:
                    return int(data["spawn_x"]), int(data["spawn_y"])
                except (TypeError, ValueError):
                    return None
            return None

        for obj in iter_objects_by_layer(self.tmx_data, definition.interactable_layers):
            props = dict(getattr(obj, "properties", {}))
            object_id = str(props.get("id") or obj.name or f"{self.map_id}_obj_{len(interactables)}")
            kind = str(props.get("type") or getattr(obj, "type", "")).lower()
            dialogue_id = props.get("dialogue_id")
            rect = pygame.Rect(
                int(obj.x),
                int(obj.y),
                int(obj.width or TILE_SIZE),
                int(obj.height or TILE_SIZE),
            )

            if kind == "door":
                target_map = props.get("target_map")
                spawn = parse_spawn(props)
                if target_map and spawn:
                    interactables.append(
                        DoorInteractable(object_id, rect, target_map, spawn, props.get("dialogue_id"))
                    )
            elif kind == "npc":
                if dialogue_id:
                    interactables.append(NPC(object_id, rect, dialogue_id))
            elif kind in {"lore", "object"}:
                if dialogue_id:
                    interactables.append(LoreObject(object_id, rect, dialogue_id))
            elif kind in {"quest_item", "questitem"}:
                event_name = props.get("event") or props.get("quest_event")
                if dialogue_id and event_name:
                    interactables.append(QuestItem(object_id, rect, dialogue_id, str(event_name)))

        return interactables


class MapManager:
    def __init__(self) -> None:
        self.maps: dict[str, GameMap] = {}
        self.current_map: GameMap | None = None
        self.pending_spawn: tuple[int, int] | None = None
        self._build_maps()

    def _build_maps(self) -> None:
        for map_id, definition in _create_map_definitions().items():
            self.maps[map_id] = GameMap(map_id, definition)

    def load_map(self, map_id: str, spawn: tuple[int, int] | None = None) -> tuple[int, int]:
        if map_id not in self.maps:
            raise KeyError(f"Map '{map_id}' is not defined.")

        self.current_map = self.maps[map_id]
        return spawn or self.current_map.definition.spawn

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        if not self.current_map:
            return
        map_surface = self.current_map.surface
        surface.blit(map_surface, (-camera_offset.x, -camera_offset.y))

        for interactable in self.current_interactables:
            interactable.draw(surface, camera_offset)

    @property
    def current_interactables(self) -> list[Interactable]:
        return self.current_map.interactables if self.current_map else []

    @property
    def collision_rects(self) -> list[pygame.Rect]:
        return self.current_map.colliders if self.current_map else []

    @property
    def map_rect(self) -> pygame.Rect:
        if not self.current_map:
            return pygame.Rect(0, 0, TILE_SIZE * 10, TILE_SIZE * 10)
        return self.current_map.rect

    def find_interactable(self, object_id: str) -> Interactable | None:
        if not self.current_map:
            return None
        for interactable in self.current_map.interactables:
            if interactable.object_id == object_id:
                return interactable
        return None


def _create_map_definitions() -> dict[str, MapDefinition]:
    def rect(x: int, y: int, w: int, h: int) -> pygame.Rect:
        return pygame.Rect(x, y, w, h)

    def outside_village() -> MapDefinition:
        interactables: list[Callable[[], Interactable]] = [
            lambda: DoorInteractable(
                "home_front_door",
                rect(53 * 16 - 8, 24 * 16 - 16, 32, 48),
                MAP_INTERIOR_HOME,
                (220, 360),
            ),
            lambda: NPC(
                "npc_mia",
                rect(520, 420, TILE_SIZE, TILE_SIZE + 16),
                "mia_intro",
            ),
            lambda: LoreObject(
                "village_sign",
                rect(900, 480, TILE_SIZE, TILE_SIZE),
                "village_sign",
            ),
            lambda: QuestItem(
                "quest_totem_a",
                rect(1100, 300, TILE_SIZE, TILE_SIZE),
                "quest_item_a",
                "quest_item_collected",
            ),
            lambda: QuestItem(
                "quest_totem_b",
                rect(300, 900, TILE_SIZE, TILE_SIZE),
                "quest_item_b",
                "quest_item_collected",
            ),
            lambda: QuestItem(
                "quest_totem_c",
                rect(1250, 900, TILE_SIZE, TILE_SIZE),
                "quest_item_c",
                "quest_item_collected",
            ),
        ]

        return MapDefinition(
            spawn=(960, 640),
            interactables=interactables,
            colliders=[],
            tmx_path=ASSETS_DIR / "maps/outside.tmx",
            interactable_layers=("interactables",),
            collision_layers=("collision",),
        )

    def interior_home() -> MapDefinition:
        width, height = 640, 480
        interactables = [
            lambda: DoorInteractable(
                "home_exit",
                rect(width // 2 - 32, height - 96, 64, 64),
                MAP_OUTSIDE_VILLAGE,
                (760, 620),
            ),
            lambda: LoreObject(
                "bookshelf",
                rect(120, 120, 80, 80),
                "bookshelf",
            ),
        ]

        colliders = [
            rect(0, 0, width, 48),
            rect(0, height - 32, width, 32),
            rect(0, 0, 32, height),
            rect(width - 32, 0, 32, height),
            rect(200, 200, 240, 80),
        ]

        return MapDefinition(
            spawn=(width // 2, height - 120),
            interactables=interactables,
            colliders=colliders,
            size=(width, height),
            color=(190, 170, 140),
        )

    def outside_forest() -> MapDefinition:
        width, height = 1800, 1400
        interactables = [
            lambda: NPC(
                "elder_rhea",
                rect(900, 700, TILE_SIZE, TILE_SIZE + 16),
                "quest_complete",
            ),
            lambda: LoreObject(
                "forest_shrine",
                rect(900, 540, TILE_SIZE * 2, TILE_SIZE),
                "forest_shrine",
            ),
        ]

        colliders = [
            rect(400, 400, 1000, 80),
            rect(400, 400, 80, 600),
            rect(1320, 400, 80, 600),
            rect(400, 920, 1000, 80),
        ]

        return MapDefinition(
            spawn=(width // 2, height - 160),
            interactables=interactables,
            colliders=colliders,
            size=(width, height),
            color=(60, 120, 90),
        )

    return {
        MAP_OUTSIDE_VILLAGE: outside_village(),
        MAP_INTERIOR_HOME: interior_home(),
        MAP_OUTSIDE_FOREST: outside_forest(),
    }

