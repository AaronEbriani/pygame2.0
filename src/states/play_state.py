from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from core.dialogue import DialogueChoice, DialogueManager, DialogueNode, DialogueSession
from core.quests import QuestManager
from core.settings import MAP_OUTSIDE_FOREST, MAP_OUTSIDE_VILLAGE, QUEST_FIND_ARTIFACTS
from core.state import GameState
from entities.interactables import Interactable, NPC
from entities.player import Player
from ui.dialogue_box import DialogueBox
from world.map_manager import MapManager


class PlayState(GameState):
    def __init__(self, game: "Game"):
        super().__init__(game)
        self.map_manager = MapManager()
        spawn = self.map_manager.load_map(MAP_OUTSIDE_VILLAGE)
        self.player = Player(spawn)
        self.camera = pygame.Vector2()
        self.view_width, self.view_height = self.game.view_size

        self.dialogue_manager = DialogueManager(event_callback=self.notify_event)
        self.dialogue_box = DialogueBox()
        self.active_dialogue: DialogueSession | None = None

        self.font = pygame.font.Font(None, 18)
        self.quest_font = pygame.font.Font(None, 16)

        self.quest_manager = QuestManager()
        self.pending_map_change: tuple[str, tuple[int, int]] | None = None

        self.current_prompt: str | None = None
        self.focus_interactable: Interactable | None = None

        self._register_dialogues()

    def enter(self, previous_state: str | None = None) -> None:
        self._update_camera()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if self.active_dialogue:
                self._handle_dialogue_input(event)
                return

            if event.key == pygame.K_e:
                self._attempt_interaction()

    def _handle_dialogue_input(self, event: pygame.event.Event) -> None:
        if not self.active_dialogue:
            return

        if event.key in (pygame.K_UP, pygame.K_w):
            self.active_dialogue.move_choice(-1)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.active_dialogue.move_choice(1)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
            finished = self.active_dialogue.confirm()
            if finished:
                self.active_dialogue = None
                self.current_prompt = None
        elif event.key in (pygame.K_ESCAPE, pygame.K_q):
            self.active_dialogue.cancel()
            self.active_dialogue = None
            self.current_prompt = None

    def _attempt_interaction(self) -> None:
        if not self.focus_interactable:
            return
        self.focus_interactable.interact(self)

    def update(self, dt: float) -> None:
        if not self.active_dialogue:
            self.player.update(dt, self.map_manager.collision_rects, self.map_manager.map_rect)

        self._update_camera()
        self._update_focus_interactable()

        if self.pending_map_change and not self.active_dialogue:
            map_id, spawn = self.pending_map_change
            spawn_pos = self.map_manager.load_map(map_id, spawn)
            self.player = Player(spawn_pos)
            self.pending_map_change = None
            self._update_camera()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((0, 0, 0))
        self.map_manager.draw(surface, self.camera)
        self.player.draw(surface, self.camera)

        if self.current_prompt and not self.active_dialogue:
            prompt_surface = self.font.render(self.current_prompt, True, (255, 255, 255))
            surface.blit(prompt_surface, (10, 10))

        self._draw_quest_tracker(surface)

        if self.active_dialogue:
            self.dialogue_box.draw(surface, self.active_dialogue)

    def begin_dialogue(self, dialogue_id: str, start_node: str | None = None) -> None:
        self.active_dialogue = self.dialogue_manager.start(dialogue_id, start_node or "root")

    def request_map_change(self, map_id: str, spawn: tuple[int, int]) -> None:
        self.pending_map_change = (map_id, spawn)

    def notify_event(self, event_name: str, payload: dict | None = None) -> None:
        payload = payload or {}

        if event_name == "travel_to_forest":
            self.request_map_change(MAP_OUTSIDE_FOREST, (900, 1100))
            return

        if event_name == "quest_begin":
            self.current_prompt = "Collect the three ancient totems around the village."
            return

        if event_name == "quest_turn_in":
            elder = self._get_interactable("elder_rhea")
            if elder and isinstance(elder, NPC):
                elder.set_dialogue("quest_epilogue")
            return

        triggered = self.quest_manager.handle_event(event_name, payload)
        for action in triggered:
            if action == "quest_completed":
                self._on_quest_completed()

    def _on_quest_completed(self) -> None:
        npc = self._get_interactable("npc_mia")
        if npc and isinstance(npc, NPC):
            npc.set_dialogue("mia_ready")
        self.current_prompt = "Return to Mia to continue your adventure."

    def _get_interactable(self, object_id: str) -> Interactable | None:
        return self.map_manager.find_interactable(object_id)

    def _update_focus_interactable(self) -> None:
        self.focus_interactable = None
        for interactable in self.map_manager.current_interactables:
            if interactable.can_interact(self.player.rect):
                self.focus_interactable = interactable
                break

        self.current_prompt = "Press [E] to Interact" if self.focus_interactable else None

    def _update_camera(self) -> None:
        self.view_width, self.view_height = self.game.view_size
        map_rect = self.map_manager.map_rect

        target_x = self.player.rect.centerx - self.view_width // 2
        target_y = self.player.rect.centery - self.view_height // 2

        max_x = max(0, map_rect.width - self.view_width)
        max_y = max(0, map_rect.height - self.view_height)

        self.camera.x = max(0, min(target_x, max_x))
        self.camera.y = max(0, min(target_y, max_y))

    def _draw_quest_tracker(self, surface: pygame.Surface) -> None:
        state = self.quest_manager.quests[QUEST_FIND_ARTIFACTS]
        quest_status = (
            f"Quest: {state.description} "
            f"({len(state.items_collected)}/{state.items_required})"
        )

        text_surface = self.quest_font.render(quest_status, True, (255, 255, 255))
        surface.blit(text_surface, (20, 20))

    def _register_dialogues(self) -> None:
        dm = self.dialogue_manager

        dm.register(
            "mia_intro",
            [
                DialogueNode(
                    "root",
                    "Hi there! Our village relics went missing. Will you help me find the three totems?",
                    choices=[
                        DialogueChoice("I'll help you.", next_id="accept"),
                        DialogueChoice("Maybe later.", next_id="decline"),
                    ],
                ),
                DialogueNode(
                    "accept",
                    "Thank you! I last saw them near the pond, a tree grove, and the town market.",
                    next_id=None,
                    exit_event="quest_begin",
                ),
                DialogueNode(
                    "decline",
                    "No worries. Come back if you change your mind!",
                    next_id=None,
                ),
            ],
        )

        dm.register(
            "mia_ready",
            [
                DialogueNode(
                    "root",
                    "You found them all! Ready to travel to the forest shrine to deliver them?",
                    choices=[
                        DialogueChoice("Yes, let's go!", next_id="travel", event="travel_to_forest"),
                        DialogueChoice("Give me a moment.", next_id="later"),
                    ],
                ),
                DialogueNode(
                    "travel",
                    "Hold tight! I'll meet you there.",
                    next_id=None,
                ),
                DialogueNode(
                    "later",
                    "Alright, come back when you're prepared.",
                    next_id=None,
                ),
            ],
        )

        dm.register(
            "quest_item_a",
            [
                DialogueNode(
                    "root",
                    "An ancient rune-stone pulsing with faint energy.",
                    next_id=None,
                )
            ],
        )

        dm.register(
            "quest_item_b",
            [
                DialogueNode(
                    "root",
                    "A totem etched with mysterious patterns. You carefully add it to your pack.",
                    next_id=None,
                )
            ],
        )

        dm.register(
            "quest_item_c",
            [
                DialogueNode(
                    "root",
                    "The final totem! It hums softly as you pick it up.",
                    next_id=None,
                )
            ],
        )

        dm.register(
            "village_sign",
            [
                DialogueNode(
                    "root",
                    "Village of Lumeris - A place of harmony between trainers and spirits.",
                    next_id=None,
                )
            ],
        )

        dm.register(
            "bookshelf",
            [
                DialogueNode(
                    "root",
                    "The bookshelf is stuffed with battle tactics manuals and berry recipes.",
                    next_id=None,
                )
            ],
        )

        dm.register(
            "forest_shrine",
            [
                DialogueNode(
                    "root",
                    "The shrine awaits the reunited relics. It glows faintly in your presence.",
                    next_id=None,
                )
            ],
        )

        dm.register(
            "quest_complete",
            [
                DialogueNode(
                    "root",
                    "Welcome to the forest shrine. Your dedication saved our realm.",
                    next_id="continue",
                ),
                DialogueNode(
                    "continue",
                    "I will guard the relics from here. Thank you, brave soul.",
                    next_id=None,
                    exit_event="quest_turn_in",
                ),
            ],
        )

        dm.register(
            "quest_epilogue",
            [
                DialogueNode(
                    "root",
                    "May your journey continue with the blessings of the spirits.",
                    next_id=None,
                )
            ],
        )

