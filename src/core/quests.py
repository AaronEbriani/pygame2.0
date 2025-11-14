from __future__ import annotations

from dataclasses import dataclass, field

from core.settings import QUEST_FIND_ARTIFACTS


@dataclass
class QuestState:
    quest_id: str
    description: str
    items_required: int
    items_collected: set[str] = field(default_factory=set)
    completed: bool = False

    def record_item(self, object_id: str) -> None:
        if not self.completed:
            self.items_collected.add(object_id)
            if len(self.items_collected) >= self.items_required:
                self.completed = True


class QuestManager:
    def __init__(self) -> None:
        self.quests: dict[str, QuestState] = {
            QUEST_FIND_ARTIFACTS: QuestState(
                quest_id=QUEST_FIND_ARTIFACTS,
                description="Gather the three Heart Shards scattered across the region.",
                items_required=3,
            )
        }

    def handle_event(self, event_name: str, payload: dict | None = None) -> list[str]:
        if event_name != "quest_item_collected":
            return []

        payload = payload or {}
        object_id = payload.get("object_id")
        if not object_id:
            return []

        state = self.quests[QUEST_FIND_ARTIFACTS]
        pre_complete = state.completed
        state.record_item(object_id)
        if not pre_complete and state.completed:
            return ["quest_completed"]
        return []

    def quest_completed(self, quest_id: str) -> bool:
        return self.quests.get(quest_id, QuestState("", "", 0)).completed

