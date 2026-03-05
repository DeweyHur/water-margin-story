"""crewAI tool: engage in combat."""
from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class CombatInput(BaseModel):
    attacker_id: str = Field(description="공격하는 영웅 ID")
    target_id: str = Field(description="공격 대상 ID (적 또는 'gao_qiu')")
    town_id: str = Field(description="전투가 벌어지는 마을 ID")


class CombatTool(BaseTool):
    name: str = "combat_tool"
    description: str = (
        "영웅이 적 또는 고구와 전투를 벌인다. "
        "attacker_id, target_id, town_id를 입력하면 전투 결과 서술을 반환한다."
    )
    args_schema: type[BaseModel] = CombatInput

    def _run(self, attacker_id: str, target_id: str, town_id: str) -> str:
        return (
            f"{attacker_id}이(가) {town_id}에서 {target_id}와 교전. "
            "전투 결과는 힘/전략 스탯에 따라 엔진이 결정한다."
        )
