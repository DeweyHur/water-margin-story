"""crewAI tool: investigate a town for clues about Gao Qiu."""
from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class InvestigationInput(BaseModel):
    hero_id: str = Field(description="조사하는 영웅 ID")
    town_id: str = Field(description="조사 대상 마을 ID")


class InvestigationTool(BaseTool):
    name: str = "investigation_tool"
    description: str = (
        "마을에서 고구의 행방에 관한 정보를 수집한다. "
        "hero_id와 town_id를 입력하면 수집된 단서를 반환한다."
    )
    args_schema: type[BaseModel] = InvestigationInput

    def _run(self, hero_id: str, town_id: str) -> str:
        return (
            f"{hero_id}이(가) {town_id}에서 고구 관련 정보 수집. "
            "단서 수준 증가는 엔진 사이클에서 처리된다."
        )
