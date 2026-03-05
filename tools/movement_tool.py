"""crewAI tool: move a hero or Gao Qiu to an adjacent town."""
from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class MovementInput(BaseModel):
    actor_id: str = Field(description="영웅 ID 또는 'gao_qiu'")
    destination_town_id: str = Field(description="이동할 마을 ID")


class MovementTool(BaseTool):
    name: str = "movement_tool"
    description: str = (
        "영웅이나 고구를 인접한 마을로 이동시킨다. "
        "actor_id와 destination_town_id를 입력하면 이동 결과를 반환한다."
    )
    args_schema: type[BaseModel] = MovementInput

    def _run(self, actor_id: str, destination_town_id: str) -> str:
        # Actual state mutation occurs in TurnManager; tools return descriptions
        # for agent reasoning. Real movement is applied by the engine.
        return (
            f"{actor_id}이(가) {destination_town_id}(으)로 이동 시도. "
            "이동은 다음 엔진 사이클에 적용된다."
        )
