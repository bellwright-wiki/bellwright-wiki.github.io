"""Data models used by the quest generator."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class QuestItem:
    name: str
    min_amount: int
    max_amount: int


@dataclass(frozen=True)
class QuestReward:
    name: str
    min_amount: int | None
    max_amount: int | None
    chance: float | None = None
    per_roll: bool = False


@dataclass(frozen=True)
class QuestStep:
    name: str
    source: Path
    summary: str = ""
    completion_text: str = ""
    group_next: bool = False
    type: str = ""
    optional: bool = False
    items: tuple[QuestItem, ...] = field(default_factory=tuple)
    npc: str = ""


@dataclass(frozen=True)
class Quest:
    name: str
    category: str
    source: Path
    relative_path: tuple[str, ...]
    title: str
    summary: str = ""
    giver: str = ""
    npcs: tuple[str, ...] = field(default_factory=tuple)
    steps: tuple[QuestStep, ...] = field(default_factory=tuple)
    rewards: tuple[QuestReward, ...] = field(default_factory=tuple)
    money_reward: int = 0
    renown_reward: int = 0
    village_trust_reward: int = 0
    village_prosperity_reward: int = 0


@dataclass
class QuestNode:
    name: str
    quest: Quest | None = None
    children: dict[str, "QuestNode"] = field(default_factory=dict)
