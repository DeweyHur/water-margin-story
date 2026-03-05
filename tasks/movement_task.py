"""crewAI task: movement decision for an AI hero."""
from __future__ import annotations

from crewai import Task, Agent
from models import Hero, GameState


def build_movement_task(hero: Hero, state: GameState, agent: Agent) -> Task:
    gao_qiu_town = state.towns.get(state.gao_qiu_location)
    gao_qiu_name = gao_qiu_town.name_ko if gao_qiu_town else state.gao_qiu_location
    current_town = state.towns.get(hero.current_town)
    current_name = current_town.name_ko if current_town else hero.current_town
    adjacent = current_town.adjacent if current_town else []
    adjacent_names = [state.towns[t].name_ko for t in adjacent if t in state.towns]

    return Task(
        description=(
            f"영웅 {hero.name_ko}은 현재 {current_name}에 있다.\n"
            f"고구의 마지막 목격지: {gao_qiu_name}\n"
            f"이동 가능한 마을: {', '.join(adjacent_names)}\n"
            f"왕조 안정도: {state.dynasty_stability}/100, 남은 턴: {state.turns_remaining()}\n\n"
            "최선의 이동 전략을 선택하고 목적지 마을 ID 하나를 반환하라."
        ),
        expected_output="이동할 마을 ID (예: bianjing)",
        agent=agent,
    )
