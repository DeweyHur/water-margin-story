"""Tests for Pydantic models."""
import pytest
from pydantic import ValidationError

from models.town import Town
from models.hero import Hero, HeroClass
from models.faction import Faction
from models.game_state import GameState, GamePhase


# ── Town ────────────────────────────────────────────────────────────────────

class TestTown:
    def _make(self, **kwargs) -> Town:
        defaults = dict(id="test", name_ko="테스트", name_zh="測試", town_type="village")
        return Town(**{**defaults, **kwargs})

    def test_default_admin_level(self):
        t = self._make()
        assert t.admin_level == 3

    def test_custom_admin_level(self):
        t = self._make(admin_level=7)
        assert t.admin_level == 7

    def test_admin_level_min_bound(self):
        with pytest.raises(ValidationError):
            self._make(admin_level=0)

    def test_admin_level_max_bound(self):
        with pytest.raises(ValidationError):
            self._make(admin_level=11)

    def test_wall_integrity_full(self):
        t = self._make(wall_hp=100, max_wall_hp=100)
        assert t.wall_integrity() == 1.0

    def test_wall_integrity_partial(self):
        t = self._make(wall_hp=50, max_wall_hp=100)
        assert t.wall_integrity() == 0.5

    def test_repair_walls_clamps_to_max(self):
        t = self._make(wall_hp=90, max_wall_hp=100)
        t.repair_walls(50)
        assert t.wall_hp == 100

    def test_is_fortified_fortress(self):
        assert self._make(town_type="fortress").is_fortified()

    def test_is_fortified_metropolis(self):
        assert self._make(town_type="metropolis").is_fortified()

    def test_village_not_fortified(self):
        assert not self._make(town_type="village").is_fortified()


# ── Hero ────────────────────────────────────────────────────────────────────

class TestHero:
    def _make(self, **kwargs) -> Hero:
        defaults = dict(
            id="wu_yong", name_ko="오용", name_zh="吳用",
            nickname="지다성", hero_class=HeroClass.STRATEGIST,
            strength=3, intelligence=9, agility=6,
        )
        return Hero(**{**defaults, **kwargs})

    def test_default_faction_is_neutral(self):
        assert self._make().faction_id == "neutral"

    def test_hero_alive(self):
        assert self._make().is_alive()

    def test_hero_dead_at_zero_hp(self):
        h = self._make()
        h.hp = 0
        assert not h.is_alive()

    def test_restore_action_points(self):
        h = self._make()
        h.action_points = 0
        h.restore_action_points()
        assert h.action_points == 3

    def test_current_army_default(self):
        assert self._make().current_army == 0

    def test_current_army_custom(self):
        h = self._make(current_army=5000)
        assert h.current_army == 5000


# ── GameState ────────────────────────────────────────────────────────────────

class TestGameState:
    def test_initial_phase(self):
        assert GameState().phase == GamePhase.SETUP

    def test_is_over_false_initially(self):
        assert not GameState().is_over()

    def test_max_turns_default(self):
        assert GameState().max_turns == 30
