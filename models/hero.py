from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class HeroClass(str, Enum):
    WARRIOR = "warrior"       # 무장 — high combat strength
    STRATEGIST = "strategist" # 군사 — reveals Gao Qiu's location faster
    RANGER = "ranger"         # 유협 — moves farther each turn
    ROGUE = "rogue"           # 의적 — gathers intelligence more effectively


class Hero(BaseModel):
    """A playable or AI-controlled hero from the Water Margin roster."""

    id: str
    name_ko: str
    name_zh: str
    nickname: str
    hero_class: HeroClass
    strength: int = Field(ge=1, le=10)
    intelligence: int = Field(ge=1, le=10)
    agility: int = Field(ge=1, le=10)
    reputation: int = Field(default=0, ge=0, le=100)
    description: str = ""

    # Strategy Expansion Fields
    faction_id: str = "neutral"
    leadership: int = Field(default=5, ge=1, le=10)  # Command and training efficiency
    loyalty: int = Field(default=100, ge=0, le=100) # Chance of betrayal
    skills: list[str] = Field(default_factory=list)  # Unique skill IDs
    current_army: int = 0   # Current number of troops commanded

    # Runtime state (not serialised to config YAML)
    current_town: str = "liangshan"
    hp: int = 100
    max_hp: int = 100
    action_points: int = 3
    is_player_controlled: bool = False
    player_id: Optional[str] = None   # None → AI-controlled

    def is_alive(self) -> bool:
        return self.hp > 0

    def restore_action_points(self) -> None:
        self.action_points = 3

    def move_cost(self) -> int:
        """Movement costs 1 AP; Rangers spend 0 extra on the first extra step."""
        return 1
