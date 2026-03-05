from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    MOVEMENT = "movement"
    COMBAT = "combat"
    INVESTIGATION = "investigation"
    ENCOUNTER = "encounter"
    DYNASTY_CRISIS = "dynasty_crisis"
    GAO_QIU_SPOTTED = "gao_qiu_spotted"
    HERO_DEFEATED = "hero_defeated"
    GAME_WON = "game_won"
    GAME_LOST = "game_lost"


class GameEvent(BaseModel):
    """A discrete game event that updates state and can be logged / broadcast."""

    type: EventType
    actor_id: Optional[str] = None       # hero or system
    target_id: Optional[str] = None      # town or hero
    payload: dict[str, Any] = Field(default_factory=dict)
    turn: int = 0
    message: str = ""
