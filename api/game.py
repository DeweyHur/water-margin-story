from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from game.turn_manager import TurnManager
from models import EventType, GameEvent, GamePhase, GameState, Hero, Town
from models.faction import Faction
from models.hero import HeroClass

APP_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = APP_ROOT / "config"

app = FastAPI(title="Water Margin Story Web API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NewGameRequest(BaseModel):
    scenario_id: str
    hero_id: str


class ActionRequest(BaseModel):
    state: dict[str, Any]
    action: str
    destination_id: str | None = None
    candidate_id: str | None = None


class _NoopConsole:
    def print(self, *_args: Any, **_kwargs: Any) -> None:
        return


class WebUIBridge:
    def __init__(self, payload: ActionRequest) -> None:
        self.payload = payload
        self.messages: list[str] = []
        self.console = _NoopConsole()

    def choose_destination(self, _hero: Hero, _town: Town, _state: GameState) -> str | None:
        return self.payload.destination_id

    def choose_party_candidate(self, _hero: Hero, _candidates: list[Hero], _state: GameState) -> str | None:
        return self.payload.candidate_id

    def show_message(self, message: str) -> None:
        self.messages.append(message)

    def show_action_blocked(self, reason: str, details: list[str] | None = None) -> None:
        line = reason
        if details:
            line += " | " + " / ".join(details)
        self.messages.append(line)

    def wait_for_continue(self, _prompt: str = "") -> None:
        return

    def show_recruit_preview(self, *_args: Any, **_kwargs: Any) -> bool:
        return True

    def show_recruit_animation(self, *_args: Any, **_kwargs: Any) -> None:
        return

    def show_admin_preview(self, *_args: Any, **_kwargs: Any) -> bool:
        return True

    def show_admin_animation(self, *_args: Any, **_kwargs: Any) -> None:
        return

    def show_battle_announcement(self, *_args: Any, **_kwargs: Any) -> None:
        return

    def show_battle_deployment(self, *_args: Any, **_kwargs: Any) -> None:
        return

    def make_round_callback(self, *_args: Any, **_kwargs: Any):
        return lambda *_a, **_k: None

    def show_battle_result(self, *_args: Any, **_kwargs: Any) -> None:
        return

    def show_battle_map_update(self, *_args: Any, **_kwargs: Any) -> None:
        return


def _load_yaml(name: str) -> dict[str, Any]:
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_base_state() -> tuple[GameState, list[Hero], list[dict[str, Any]]]:
    state = GameState()

    for f_data in _load_yaml("factions.yaml")["factions"]:
        faction = Faction(**f_data)
        state.factions[faction.id] = faction

    for t_data in _load_yaml("towns.yaml")["towns"]:
        town = Town(**t_data)
        state.towns[town.id] = town

    heroes = [Hero(**h) for h in _load_yaml("heroes.yaml")["heroes"]]
    scenarios = _load_yaml("scenarios.yaml")["scenarios"]
    return state, heroes, scenarios


def _apply_scenario(state: GameState, scenario: dict[str, Any], heroes: list[Hero]) -> None:
    for town in state.towns.values():
        town.controlled_by_faction = None
    for faction in state.factions.values():
        faction.controlled_towns = []

    town_ctrl: dict[str, list[str]] = scenario.get("town_control", {})
    for faction_id, town_ids in town_ctrl.items():
        faction = state.factions.get(faction_id)
        if faction:
            faction.controlled_towns = list(town_ids)
        for tid in town_ids:
            if tid in state.towns:
                state.towns[tid].controlled_by_faction = faction_id

    hero_starts: dict[str, str] = scenario.get("hero_starts", {})
    hero_by_id = {h.id: h for h in heroes}
    for hero_id, town_id in hero_starts.items():
        h = hero_by_id.get(hero_id)
        if h and town_id in state.towns:
            h.current_town = town_id

    hero_factions: dict[str, str] = scenario.get("hero_factions", {})
    for hero_id, faction_id in hero_factions.items():
        h = hero_by_id.get(hero_id)
        if h:
            h.faction_id = faction_id

    hero_armies: dict[str, int] = scenario.get("hero_armies", {})
    for hero_id, army_size in hero_armies.items():
        h = hero_by_id.get(hero_id)
        if h:
            h.current_army = army_size

    for h in heroes:
        if h.personal_gold == 0:
            h.personal_gold = max(50, h.reputation * 10)


def _contact_candidates(state: GameState, hero: Hero) -> list[Hero]:
    candidates: list[Hero] = []
    for h in state.heroes.values():
        if h.id == hero.id or not h.is_alive() or h.current_town != hero.current_town:
            continue
        if h.is_player_controlled or h.following_hero_id:
            continue
        if hero.faction_id == "neutral":
            if h.faction_id == "neutral":
                candidates.append(h)
        elif h.faction_id in (hero.faction_id, "neutral"):
            candidates.append(h)
    return candidates


def _available_actions(state: GameState, hero: Hero) -> list[str]:
    town = state.towns[hero.current_town]
    is_own = town.controlled_by_faction == hero.faction_id
    is_neutral = hero.faction_id == "neutral"
    is_enemy_town = town.controlled_by_faction not in (hero.faction_id, None)

    actions = ["move", "investigate", "recruit"]
    if is_own:
        actions.append("admin")
    elif hero.current_army > 0 or not is_neutral:
        actions.append("siege")

    if _contact_candidates(state, hero):
        actions.append("rally")

    if hero.hero_class in (HeroClass.WARRIOR, HeroClass.ROGUE):
        if is_enemy_town:
            actions.append("class_action")
    else:
        actions.append("class_action")

    actions += ["rest", "end"]
    return actions


def _ui_hints(state: GameState, hero: Hero) -> dict[str, Any]:
    town = state.towns[hero.current_town]
    return {
        "actions": _available_actions(state, hero),
        "destinations": [
            {
                "id": tid,
                "name_ko": state.towns[tid].name_ko,
            }
            for tid in town.adjacent if tid in state.towns
        ],
        "contact_candidates": [
            {
                "id": h.id,
                "name_ko": h.name_ko,
                "hero_class": h.hero_class.value,
                "army": h.current_army,
            }
            for h in _contact_candidates(state, hero)
        ],
    }


def _produce_resources(state: GameState) -> None:
    for town in state.towns.values():
        if town.controlled_by_faction and town.controlled_by_faction in state.factions:
            faction = state.factions[town.controlled_by_faction]
            multiplier = town.admin_level / 5.0
            faction.gold += int(town.tax_yield * multiplier)
            faction.food += int(town.food_yield * multiplier)


def _end_turn(state: GameState, tm: TurnManager) -> list[str]:
    state.turn += 1
    _produce_resources(state)
    state.dynasty_stability = max(0, state.dynasty_stability - 2)

    ai_logs: list[str] = []
    sorted_heroes = sorted(state.heroes.values(), key=lambda x: x.agility, reverse=True)
    for h in sorted_heroes:
        if not h.is_alive() or h.is_player_controlled:
            continue
        h.restore_action_points()
        if h.following_hero_id:
            leader = state.heroes.get(h.following_hero_id)
            if leader and leader.is_alive():
                h.current_town = leader.current_town
            continue
        ai_logs.extend(tm.ai_turn(h))

    player = state.get_player_hero()
    if player:
        player.restore_action_points()

    if "bianjing" in state.towns and state.towns["bianjing"].controlled_by_faction == "liangshan":
        state.phase = GamePhase.WON
        state.winner_id = "liangshan"
    elif state.dynasty_stability <= 0:
        state.phase = GamePhase.LOST

    return ai_logs


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/game/meta")
def game_meta() -> dict[str, Any]:
    _state, heroes, scenarios = _load_base_state()
    return {
        "scenarios": [
            {
                "id": s["id"],
                "name_ko": s["name_ko"],
                "year": s["year"],
                "playable_heroes": s.get("playable_heroes", []),
            }
            for s in scenarios
        ],
        "heroes": [
            {
                "id": h.id,
                "name_ko": h.name_ko,
                "hero_class": h.hero_class.value,
            }
            for h in heroes
        ],
    }


@app.post("/api/game/new")
def new_game(req: NewGameRequest) -> dict[str, Any]:
    state, heroes, scenarios = _load_base_state()

    scenario = next((s for s in scenarios if s["id"] == req.scenario_id), None)
    if not scenario:
        return {"error": "scenario_not_found"}

    _apply_scenario(state, scenario, heroes)
    state.max_turns = scenario["max_turns"]
    state.dynasty_stability = scenario["dynasty_stability"]
    state.phase = GamePhase.PLAYING

    chosen = next((h for h in heroes if h.id == req.hero_id), None)
    if not chosen:
        return {"error": "hero_not_found"}

    chosen.is_player_controlled = True
    chosen.player_id = "player1"
    state.heroes[chosen.id] = chosen
    state.player_ids.append("player1")

    for h in heroes:
        if h.id not in state.heroes:
            state.heroes[h.id] = h

    return {
        "state": state.model_dump(mode="json"),
        "messages": [f"{chosen.name_ko}으로 게임을 시작했습니다."],
        "ai_logs": [],
        "ui_hints": _ui_hints(state, chosen),
    }


@app.post("/api/game/action")
def game_action(req: ActionRequest) -> dict[str, Any]:
    state = GameState.model_validate(req.state)
    hero = state.get_player_hero()
    if not hero:
        return {"error": "player_hero_not_found"}

    tm = TurnManager(state)
    ui = WebUIBridge(req)

    if req.action == "move":
        tm._do_move_player(hero, ui)
    elif req.action == "investigate":
        tm._do_investigate(hero, ui)
        hero.action_points -= 1
    elif req.action == "recruit":
        if tm._do_recruit(hero, ui):
            hero.action_points -= 1
    elif req.action == "admin":
        if tm._do_admin(hero, ui):
            hero.action_points -= 1
    elif req.action == "class_action":
        if tm._do_class_action(hero, ui):
            hero.action_points -= 1
    elif req.action == "rally":
        if tm._do_rally_party(hero, ui):
            hero.action_points -= 1
    elif req.action == "siege":
        if tm._do_siege(hero, ui):
            hero.action_points -= 2
    elif req.action == "rest":
        tm._do_rest(hero, ui)
        hero.action_points -= 1
    elif req.action == "end":
        hero.action_points = 0
    else:
        return {"error": "unsupported_action", "action": req.action}

    ai_logs: list[str] = []
    if hero.action_points <= 0 or req.action == "end":
        ai_logs = _end_turn(state, tm)

    state.log_event(GameEvent(
        type=EventType.MOVEMENT,
        actor_id=hero.id,
        message=f"플레이어 행동: {req.action}",
    ))

    updated_player = state.get_player_hero()
    hints = _ui_hints(state, updated_player) if updated_player else {}

    return {
        "state": state.model_dump(mode="json"),
        "messages": ui.messages,
        "ai_logs": ai_logs,
        "ui_hints": hints,
    }
