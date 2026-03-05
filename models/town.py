"""Town model."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Town(BaseModel):
    """A strategic location on the Water Margin map."""

    id: str
    name_ko: str
    name_zh: str = ""
    town_type: str = "village"          # village / fortress / metropolis
    population: int = 5000
    max_garrison: int = 5000
    tax_yield: int = 100
    food_yield: int = 100
    defense_level: int = Field(default=3, ge=1, le=10)
    adjacent: list[str] = Field(default_factory=list)
    garrison_strength: int = Field(default=3, ge=0, le=10)
    controlled_by_faction: Optional[str] = None

    # Investigation / intel
    gao_qiu_presence: int = Field(default=0, ge=0, le=3)  # 0=none 3=confirmed
    clue_level: int = Field(default=0, ge=0, le=5)

    # Siege / battle fields (NEW)
    wall_hp: int = Field(default=100, ge=0)    # 성벽 HP
    max_wall_hp: int = Field(default=100, ge=1)

    def is_fortified(self) -> bool:
        return self.town_type in ("fortress", "metropolis")

    def wall_integrity(self) -> float:
        """0.0–1.0 remaining wall strength."""
        return self.wall_hp / self.max_wall_hp

    def repair_walls(self, amount: int = 20) -> None:
        self.wall_hp = min(self.max_wall_hp, self.wall_hp + amount)