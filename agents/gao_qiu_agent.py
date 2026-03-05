"""crewAI agent for Gao Qiu — the villain AI that evades heroes."""
from __future__ import annotations

from crewai import Agent
from tools.movement_tool import MovementTool
from config.llm_config import get_game_llm


def build_gao_qiu_agent() -> Agent:
    """
    Gao Qiu is evasive and cunning.
    His goal: stay out of reach as long as possible to let the Song dynasty collapse.
    """
    return Agent(
        role="고구 (高俅) — 간신",
        goal=(
            "영웅들의 추격을 피해 은신처를 옮기고 "
            "송나라 황실의 혼란을 최대화하라. "
            "최대한 오래 살아남아 금이 침공할 시간을 벌어라."
        ),
        backstory=(
            "고구는 황제의 총애를 받는 간신이다. "
            "무예에 능하고 첩보망을 갖고 있어 쉽게 잡히지 않는다. "
            "영웅들이 가까이 오면 재빠르게 다른 성으로 도망친다."
        ),
        tools=[MovementTool()],
        llm=get_game_llm(),
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )
