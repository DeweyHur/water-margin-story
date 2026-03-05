"""crewAI task: investigation decision."""
from __future__ import annotations

from crewai import Task, Agent
from models import Hero, GameState


def build_investigation_task(hero: Hero, state: GameState, agent: Agent) -> Task:
    town = state.towns.get(hero.current_town)
    town_name = town.name_ko if town else hero.current_town
    clue_level = town.clue_level if town else 0

    return Task(
        description=(
            f"{hero.name_ko}이(가) {town_name}에서 정보를 수집하려 한다.\n"
            f"현재 단서 수준: {clue_level}/5\n"
            f"지략: {hero.intelligence}\n\n"
            "어떤 방법으로 정보를 수집할지 결정하라 "
            "('매수', '심문', '잠입' 중 하나). "
            "선택과 예상 클루 획득량을 반환하라."
        ),
        expected_output="정보 수집 방법과 예상 단서 획득량 (예: '잠입, +2')",
        agent=agent,
    )
