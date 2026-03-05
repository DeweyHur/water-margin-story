# Water Margin Story - Copilot Instructions

## Project Overview
A crewAI-powered strategy game inspired by the classic Chinese novel "Water Margin" (水滸傳).
Players choose a hero, explore towns, and race to defeat Gao Qiu (高俅) before the Song dynasty
falls to the Jin dynasty.

## Tech Stack
- Python 3.11+
- crewAI (multi-agent framework for AI-controlled NPCs and game logic)
- Rich (terminal UI)
- Pydantic (data models)

## Architecture
- `agents/` — crewAI agents (NPC heroes, Gao Qiu, advisors)
- `tasks/` — crewAI tasks for game events and AI decisions
- `models/` — Pydantic data models (Hero, Town, GameState, etc.)
- `game/` — core game loop, turn engine, event system
- `config/` — YAML configs for heroes, towns, events
- `tools/` — crewAI tools for movement, combat, investigation
- `main.py` — entry point

## Coding Guidelines
- All game state must be serializable (Pydantic models) for future multiplayer support
- Agents use crewAI's Agent/Task/Crew pattern
- Design for single-player vs AI first; abstract player interface for multiplayer extension
- Keep game logic decoupled from UI layer
- Use type hints throughout
