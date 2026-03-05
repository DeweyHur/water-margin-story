"""crewAI tasks package."""
from tasks.movement_task import build_movement_task
from tasks.combat_task import build_combat_task
from tasks.investigation_task import build_investigation_task

__all__ = ["build_movement_task", "build_combat_task", "build_investigation_task"]
