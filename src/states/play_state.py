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

if TYPE_CHECKING:
    from game.game import Game


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
        self.end_title_font = pygame.font.Font(None, 32)
        self.end_message_font = pygame.font.Font(None, 20)

        self.quest_manager = QuestManager()
        self.pending_map_change: tuple[str, tuple[int, int]] | None = None

        self.current_prompt: str | None = None
        self.focus_interactable: Interactable | None = None
        self.end_screen_active = False

        self._register_dialogues()

    def enter(self, previous_state: str | None = None) -> None:
        self._update_camera()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.end_screen_active:
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE,
                pygame.K_RETURN,
                pygame.K_SPACE,
            ):
                self.game.change_state("main_menu")
            return

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
        if self.end_screen_active:
            return

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

        if self.active_dialogue:
            self.dialogue_box.draw(surface, self.active_dialogue)
        elif not self.end_screen_active:
            self._draw_prompt(surface)
        self._draw_quest_tracker(surface)
        if self.end_screen_active:
            self._draw_end_screen(surface)

    def _draw_prompt(self, surface: pygame.Surface) -> None:
        if self.end_screen_active or not self.current_prompt:
            return
        prompt_surface = self.font.render(self.current_prompt, True, (255, 255, 255))
        prompt_rect = prompt_surface.get_rect()
        surface.blit(
            prompt_surface,
            (self.view_width - prompt_rect.width - 10, self.view_height - prompt_rect.height - 10),
        )

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
            self.current_prompt = "Collect the three Heart Shards the cloaked figure described."
            return

        if event_name == "quest_turn_in":
            elder = self._get_interactable("elder_rhea")
            if elder and isinstance(elder, NPC):
                elder.set_dialogue("quest_epilogue")
            self.current_prompt = "Return to the cloaked figure when you are ready."
            return

        if event_name == "flower_found":
            sally = self._get_interactable("npc_sally")
            if sally and isinstance(sally, NPC):
                sally.set_dialogue("sally_thanks")
            self.current_prompt = None
            return

        if event_name == "sally_complete":
            sally = self._get_interactable("npc_sally")
            if sally and isinstance(sally, NPC):
                sally.set_dialogue("sally_repeat")
            self.current_prompt = "You obtained a Heart Shard!"
            return

        if event_name == "show_ending":
            npc = self._get_interactable("npc_mia")
            if npc and isinstance(npc, NPC):
                npc.set_dialogue("mia_epilogue")
            self.end_screen_active = True
            self.active_dialogue = None
            self.current_prompt = None
            self.focus_interactable = None
            return

        triggered = self.quest_manager.handle_event(event_name, payload)
        for action in triggered:
            if action == "quest_completed":
                self._on_quest_completed()

    def _on_quest_completed(self) -> None:
        npc = self._get_interactable("npc_mia")
        if npc and isinstance(npc, NPC):
            npc.set_dialogue("mia_confession")
        self.current_prompt = "Return to the cloaked figure when you feel ready."

    def _get_interactable(self, object_id: str) -> Interactable | None:
        return self.map_manager.find_interactable(object_id)

    def _update_focus_interactable(self) -> None:
        if self.end_screen_active:
            self.focus_interactable = None
            self.current_prompt = None
            return

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
        surface.blit(text_surface, (10, 10))

    def _draw_end_screen(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))

        message_lines = [
            "The Heart Gem shines brightest",
            "when it's shared.",
        ]
        title_y = surface.get_height() // 2 - 40
        for idx, line in enumerate(message_lines):
            rendered = self.end_title_font.render(line, True, (255, 255, 255))
            rect = rendered.get_rect(center=(surface.get_width() // 2, title_y + idx * 40))
            surface.blit(rendered, rect)

        prompt = self.end_message_font.render(
            "Press Enter to return to the main menu.", True, (220, 220, 220)
        )
        prompt_rect = prompt.get_rect(center=(surface.get_width() // 2, title_y + 110))
        surface.blit(prompt, prompt_rect)

    def _register_dialogues(self) -> None:
        dm = self.dialogue_manager

        dm.register(
            "mia_intro",
            [
                DialogueNode(
                    "root",
                    "Ah, good morning, fair maiden! Have you heard of the Heart Gem?",
                    next_id="line2",
                ),
                DialogueNode(
                    "line2",
                    "They say it only appears for someone whose heart beats true.",
                    next_id="line3",
                ),
                DialogueNode(
                    "line3",
                    "If you find its three shards, the full gem -- and your destiny -- will reveal itself.",
                    next_id="line4",
                ),
                DialogueNode(
                    "line4",
                    "Start by looking in the caves behind your house.",
                    next_id="line5",
                ),
                DialogueNode(
                    "line5",
                    "Second, give a helping hand to someone in need. Check the Fortified Forest in the east.",
                    next_id="line6",
                ),
                DialogueNode(
                    "line6",
                    "Lastly, talk to the Old Fisher by the beach.",
                    next_id=None,
                    exit_event="quest_begin",
                ),
            ],
        )

        dm.register(
            "mia_confession",
            [
                DialogueNode(
                    "root",
                    "You found them all. The Heart Gem waits.",
                    next_id="confession_2",
                ),
                DialogueNode(
                    "confession_2",
                    "But... there's one last thing it needs.",
                    next_id="confession_3",
                ),
                DialogueNode(
                    "confession_3",
                    "It must know who your heart truly beats for.",
                    next_id="confession_4",
                ),
                DialogueNode(
                    "confession_4",
                    "(Soft music begins to play...)",
                    next_id="confession_5",
                ),
                DialogueNode(
                    "confession_5",
                    "You've gathered every shard...",
                    next_id="confession_6",
                ),
                DialogueNode(
                    "confession_6",
                    "You've proven your heart's warmth, your courage, your care...",
                    next_id="confession_7",
                ),
                DialogueNode(
                    "confession_7",
                    "So now there's only one question left.",
                    next_id="confession_8",
                ),
                DialogueNode(
                    "confession_8",
                    "Dayana...",
                    next_id="proposal",
                ),
                DialogueNode(
                    "proposal",
                    "Will you be my girlfriend?",
                    choices=[
                        DialogueChoice("[ Yes ]", next_id="accept"),
                        DialogueChoice("[ Of course 💞 ]", next_id="accept"),
                    ],
                ),
                DialogueNode(
                    "accept",
                    "You completed the Quest for the Heart Gem!",
                    next_id="accept_2",
                ),
                DialogueNode(
                    "accept_2",
                    "A new adventure begins -- together.",
                    next_id="accept_3",
                ),
                DialogueNode(
                    "accept_3",
                    "(Soft pixel music swells as the scene fades.)",
                    next_id="ending",
                ),
                DialogueNode(
                    "ending",
                    "The Heart Gem shines brightest when it's shared.",
                    next_id=None,
                    exit_event="show_ending",
                ),
            ],
        )

        dm.register(
            "mia_epilogue",
            [
                DialogueNode(
                    "root",
                    "The Heart Gem shines brightest when it's shared.",
                    next_id=None,
                )
            ],
        )

        dm.register(
            "sally_missing",
            [
                DialogueNode(
                    "root",
                    "I can't find my flower... It was so pretty and pink.",
                    next_id="clue",
                ),
                DialogueNode(
                    "clue",
                    "It's somewhere in this tall grass. That's where I last had it.",
                    next_id=None,
                ),
            ],
        )

        dm.register(
            "sally_flower_item",
            [
                DialogueNode(
                    "root",
                    "You gently pick up a delicate pink flower nestled in the grass.",
                    next_id=None,
                )
            ],
        )

        dm.register(
            "sally_thanks",
            [
                DialogueNode(
                    "root",
                    "You found it! Thank you, kind one.",
                    next_id="shimmer",
                ),
                DialogueNode(
                    "shimmer",
                    "Something shines near your feet...",
                    next_id="reward",
                ),
                DialogueNode(
                    "reward",
                    "**You got a Heart Shard!**",
                    next_id=None,
                    exit_event="sally_complete",
                ),
            ],
        )

        dm.register(
            "sally_repeat",
            [
                DialogueNode(
                    "root",
                    "Thank you so much again!!",
                    next_id=None,
                )
            ],
        )

        dm.register(
            "quest_item_a",
            [
                DialogueNode(
                    "root",
                    "A shimmering Heart Shard rests among the cave stones.",
                    next_id=None,
                )
            ],
        )

        dm.register(
            "quest_item_b",
            [
                DialogueNode(
                    "root",
                    "A Heart Shard gifted for lending a helping hand.",
                    next_id=None,
                )
            ],
        )

        dm.register(
            "quest_item_c",
            [
                DialogueNode(
                    "root",
                    "The final Heart Shard pulses warmly in your hands.",
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
                    "The shrine hums with the promise of a completed Heart Gem.",
                    next_id=None,
                )
            ],
        )

        dm.register(
            "quest_complete",
            [
                DialogueNode(
                    "root",
                    "Welcome, seeker of the Heart Gem. Your devotion brought its light back.",
                    next_id="continue",
                ),
                DialogueNode(
                    "continue",
                    "I will keep its glow safe. Thank you for believing in love's power.",
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

