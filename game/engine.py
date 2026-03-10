"""Game engine — orchestrates turns, agents, and win/loss conditions."""
from __future__ import annotations

import random
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from models import GameState, GamePhase, Hero, Town, GameEvent, EventType, HeroClass
from models.faction import Faction
from game.turn_manager import TurnManager
from game.event_system import EventSystem
from game.combat_manager import CombatManager

if TYPE_CHECKING:
    from ui.terminal_ui import TerminalUI


class GameEngine:
    """Top-level game controller."""

    def __init__(self, ui: "TerminalUI") -> None:
        self.ui = ui
        self.state = GameState()
        self.turn_manager = TurnManager(self.state)
        self.event_system = EventSystem(self.state)
        self.combat_manager = CombatManager(self.state)
        self._config_dir = Path(__file__).parent.parent / "config"

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.ui.show_title()
        self._setup()
        self.state.phase = GamePhase.PLAYING

        while not self.state.is_over():
            self.ui.show_turn_header(self.state)
            self._process_turn()
            self._check_win_conditions()

        self.ui.show_game_over(self.state)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup(self) -> None:
        self._load_factions()
        self._load_towns()
        all_heroes = self._load_hero_roster()
        all_scenarios = self._load_scenarios()

        while True:
            # 1. Scenario selection
            scenario = self.ui.choose_scenario(all_scenarios)
            self._apply_scenario(scenario, all_heroes)
            self.state.max_turns = scenario["max_turns"]
            self.state.dynasty_stability = scenario["dynasty_stability"]

            # 2. Hero selection — only playable heroes for this scenario
            playable_ids = set(scenario.get("playable_heroes", []))
            playable = [h for h in all_heroes if h.id in playable_ids]
            if not playable:
                playable = all_heroes  # fallback

            chosen = self.ui.choose_hero(playable, self.state)
            if chosen is None:
                # User pressed back — restart from scenario selection
                self.state = GameState()
                self.turn_manager = TurnManager(self.state)
                self.event_system = EventSystem(self.state)
                self.combat_manager = CombatManager(self.state)
                # Re-populate base data so map/towns are available next iteration
                self._load_factions()
                self._load_towns()
                continue
            break

        chosen.is_player_controlled = True
        chosen.player_id = "player1"
        self.state.heroes[chosen.id] = chosen
        self.state.player_ids.append("player1")

        # Add remaining heroes (already placed by _apply_scenario) to state
        for h in all_heroes:
            if h.id not in self.state.heroes:
                self.state.heroes[h.id] = h

        self.ui.show_setup_complete(self.state, chosen)

    def _load_scenarios(self) -> list[dict]:
        with open(self._config_dir / "scenarios.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data["scenarios"]

    def _apply_scenario(self, scenario: dict, heroes: list) -> None:
        """Apply initial faction town control and hero starting positions."""
        # 먼저 모든 도시와 세력을 미점령으로 초기화 (towns.yaml 기본값 무시)
        for town in self.state.towns.values():
            town.controlled_by_faction = None
        for faction in self.state.factions.values():
            faction.controlled_towns = []

        # 시나리오 town_control 적용
        town_ctrl: dict[str, list[str]] = scenario.get("town_control", {})
        for faction_id, town_ids in town_ctrl.items():
            faction = self.state.factions.get(faction_id)
            if faction:
                faction.controlled_towns = list(town_ids)
            for tid in town_ids:
                if tid in self.state.towns:
                    self.state.towns[tid].controlled_by_faction = faction_id

        # Hero starting locations
        hero_starts: dict[str, str] = scenario.get("hero_starts", {})
        hero_by_id = {h.id: h for h in heroes}
        for hero_id, town_id in hero_starts.items():
            h = hero_by_id.get(hero_id)
            if h and town_id in self.state.towns:
                h.current_town = town_id

        # Hero faction overrides (scenario can change faction_id based on story context)
        hero_factions: dict[str, str] = scenario.get("hero_factions", {})
        for hero_id, faction_id in hero_factions.items():
            h = hero_by_id.get(hero_id)
            if h:
                h.faction_id = faction_id

        # Hero starting armies
        hero_armies: dict[str, int] = scenario.get("hero_armies", {})
        for hero_id, army_size in hero_armies.items():
            h = hero_by_id.get(hero_id)
            if h:
                h.current_army = army_size


    def _load_factions(self) -> None:
        with open(self._config_dir / "factions.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for f_data in data["factions"]:
            faction = Faction(**f_data)
            self.state.factions[faction.id] = faction

    def _load_towns(self) -> None:
        with open(self._config_dir / "towns.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for t in data["towns"]:
            town = Town(**t)
            self.state.towns[town.id] = town

    def _load_hero_roster(self) -> list[Hero]:
        with open(self._config_dir / "heroes.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return [Hero(**h) for h in data["heroes"]]

    # ------------------------------------------------------------------
    # Turn processing
    # ------------------------------------------------------------------

    def _process_turn(self) -> None:
        self.state.turn += 1

        # 1. Resource Production
        self._produce_resources()

        # 2. Dynasty stability decay
        self.state.dynasty_stability -= 2
        self.event_system.fire_dynasty_events()

        # 3. Each hero takes their turn
        # Sort by agility for turn order
        sorted_heroes = sorted(self.state.heroes.values(), key=lambda x: x.agility, reverse=True)
        for hero in sorted_heroes:
            if not hero.is_alive():
                continue
            hero.restore_action_points()
            if hero.is_player_controlled:
                self.turn_manager.player_turn(hero, self.ui)
            else:
                self.turn_manager.ai_turn(hero)

        # 4. Random events
        self.event_system.fire_random_events()

    def _produce_resources(self) -> None:
        """Collect gold and food from controlled towns, scaled by admin_level."""
        for town in self.state.towns.values():
            if town.controlled_by_faction and town.controlled_by_faction in self.state.factions:
                faction = self.state.factions[town.controlled_by_faction]
                # admin_level 5 = 100% base, 1 = 20%, 10 = 200%
                multiplier = town.admin_level / 5.0
                faction.gold += int(town.tax_yield * multiplier)
                faction.food += int(town.food_yield * multiplier)

    def _check_win_conditions(self) -> None:
        # Simplified win condition: Liangshan controls Bianjing or Gao Qiu is defeated
        if self.state.towns["bianjing"].controlled_by_faction == "liangshan":
            self.state.phase = GamePhase.WON
            self.state.winner_id = "liangshan"
        elif self.state.dynasty_stability <= 0:
            self.state.phase = GamePhase.LOST
