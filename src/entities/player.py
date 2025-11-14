from __future__ import annotations

from pathlib import Path

import pygame


ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
PLAYER_SPRITE_PATH = ASSETS_DIR / "characters" / "dayana.png"


class Player:
    _sheet: pygame.Surface | None = None
    _animations: dict[str, list[pygame.Surface]] | None = None

    FRAME_COLUMNS = 3
    FRAME_ROWS = 4
    WALK_SEQUENCE = [0, 1, 2, 1]
    IDLE_INDEX = 0
    COLLISION_WIDTH = 16
    COLLISION_HEIGHT = 16

    def __init__(self, spawn_position: tuple[int, int]) -> None:
        self.speed = 180
        self.animations = self._load_animations()
        self.facing = "down"
        self.walk_sequence_index = 0
        self.animation_timer = 0.0
        self.animation_speed = 0.12

        starting_sprite = self.animations[self.facing][self.IDLE_INDEX]
        self.rect = pygame.Rect(
            spawn_position[0],
            spawn_position[1],
            self.COLLISION_WIDTH,
            self.COLLISION_HEIGHT,
        )
        self.pos = pygame.Vector2(self.rect.topleft)
        self.sprite_offset = pygame.Vector2(
            (starting_sprite.get_width() - self.COLLISION_WIDTH) / 2,
            starting_sprite.get_height() - self.COLLISION_HEIGHT,
        )

        self.input_vector = pygame.Vector2(0, 0)
        self.direction = pygame.Vector2(0, 0)
        self.sprite = starting_sprite

    def handle_input(self) -> None:
        keys = pygame.key.get_pressed()
        vector = pygame.Vector2(0, 0)

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            vector.x = -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            vector.x = 1

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            vector.y = -1
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            vector.y = 1

        self.input_vector = vector
        if vector.length_squared() > 0:
            self.direction = vector.normalize()
            self._update_facing(vector)
        else:
            self.direction.update(0, 0)

    def update(self, dt: float, colliders: list[pygame.Rect], bounds: pygame.Rect) -> None:
        self.handle_input()

        velocity = self.direction * self.speed * dt
        self._move(velocity.x, 0, colliders)
        self._move(0, velocity.y, colliders)

        self.rect.clamp_ip(bounds)
        self.pos.update(self.rect.topleft)

        moving = self.input_vector.length_squared() > 0
        self._update_animation(dt, moving)

    def _move(self, dx: float, dy: float, colliders: list[pygame.Rect]) -> None:
        if dx == 0 and dy == 0:
            return

        self.pos.x += dx
        self.pos.y += dy
        self.rect.topleft = (round(self.pos.x), round(self.pos.y))

        for collider in colliders:
            if self.rect.colliderect(collider):
                if dx > 0:
                    self.rect.right = collider.left
                if dx < 0:
                    self.rect.left = collider.right
                if dy > 0:
                    self.rect.bottom = collider.top
                if dy < 0:
                    self.rect.top = collider.bottom
                self.pos.update(self.rect.topleft)

    def _update_facing(self, vector: pygame.Vector2) -> None:
        if abs(vector.x) > abs(vector.y):
            self.facing = "right" if vector.x > 0 else "left"
        else:
            self.facing = "down" if vector.y > 0 else "up"

    def _update_animation(self, dt: float, moving: bool) -> None:
        frames = self.animations[self.facing]
        if moving:
            self.animation_timer += dt
            if self.animation_timer >= self.animation_speed:
                self.animation_timer = 0.0
                self.walk_sequence_index = (self.walk_sequence_index + 1) % len(self.WALK_SEQUENCE)
            frame_index = self.WALK_SEQUENCE[self.walk_sequence_index]
        else:
            self.walk_sequence_index = 0
            frame_index = self.IDLE_INDEX
            self.animation_timer = 0.0

        self.sprite = frames[frame_index]
        self.sprite_offset.update(
            (self.sprite.get_width() - self.COLLISION_WIDTH) / 2,
            self.sprite.get_height() - self.COLLISION_HEIGHT,
        )

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        draw_pos = pygame.Vector2(self.rect.topleft) - pygame.Vector2(camera_offset)
        draw_pos -= self.sprite_offset
        surface.blit(self.sprite, (round(draw_pos.x), round(draw_pos.y)))

    @classmethod
    def _load_sheet(cls) -> pygame.Surface:
        if cls._sheet is None:
            if not PLAYER_SPRITE_PATH.exists():
                raise FileNotFoundError(f"Player sprite not found at {PLAYER_SPRITE_PATH}")
            cls._sheet = pygame.image.load(str(PLAYER_SPRITE_PATH)).convert_alpha()
        return cls._sheet

    @classmethod
    def _load_animations(cls) -> dict[str, list[pygame.Surface]]:
        if cls._animations is not None:
            return cls._animations

        sheet = cls._load_sheet()
        frame_width = sheet.get_width() // cls.FRAME_COLUMNS
        frame_height = sheet.get_height() // cls.FRAME_ROWS
        scale = 1

        directions = ["down", "up", "left", "right"]
        animations: dict[str, list[pygame.Surface]] = {}

        for row, direction in enumerate(directions):
            frames: list[pygame.Surface] = []
            for col in range(cls.FRAME_COLUMNS):
                frame_rect = pygame.Rect(col * frame_width, row * frame_height, frame_width, frame_height)
                frame = sheet.subsurface(frame_rect).copy()
                if scale != 1:
                    frame = pygame.transform.scale(frame, (frame_width * scale, frame_height * scale))
                frames.append(frame)
            animations[direction] = frames

        cls._animations = animations
        return cls._animations

