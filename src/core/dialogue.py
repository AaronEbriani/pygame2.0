from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol


class DialogueEventCallback(Protocol):
    def __call__(self, event_name: str, payload: dict | None = None) -> None: ...


@dataclass(slots=True)
class DialogueChoice:
    text: str
    next_id: str | None = None
    event: str | None = None


@dataclass(slots=True)
class DialogueNode:
    node_id: str
    text: str
    next_id: str | None = None
    choices: list[DialogueChoice] = field(default_factory=list)
    enter_event: str | None = None
    exit_event: str | None = None

    def has_choices(self) -> bool:
        return bool(self.choices)


class DialogueSession:
    """Tracks the current position inside a dialogue graph."""

    def __init__(
        self,
        nodes: dict[str, DialogueNode],
        start_id: str,
        event_callback: DialogueEventCallback | None = None,
    ) -> None:
        if start_id not in nodes:
            raise ValueError(f"Dialogue node '{start_id}' not found.")

        self.nodes = nodes
        self.current_id = start_id
        self.event_callback = event_callback
        self.choice_index = 0

        self._dispatch_enter_event(self.current_node)

    @property
    def current_node(self) -> DialogueNode:
        return self.nodes[self.current_id]

    def move_choice(self, offset: int) -> None:
        node = self.current_node
        if not node.has_choices():
            return
        self.choice_index = (self.choice_index + offset) % len(node.choices)

    def confirm(self) -> bool:
        """Advance the dialogue. Returns True when the session completes."""
        node = self.current_node
        if node.has_choices():
            choice = node.choices[self.choice_index]
            if self.event_callback and choice.event:
                self.event_callback(choice.event, {"node_id": node.node_id})
            next_id = choice.next_id
        else:
            next_id = node.next_id
            if self.event_callback and node.exit_event:
                self.event_callback(node.exit_event, {"node_id": node.node_id})

        if next_id is None:
            # Dialogue finished.
            return True

        if next_id not in self.nodes:
            raise ValueError(f"Dialogue node '{next_id}' not found.")

        self.current_id = next_id
        self.choice_index = 0
        self._dispatch_enter_event(self.current_node)
        return False

    def cancel(self) -> None:
        node = self.current_node
        if self.event_callback and node.exit_event:
            self.event_callback(node.exit_event, {"node_id": node.node_id})

    def _dispatch_enter_event(self, node: DialogueNode) -> None:
        if self.event_callback and node.enter_event:
            self.event_callback(node.enter_event, {"node_id": node.node_id})


class DialogueManager:
    """Registry of dialogue graphs."""

    def __init__(self, event_callback: DialogueEventCallback | None = None) -> None:
        self.dialogues: dict[str, dict[str, DialogueNode]] = {}
        self.event_callback = event_callback

    def register(self, dialogue_id: str, nodes: Iterable[DialogueNode]) -> None:
        mapping = {node.node_id: node for node in nodes}
        self.dialogues[dialogue_id] = mapping

    def start(self, dialogue_id: str, start_node: str = "root") -> DialogueSession:
        if dialogue_id not in self.dialogues:
            raise ValueError(f"Dialogue '{dialogue_id}' not registered.")
        return DialogueSession(self.dialogues[dialogue_id], start_node, self.event_callback)

