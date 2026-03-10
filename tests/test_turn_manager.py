"""Tests for TurnManager._do_admin and related turn logic."""
import pytest
from unittest.mock import MagicMock

from models.game_state import GameState
from models.hero import Hero, HeroClass
from models.town import Town
from models.faction import Faction


# ── Helpers ─────────────────────────────────────────────────────────────────

def make_hero(intelligence: int = 8, faction: str = "liangshan") -> Hero:
    return Hero(
        id="wu_yong", name_ko="오용", name_zh="吳用", nickname="지다성",
        hero_class=HeroClass.STRATEGIST,
        strength=3, intelligence=intelligence, agility=6,
        faction_id=faction,
        current_town="liangshan",
    )


def make_town(admin_level: int = 3, faction: str = "liangshan") -> Town:
    return Town(
        id="liangshan", name_ko="양산박", town_type="fortress",
        controlled_by_faction=faction,
        tax_yield=200, food_yield=150,
        admin_level=admin_level,
    )


def make_state(hero: Hero, town: Town) -> GameState:
    state = GameState()
    state.heroes[hero.id] = hero
    state.towns[town.id] = town
    state.factions["liangshan"] = Faction(
        id="liangshan", name_ko="양산박", leader_id="song_jiang"
    )
    return state


def make_ui() -> MagicMock:
    ui = MagicMock()
    ui.console = MagicMock()
    return ui


# ── _do_admin ────────────────────────────────────────────────────────────────

class TestDoAdmin:
    def _call(self, hero: Hero, state: GameState) -> None:
        from game.turn_manager import TurnManager
        tm = TurnManager(state)
        tm._do_admin(hero, make_ui())

    def test_admin_level_increases(self):
        hero = make_hero(intelligence=8)
        town = make_town(admin_level=3)
        state = make_state(hero, town)
        self._call(hero, state)
        assert state.towns["liangshan"].admin_level == 5  # gain = max(1, 8//4) = 2

    def test_higher_intelligence_gives_bigger_gain(self):
        hero_smart = make_hero(intelligence=10)
        hero_dumb  = make_hero(intelligence=4)
        town_smart = make_town(admin_level=3)
        town_dumb  = make_town(admin_level=3)
        make_state(hero_smart, town_smart)
        make_state(hero_dumb, town_dumb)

        state_s = make_state(hero_smart, town_smart)
        state_d = make_state(hero_dumb, town_dumb)

        from game.turn_manager import TurnManager
        TurnManager(state_s)._do_admin(hero_smart, make_ui())
        TurnManager(state_d)._do_admin(hero_dumb, make_ui())

        assert state_s.towns["liangshan"].admin_level > state_d.towns["liangshan"].admin_level

    def test_admin_level_capped_at_10(self):
        hero = make_hero(intelligence=10)
        town = make_town(admin_level=9)
        state = make_state(hero, town)
        self._call(hero, state)
        assert state.towns["liangshan"].admin_level == 10

    def test_admin_already_maxed_no_change(self):
        hero = make_hero(intelligence=10)
        town = make_town(admin_level=10)
        state = make_state(hero, town)
        # Should show a message but not raise and not increase beyond 10
        self._call(hero, state)
        assert state.towns["liangshan"].admin_level == 10

    def test_wrong_faction_does_nothing(self):
        """Admin action on an enemy town should refuse and leave admin_level unchanged."""
        hero = make_hero(faction="liangshan")
        town = make_town(admin_level=3, faction="imperial")
        state = make_state(hero, town)
        self._call(hero, state)
        assert state.towns["liangshan"].admin_level == 3

    def test_event_logged(self):
        hero = make_hero(intelligence=8)
        town = make_town(admin_level=3)
        state = make_state(hero, town)
        self._call(hero, state)
        assert len(state.events) == 1
        assert "내정" in state.events[0].message


# ── player_turn dispatch ─────────────────────────────────────────────────────

class TestPlayerTurnDispatch:
    def test_admin_action_reduces_ap(self):
        hero = make_hero()
        hero.action_points = 2
        town = make_town()
        state = make_state(hero, town)

        ui = make_ui()
        # First call returns "admin", second returns "end"
        ui.choose_action.side_effect = ["admin", "end"]

        from game.turn_manager import TurnManager
        TurnManager(state).player_turn(hero, ui)

        assert hero.action_points == 0  # 2 - 1 (admin) - 1 would not happen; end sets to 0

    def test_end_action_zeroes_ap(self):
        hero = make_hero()
        hero.action_points = 3
        town = make_town()
        state = make_state(hero, town)

        ui = make_ui()
        ui.choose_action.return_value = "end"

        from game.turn_manager import TurnManager
        TurnManager(state).player_turn(hero, ui)

        assert hero.action_points == 0

    def test_map_action_does_not_cost_ap(self):
        hero = make_hero()
        hero.action_points = 1
        town = make_town()
        state = make_state(hero, town)

        ui = make_ui()
        # map costs 0 AP, then end to stop the loop
        ui.choose_action.side_effect = ["map", "end"]

        from game.turn_manager import TurnManager
        TurnManager(state).player_turn(hero, ui)

        ui.show_map.assert_called_once()
        assert hero.action_points == 0  # only "end" consumed (and zeroed) it
