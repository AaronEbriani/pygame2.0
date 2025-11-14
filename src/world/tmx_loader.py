from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pygame
from pytmx import TiledObjectGroup, TiledTileLayer
from pytmx.util_pygame import load_pygame


class TMXLoadError(RuntimeError):
    """Raised when a TMX map cannot be loaded or rendered."""


def load_tmx_surface(path: Path) -> tuple[pygame.Surface, "TiledMap"]:
    """Load a TMX map and render all visible tile layers to a surface."""
    if not path.exists():
        raise TMXLoadError(f"TMX file not found: {path}")

    tmx_data = load_pygame(str(path), pixelalpha=True)
    width = tmx_data.width * tmx_data.tilewidth
    height = tmx_data.height * tmx_data.tileheight

    surface = pygame.Surface((width, height), flags=pygame.SRCALPHA)

    for layer in tmx_data.visible_layers:
        if isinstance(layer, TiledTileLayer):
            for x, y, gid in layer:
                tile_image = tmx_data.get_tile_image_by_gid(gid)
                if tile_image:
                    surface.blit(tile_image, (x * tmx_data.tilewidth, y * tmx_data.tileheight))

    return surface, tmx_data


def extract_rects_from_object_layers(
    tmx_data: "TiledMap",
    layer_names: Iterable[str],
) -> list[pygame.Rect]:
    """Return pygame.Rects for any objects found in the named layers."""
    desired = {name.lower() for name in layer_names}
    rects: list[pygame.Rect] = []
    for layer in tmx_data.layers:
        if isinstance(layer, TiledObjectGroup) and layer.name and layer.name.lower() in desired:
            for obj in layer:
                rect = pygame.Rect(int(obj.x), int(obj.y), int(obj.width), int(obj.height))
                rects.append(rect)
    return rects


def extract_rects_from_tile_layers(
    tmx_data: "TiledMap",
    layer_names: Iterable[str],
) -> list[pygame.Rect]:
    """Return rects for any non-empty tiles inside the named tile layers."""
    desired = {name.lower() for name in layer_names}
    rects: list[pygame.Rect] = []
    tile_w = tmx_data.tilewidth
    tile_h = tmx_data.tileheight

    for layer in tmx_data.layers:
        if isinstance(layer, TiledTileLayer) and layer.name and layer.name.lower() in desired:
            for x, y, gid in layer:
                if gid:
                    rects.append(pygame.Rect(x * tile_w, y * tile_h, tile_w, tile_h))
    return rects


def iter_objects_by_layer(
    tmx_data: "TiledMap",
    layer_names: Iterable[str],
):
    """Yield objects contained within the requested object layers."""
    desired = {name.lower() for name in layer_names}
    for layer in tmx_data.layers:
        if isinstance(layer, TiledObjectGroup) and layer.name and layer.name.lower() in desired:
            for obj in layer:
                yield obj

