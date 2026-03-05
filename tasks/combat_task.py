"""crewAI task: combat decision."""
from __future__ import annotations

from crewai import Task, Agent
from models import Hero, GameState


def build_combat_task(hero: Hero, state: GameState, agent: Agent) -> Task:
    town = state.towns.get(hero.current_town)
    town_name = town.name_ko if town else hero.current_town

    return Task(
        description=(
            f"{hero.name_ko}이(가) {town_name}에서 고구의 병력과 조우했다!\n"
            f"영웅 현재 HP: {hero.hp}/{hero.max_hp}\n"
            f"힘: {hero.strength}, 지략: {hero.intelligence}\n\n"
            "이 전투를 어떻게 해결할지 결정하라. "
            "'공격', '기습', '퇴각' 중 하나를 선택하고 그 이유를 설명하라."
        ),
        expected_output="전투 전략 ('공격', '기습', 또는 '퇴각') 및 이유",
        agent=agent,
    )
