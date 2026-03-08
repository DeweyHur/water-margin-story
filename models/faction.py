from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class Faction(BaseModel):
    """Represents a political entity in the game (e.g., Liangshan, Imperial, Jin)."""

    id: str
    name_ko: str
    name_zh: str = ""
    leader_id: str  # Leader hero ID (e.g., song_jiang, gao_qiu)
    gold: int = 5000
    food: int = 5000
    prestige: int = 0  # Influence for diplomacy and recruitment
    controlled_towns: list[str] = Field(default_factory=list)
    relations: dict[str, int] = Field(default_factory=dict)  # Faction ID -> Opinion (-100 to 100)
    color: str = "white"           # Rich color tag for UI rendering
    description: Optional[str] = None
