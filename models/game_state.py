"""GameState model — full serializable game state."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from models.hero import Hero
from models.town import Town
from models.army import Army
from models.event import GameEvent
from models.faction import Faction


class GamePhase(str, Enum):
    SETUP = "setup"
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


class GameState(BaseModel):
    """Complete, serializable state of a Water Margin game session."""

    # Turn tracking
    turn: int = 0
    max_turns: int = 30

    # Game phase
    phase: GamePhase = GamePhase.SETUP

    # Entities (keyed by id)
    heroes: dict[str, Hero] = Field(default_factory=dict)
    towns: dict[str, Town] = Field(default_factory=dict)
    factions: dict[str, Faction] = Field(default_factory=dict)
    armies: dict[str, Army] = Field(default_factory=dict)   # NEW

    # Story / win condition
    gao_qiu_location: str = "bianjing"
    dynasty_stability: int = Field(default=100, ge=0, le=100)
    winner_id: Optional[str] = None

    # Multiplayer
    player_ids: list[str] = Field(default_factory=list)

    # Event log
    events: list[GameEvent] = Field(default_factory=list)

    def is_over(self) -> bool:
        return self.phase in (GamePhase.WON, GamePhase.LOST)

    def log_event(self, event: GameEvent) -> None:
        self.events.append(event)

    def get_player_hero(self) -> Optional[Hero]:
        for hero in self.heroes.values():
            if hero.is_player_controlled:
                return hero
        return None