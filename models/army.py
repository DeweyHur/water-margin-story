"""Army model — military forces for Water Margin strategy game."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class UnitType(str, Enum):
    INFANTRY = "infantry"   # 보병
    CAVALRY = "cavalry"     # 기병
    ARCHER = "archer"       # 궁병
    NAVY = "navy"           # 수군


class ArmyStatus(str, Enum):
    ACTIVE = "active"
    ROUTED = "routed"           # 패주
    BESIEGING = "besieging"     # 공성 중
    GARRISONED = "garrisoned"   # 수비 중


class Army(BaseModel):
    """A military unit commanded by a general (Hero)."""

    id: str
    name: str
    faction_id: str
    general_id: Optional[str] = None

    unit_type: UnitType = UnitType.INFANTRY
    troops: int = Field(default=1000, ge=0)
    max_troops: int = Field(default=1000, ge=1)

    morale: int = Field(default=80, ge=0, le=100)   # 사기
    training: int = Field(default=5, ge=1, le=10)   # 훈련도
    equipment: int = Field(default=5, ge=1, le=10)  # 장비 수준

    catapults: int = 0        # 투석기
    siege_towers: int = 0     # 운제
    battering_rams: int = 0   # 공성 충차

    status: ArmyStatus = ArmyStatus.ACTIVE
    location: str = "liangshan"

    @property
    def combat_power(self) -> float:
        """Effective combat power accounting for morale, training, equipment."""
        if self.troops <= 0:
            return 0.0
        return self.troops * (self.morale / 100.0) * (self.training + self.equipment) / 20.0

    @property
    def siege_power(self) -> float:
        """Extra offensive power from siege engines."""
        return (
            self.catapults * 50
            + self.siege_towers * 30
            + self.battering_rams * 20
        ) * (self.morale / 100.0)

    def is_active(self) -> bool:
        return self.troops > 0 and self.status != ArmyStatus.ROUTED

    def apply_casualties(self, losses: int) -> None:
        self.troops = max(0, self.troops - losses)
        if self.troops == 0:
            self.status = ArmyStatus.ROUTED
            self.morale = 0

    def suffer_morale_loss(self, amount: int) -> None:
        self.morale = max(0, self.morale - amount)
        if self.morale < 20 and self.troops < self.max_troops * 0.3:
            self.status = ArmyStatus.ROUTED

    def recover(self, troops: int = 0, morale: int = 10) -> None:
        self.troops = min(self.max_troops, self.troops + troops)
        self.morale = min(100, self.morale + morale)
        if self.status == ArmyStatus.ROUTED and self.morale >= 40:
            self.status = ArmyStatus.ACTIVE