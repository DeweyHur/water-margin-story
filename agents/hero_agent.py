"""crewAI agent for AI-controlled hero NPCs."""
from __future__ import annotations

from crewai import Agent
from models.hero import Hero
from tools.movement_tool import MovementTool
from tools.investigation_tool import InvestigationTool
from tools.combat_tool import CombatTool
from config.llm_config import get_game_llm


def build_hero_agent(hero: Hero) -> Agent:
    """Build an NPC hero agent that races the player to catch Gao Qiu."""
    return Agent(
        role=f"{hero.name_ko} ({hero.name_zh}) — {hero.nickname}",
        goal=(
            "고구의 행방을 추적하고, 그의 위치를 파악하면 즉시 타도하라. "
            "다른 영웅들보다 먼저 고구를 잡아야 한다."
        ),
        backstory=hero.description,
        tools=[MovementTool(), InvestigationTool(), CombatTool()],
        llm=get_game_llm(),
        verbose=False,
        allow_delegation=False,
        max_iter=5,
    )
