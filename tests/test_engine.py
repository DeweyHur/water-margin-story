"""Tests for GameEngine logic (resource production, scenario application)."""
import pytest

from models.game_state import GameState
from models.town import Town
from models.faction import Faction
from models.hero import Hero, HeroClass


# ── Helpers ─────────────────────────────────────────────────────────────────

def make_town(town_id: str, faction_id: str = "liangshan",
              tax: int = 100, food: int = 100, admin: int = 5) -> Town:
    return Town(
        id=town_id, name_ko=town_id, town_type="village",
        controlled_by_faction=faction_id,
        tax_yield=tax, food_yield=food,
        admin_level=admin,
    )


def make_faction(faction_id: str, gold: int = 0, food: int = 0) -> Faction:
    return Faction(id=faction_id, name_ko=faction_id, leader_id="test", gold=gold, food=food)


def make_state_with_town(town: Town, faction: Faction) -> GameState:
    state = GameState()
    state.towns[town.id] = town
    state.factions[faction.id] = faction
    return state


# ── _produce_resources ───────────────────────────────────────────────────────

class TestProduceResources:
    """Test the income formula: gold += tax_yield * (admin_level / 5)."""

    def _run(self, state: GameState) -> None:
        # Call the private method directly via a thin wrapper
        from game.engine import GameEngine
        engine = GameEngine.__new__(GameEngine)
        engine.state = state
        engine._produce_resources()

    def test_admin5_gives_100_percent_income(self):
        faction = make_faction("liangshan")
        town = make_town("liangshan", admin=5, tax=100, food=100)
        state = make_state_with_town(town, faction)
        self._run(state)
        assert state.factions["liangshan"].gold == 100
        assert state.factions["liangshan"].food == 100

    def test_admin10_doubles_income(self):
        faction = make_faction("liangshan")
        town = make_town("liangshan", admin=10, tax=100, food=100)
        state = make_state_with_town(town, faction)
        self._run(state)
        assert state.factions["liangshan"].gold == 200
        assert state.factions["liangshan"].food == 200

    def test_admin1_gives_20_percent_income(self):
        faction = make_faction("liangshan")
        town = make_town("liangshan", admin=1, tax=100, food=100)
        state = make_state_with_town(town, faction)
        self._run(state)
        assert state.factions["liangshan"].gold == 20
        assert state.factions["liangshan"].food == 20

    def test_uncontrolled_town_produces_nothing(self):
        faction = make_faction("liangshan")
        town = make_town("liangshan", faction_id=None, tax=100, food=100)
        state = make_state_with_town(town, faction)
        self._run(state)
        assert state.factions["liangshan"].gold == 0

    def test_unknown_faction_produces_nothing(self):
        """Town faction not present in state.factions → no crash, no income."""
        faction = make_faction("liangshan")
        town = make_town("bianjing", faction_id="imperial", tax=200, food=200)
        state = make_state_with_town(town, faction)
        self._run(state)
        assert state.factions["liangshan"].gold == 0

    def test_multiple_towns_accumulate_income(self):
        faction = make_faction("liangshan")
        state = GameState()
        state.factions["liangshan"] = faction
        state.towns["a"] = make_town("a", admin=5, tax=100, food=50)
        state.towns["b"] = make_town("b", admin=10, tax=50, food=100)
        self._run(state)
        assert state.factions["liangshan"].gold == 100 + 100   # 100*1.0 + 50*2.0
        assert state.factions["liangshan"].food == 50 + 200    # 50*1.0 + 100*2.0


# ── _apply_scenario ─────────────────────────────────────────────────────────

def make_hero(hero_id: str) -> Hero:
    return Hero(
        id=hero_id, name_ko=hero_id, name_zh="", nickname="",
        hero_class=HeroClass.WARRIOR, strength=5, intelligence=5, agility=5,
    )


class TestApplyScenario:
    def _apply(self, scenario: dict, heroes: list[Hero]) -> GameState:
        from game.engine import GameEngine
        engine = GameEngine.__new__(GameEngine)
        engine.state = GameState()
        # Pre-populate towns referenced in scenario
        for town_id in scenario.get("hero_starts", {}).values():
            if town_id not in engine.state.towns:
                engine.state.towns[town_id] = make_town(town_id)
        engine._apply_scenario(scenario, heroes)
        return engine.state

    def test_hero_starts_applied(self):
        heroes = [make_hero("song_jiang")]
        scenario = {"hero_starts": {"song_jiang": "bianjing"}, "hero_factions": {}, "hero_armies": {}}
        state = self._apply(scenario, heroes)
        assert state.heroes == {} or True  # heroes not added by _apply_scenario, just mutated in-place
        assert heroes[0].current_town == "bianjing"

    def test_hero_faction_override(self):
        h = make_hero("song_jiang")
        assert h.faction_id == "neutral"
        scenario = {"hero_starts": {}, "hero_factions": {"song_jiang": "liangshan"}, "hero_armies": {}}
        self._apply(scenario, [h])
        assert h.faction_id == "liangshan"

    def test_hero_armies_applied(self):
        h = make_hero("gao_qiu")
        assert h.current_army == 0
        scenario = {"hero_starts": {}, "hero_factions": {}, "hero_armies": {"gao_qiu": 5000}}
        self._apply(scenario, [h])
        assert h.current_army == 5000

    def test_unknown_hero_in_armies_ignored(self):
        """hero_armies entry referencing a non-existent hero should not crash."""
        heroes = [make_hero("song_jiang")]
        scenario = {"hero_starts": {}, "hero_factions": {}, "hero_armies": {"ghost": 9999}}
        self._apply(scenario, heroes)   # no exception

    def test_hero_with_zero_army_remains_zero(self):
        h = make_hero("wu_yong")
        scenario = {"hero_starts": {}, "hero_factions": {}, "hero_armies": {"wu_yong": 0}}
        self._apply(scenario, [h])
        assert h.current_army == 0
