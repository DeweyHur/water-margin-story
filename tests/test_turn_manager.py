"""Tests for TurnManager — all player and AI actions."""
import pytest
from unittest.mock import MagicMock, patch

from models.game_state import GameState
from models.hero import Hero, HeroClass
from models.town import Town
from models.faction import Faction
from game.combat_manager import BattleResult


# ── Helpers ─────────────────────────────────────────────────────────────────

def make_hero(
    hero_id: str = "wu_yong",
    intelligence: int = 8,
    strength: int = 5,
    faction: str = "liangshan",
    current_town: str = "liangshan",
    leadership: int = 5,
    current_army: int = 0,
    hp: int = 100,
) -> Hero:
    return Hero(
        id=hero_id, name_ko=hero_id, name_zh="", nickname="",
        hero_class=HeroClass.STRATEGIST,
        strength=strength, intelligence=intelligence, agility=6,
        faction_id=faction,
        current_town=current_town,
        leadership=leadership,
        current_army=current_army,
        hp=hp, max_hp=100,
    )


def make_town(
    town_id: str = "liangshan",
    admin_level: int = 3,
    faction: str = "liangshan",
    adjacent: list[str] | None = None,
    garrison_strength: int = 3,
    defense_level: int = 3,
    tax_yield: int = 200,
    food_yield: int = 150,
) -> Town:
    return Town(
        id=town_id, name_ko=town_id, town_type="fortress",
        controlled_by_faction=faction,
        tax_yield=tax_yield, food_yield=food_yield,
        admin_level=admin_level,
        adjacent=adjacent or [],
        garrison_strength=garrison_strength,
        defense_level=defense_level,
    )


def make_state(hero: Hero, *towns: Town, extra_factions: list[Faction] | None = None) -> GameState:
    state = GameState()
    state.heroes[hero.id] = hero
    for t in towns:
        state.towns[t.id] = t
    state.factions["liangshan"] = Faction(
        id="liangshan", name_ko="양산박", leader_id="song_jiang", gold=5000, food=5000
    )
    state.factions["imperial"] = Faction(
        id="imperial", name_ko="관군", leader_id="gao_qiu", gold=10000, food=10000
    )
    for f in (extra_factions or []):
        state.factions[f.id] = f
    return state


def make_ui() -> MagicMock:
    ui = MagicMock()
    ui.console = MagicMock()
    return ui


# ── _do_move_player ──────────────────────────────────────────────────────────

class TestDoMove:
    def _call(self, hero: Hero, state: GameState, dest_id: str | None) -> MagicMock:
        from game.turn_manager import TurnManager
        ui = make_ui()
        ui.choose_destination.return_value = dest_id
        TurnManager(state)._do_move_player(hero, ui)
        return ui

    def test_hero_moves_to_chosen_destination(self):
        hero = make_hero(current_town="liangshan")
        src = make_town("liangshan", adjacent=["bianjing"])
        dst = make_town("bianjing", faction="imperial")
        state = make_state(hero, src, dst)
        self._call(hero, state, "bianjing")
        assert hero.current_town == "bianjing"

    def test_move_costs_one_ap(self):
        hero = make_hero(current_town="liangshan")
        src = make_town("liangshan", adjacent=["bianjing"])
        dst = make_town("bianjing")
        state = make_state(hero, src, dst)
        hero.action_points = 3
        self._call(hero, state, "bianjing")
        assert hero.action_points == 2  # hero.move_cost() == 1

    def test_no_adjacent_towns_shows_message(self):
        hero = make_hero(current_town="liangshan")
        town = make_town("liangshan", adjacent=[])
        state = make_state(hero, town)
        ui = self._call(hero, state, None)
        ui.show_message.assert_called_once()
        assert hero.current_town == "liangshan"

    def test_cancelled_destination_does_not_move(self):
        hero = make_hero(current_town="liangshan")
        src = make_town("liangshan", adjacent=["bianjing"])
        dst = make_town("bianjing")
        state = make_state(hero, src, dst)
        self._call(hero, state, None)
        assert hero.current_town == "liangshan"

    def test_followers_move_together(self):
        leader = make_hero(hero_id="leader", current_town="liangshan")
        follower = make_hero(hero_id="follower", current_town="liangshan")
        follower.following_hero_id = "leader"
        src = make_town("liangshan", adjacent=["bianjing"])
        dst = make_town("bianjing")
        state = make_state(leader, src, dst)
        state.heroes[follower.id] = follower
        self._call(leader, state, "bianjing")
        assert leader.current_town == "bianjing"
        assert follower.current_town == "bianjing"


# ── _do_recruit ──────────────────────────────────────────────────────────────

class TestDoRecruit:
    def _call(self, hero: Hero, state: GameState) -> MagicMock:
        from game.turn_manager import TurnManager
        ui = make_ui()
        TurnManager(state)._do_recruit(hero, ui)
        return ui

    def test_sufficient_gold_increases_army(self):
        hero = make_hero(leadership=5, current_army=0)
        town = make_town()
        state = make_state(hero, town)
        state.factions["liangshan"].gold = 1000
        self._call(hero, state)
        assert hero.current_army == 500      # leadership 5 * 100
        assert state.factions["liangshan"].gold == 950  # 5 * 10 cost

    def test_insufficient_gold_shows_error(self):
        hero = make_hero(leadership=5, current_army=0)
        town = make_town()
        state = make_state(hero, town)
        state.factions["liangshan"].gold = 0
        ui = self._call(hero, state)
        assert hero.current_army == 0
        ui.show_message.assert_called_once()

    def test_no_faction_shows_error(self):
        hero = make_hero(faction="unknown_faction")
        town = make_town(faction="unknown_faction")
        state = GameState()
        state.heroes[hero.id] = hero
        state.towns[town.id] = town
        ui = make_ui()
        from game.turn_manager import TurnManager
        TurnManager(state)._do_recruit(hero, ui)
        ui.show_message.assert_called_once()
        assert hero.current_army == 0

    def test_higher_leadership_recruits_more(self):
        hero_low = make_hero(hero_id="h1", leadership=3)
        hero_high = make_hero(hero_id="h2", leadership=8)
        town = make_town()

        state_low = make_state(hero_low, town)
        state_low.factions["liangshan"].gold = 9999
        state_high = make_state(hero_high, town)
        state_high.factions["liangshan"].gold = 9999

        from game.turn_manager import TurnManager
        TurnManager(state_low)._do_recruit(hero_low, make_ui())
        TurnManager(state_high)._do_recruit(hero_high, make_ui())

        assert hero_high.current_army > hero_low.current_army


# ── _do_rally_party ─────────────────────────────────────────────────────────

class TestDoRallyParty:
    def test_rally_adds_companion_as_player_follower(self):
        leader = make_hero(hero_id="leader", current_town="liangshan", faction="liangshan")
        leader.is_player_controlled = True
        leader.player_id = "player1"
        candidate = make_hero(hero_id="candidate", current_town="liangshan", faction="liangshan")
        town = make_town("liangshan", faction="liangshan")
        state = make_state(leader, town)
        state.heroes[candidate.id] = candidate

        ui = make_ui()
        ui.choose_party_candidate.return_value = "candidate"

        from game.turn_manager import TurnManager
        ok = TurnManager(state)._do_rally_party(leader, ui)

        assert ok is True
        assert candidate.is_player_controlled is True
        assert candidate.player_id == "player1"
        assert candidate.following_hero_id == "leader"

    def test_neutral_leader_can_contact_neutral_talent(self):
        leader = make_hero(hero_id="leader", current_town="dongping", faction="neutral")
        leader.is_player_controlled = True
        leader.player_id = "player1"
        candidate = make_hero(hero_id="candidate", current_town="dongping", faction="neutral")
        town = make_town("dongping", faction="imperial")
        state = make_state(leader, town)
        state.heroes[candidate.id] = candidate

        ui = make_ui()
        ui.choose_party_candidate.return_value = "candidate"

        from game.turn_manager import TurnManager
        ok = TurnManager(state)._do_rally_party(leader, ui)

        assert ok is True
        assert candidate.is_player_controlled is True
        assert candidate.player_id == "player1"
        assert candidate.following_hero_id == "leader"


# ── _do_rest ─────────────────────────────────────────────────────────────────

class TestDoRest:
    def _call(self, hero: Hero, state: GameState) -> None:
        from game.turn_manager import TurnManager
        TurnManager(state)._do_rest(hero)

    def test_heals_20_hp(self):
        hero = make_hero(hp=50)
        state = make_state(hero, make_town())
        self._call(hero, state)
        assert hero.hp == 70

    def test_hp_clamped_to_max(self):
        hero = make_hero(hp=95)
        state = make_state(hero, make_town())
        self._call(hero, state)
        assert hero.hp == 100

    def test_full_hp_stays_at_max(self):
        hero = make_hero(hp=100)
        state = make_state(hero, make_town())
        self._call(hero, state)
        assert hero.hp == 100

    def test_event_logged(self):
        hero = make_hero(hp=50)
        state = make_state(hero, make_town())
        self._call(hero, state)
        assert len(state.events) == 1
        assert "휴식" in state.events[0].message or "회복" in state.events[0].message


# ── _do_investigate ───────────────────────────────────────────────────────────

class TestDoInvestigate:
    def _call(self, hero: Hero, state: GameState) -> None:
        from game.turn_manager import TurnManager
        ui = make_ui()
        with patch("questionary.press_any_key_to_continue") as mock_q:
            mock_q.return_value.ask.return_value = None
            TurnManager(state)._do_investigate(hero, ui)

    def test_clue_level_increases(self):
        hero = make_hero(intelligence=5)
        town = make_town(faction="imperial")
        town.clue_level = 0
        state = make_state(hero, town)
        self._call(hero, state)
        assert state.towns["liangshan"].clue_level > 0

    def test_high_intelligence_gives_bigger_clue_gain(self):
        hero_smart = make_hero(hero_id="smart", intelligence=10, current_town="liangshan")
        hero_dumb  = make_hero(hero_id="dumb",  intelligence=1,  current_town="liangshan")
        town = make_town(faction="imperial")
        town.clue_level = 0

        state_s = make_state(hero_smart, make_town(faction="imperial"))
        state_d = make_state(hero_dumb,  make_town(faction="imperial"))
        state_s.towns["liangshan"].clue_level = 0
        state_d.towns["liangshan"].clue_level = 0

        from game.turn_manager import TurnManager
        ui = make_ui()
        with patch("questionary.press_any_key_to_continue") as mq:
            mq.return_value.ask.return_value = None
            TurnManager(state_s)._do_investigate(hero_smart, ui)
        with patch("questionary.press_any_key_to_continue") as mq:
            mq.return_value.ask.return_value = None
            TurnManager(state_d)._do_investigate(hero_dumb, ui)

        assert state_s.towns["liangshan"].clue_level >= state_d.towns["liangshan"].clue_level

    def test_clue_level_capped_at_5(self):
        hero = make_hero(intelligence=10)
        town = make_town(faction="imperial")
        town.clue_level = 4
        state = make_state(hero, town)
        self._call(hero, state)
        assert state.towns["liangshan"].clue_level == 5

    def test_event_logged(self):
        hero = make_hero(intelligence=6)
        state = make_state(hero, make_town(faction="imperial"))
        self._call(hero, state)
        assert any("조사" in e.message or "단서" in e.message or "정보" in e.message
                   for e in state.events)


# ── _do_siege ────────────────────────────────────────────────────────────────

class TestDoSiege:
    def _call(self, hero: Hero, state: GameState, win: bool) -> MagicMock:
        from game.turn_manager import TurnManager
        from game.combat_manager import BattleResult
        ui = make_ui()
        result = BattleResult(
            winner=hero.faction_id if win else "imperial",
            attacker_losses=100,
            defender_losses=200,
        )
        tm = TurnManager(state)
        tm.combat_manager.siege_battle = MagicMock(return_value=result)
        tm._do_siege(hero, ui)
        return ui

    def test_own_faction_town_refuses(self):
        hero = make_hero(faction="liangshan", current_army=2000)
        town = make_town("liangshan", faction="liangshan")
        state = make_state(hero, town)
        ui = make_ui()
        from game.turn_manager import TurnManager
        TurnManager(state)._do_siege(hero, ui)
        ui.show_message.assert_called_once()
        assert state.towns["liangshan"].controlled_by_faction == "liangshan"

    def test_no_troops_refuses(self):
        hero = make_hero(faction="liangshan", current_army=0, current_town="bianjing")
        town = make_town("bianjing", faction="imperial")
        state = make_state(hero, town)
        ui = make_ui()
        from game.turn_manager import TurnManager
        TurnManager(state)._do_siege(hero, ui)
        ui.show_message.assert_called_once()
        assert state.towns["bianjing"].controlled_by_faction == "imperial"

    def test_few_troops_refuses(self):
        hero = make_hero(faction="liangshan", current_army=50, current_town="bianjing")
        town = make_town("bianjing", faction="imperial")
        state = make_state(hero, town)
        ui = make_ui()
        from game.turn_manager import TurnManager
        TurnManager(state)._do_siege(hero, ui)
        ui.show_message.assert_called_once()
        assert state.towns["bianjing"].controlled_by_faction == "imperial"

    def test_win_changes_town_faction(self):
        hero = make_hero(faction="liangshan", current_army=3000, current_town="bianjing")
        town = make_town("bianjing", faction="imperial")
        state = make_state(hero, town)
        self._call(hero, state, win=True)
        assert state.towns["bianjing"].controlled_by_faction == "liangshan"

    def test_loss_leaves_town_unchanged(self):
        hero = make_hero(faction="liangshan", current_army=500, current_town="bianjing")
        town = make_town("bianjing", faction="imperial")
        state = make_state(hero, town)
        self._call(hero, state, win=False)
        assert state.towns["bianjing"].controlled_by_faction == "imperial"

    def test_loss_reduces_hero_hp(self):
        hero = make_hero(faction="liangshan", current_army=500, current_town="bianjing", hp=80)
        town = make_town("bianjing", faction="imperial")
        state = make_state(hero, town)
        self._call(hero, state, win=False)
        assert hero.hp < 80

    def test_loss_hp_never_below_1(self):
        hero = make_hero(faction="liangshan", current_army=500, current_town="bianjing", hp=10)
        town = make_town("bianjing", faction="imperial")
        state = make_state(hero, town)
        self._call(hero, state, win=False)
        assert hero.hp >= 1

    def test_event_logged_on_win(self):
        hero = make_hero(faction="liangshan", current_army=3000, current_town="bianjing")
        town = make_town("bianjing", faction="imperial")
        state = make_state(hero, town)
        self._call(hero, state, win=True)
        assert any("공성" in e.message or "점령" in e.message for e in state.events)

    def test_event_logged_on_loss(self):
        hero = make_hero(faction="liangshan", current_army=500, current_town="bianjing")
        town = make_town("bianjing", faction="imperial")
        state = make_state(hero, town)
        self._call(hero, state, win=False)
        assert any("공성" in e.message or "패배" in e.message for e in state.events)


# ── _do_admin ────────────────────────────────────────────────────────────────

class TestDoAdmin:
    def _call(self, hero: Hero, state: GameState) -> None:
        from game.turn_manager import TurnManager
        TurnManager(state)._do_admin(hero, make_ui())

    def test_admin_level_increases(self):
        hero = make_hero(intelligence=8)
        town = make_town(admin_level=3)
        state = make_state(hero, town)
        self._call(hero, state)
        assert state.towns["liangshan"].admin_level == 5  # gain = max(1, 8//4) = 2

    def test_higher_intelligence_gives_bigger_gain(self):
        town_s = make_town(admin_level=3)
        town_d = make_town(admin_level=3)
        hero_smart = make_hero(hero_id="smart", intelligence=10)
        hero_dumb  = make_hero(hero_id="dumb",  intelligence=4)
        state_s = make_state(hero_smart, town_s)
        state_d = make_state(hero_dumb,  town_d)

        from game.turn_manager import TurnManager
        TurnManager(state_s)._do_admin(hero_smart, make_ui())
        TurnManager(state_d)._do_admin(hero_dumb,  make_ui())

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
        self._call(hero, state)
        assert state.towns["liangshan"].admin_level == 10

    def test_wrong_faction_does_nothing(self):
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


# ── AI turn ───────────────────────────────────────────────────────────────────

class TestAiTurn:
    def test_low_hp_triggers_rest(self):
        hero = make_hero(hp=20, current_town="liangshan")
        hero.action_points = 2
        town = make_town("liangshan", faction="liangshan")
        state = make_state(hero, town)
        from game.turn_manager import TurnManager
        TurnManager(state).ai_turn(hero)
        assert hero.hp > 20
        assert hero.action_points == 0

    def test_enemy_town_with_army_triggers_siege(self):
        hero = make_hero(hp=100, current_army=1000, current_town="bianjing")
        hero.action_points = 2
        town = make_town("bianjing", faction="imperial")
        state = make_state(hero, town)

        from game.turn_manager import TurnManager
        tm = TurnManager(state)
        dummy_result = BattleResult(winner="liangshan", attacker_losses=0, defender_losses=100)
        tm.combat_manager.siege_battle = MagicMock(return_value=dummy_result)
        tm.ai_turn(hero)

        assert hero.action_points == 0

    def test_friendly_town_low_army_triggers_recruit(self):
        hero = make_hero(hp=100, current_army=0, current_town="liangshan", leadership=5)
        hero.action_points = 1
        town = make_town("liangshan", faction="liangshan")
        state = make_state(hero, town)
        state.factions["liangshan"].gold = 9999

        from game.turn_manager import TurnManager
        TurnManager(state).ai_turn(hero)

        assert hero.current_army > 0

    def test_no_adjacent_exhausts_ap(self):
        hero = make_hero(hp=100, current_army=2000, current_town="liangshan")
        hero.action_points = 3
        town = make_town("liangshan", faction="liangshan", adjacent=[])
        state = make_state(hero, town)
        state.factions["liangshan"].gold = 9999
        # army >= 1000 so won't recruit; no adjacent so can't move
        hero.current_army = 5000
        from game.turn_manager import TurnManager
        TurnManager(state).ai_turn(hero)
        assert hero.action_points == 0

    def test_ai_moves_to_adjacent_when_no_action_needed(self):
        hero = make_hero(hp=100, current_army=2000, current_town="liangshan")
        hero.action_points = 1
        town = make_town("liangshan", faction="liangshan", adjacent=["bianjing"])
        dst  = make_town("bianjing", faction="liangshan")
        state = make_state(hero, town, dst)
        state.factions["liangshan"].gold = 0  # can't recruit
        hero.current_army = 5000              # army large enough, won't recruit

        from game.turn_manager import TurnManager
        TurnManager(state).ai_turn(hero)

        assert hero.current_town == "bianjing"


# ── player_turn dispatch ──────────────────────────────────────────────────────

class TestPlayerTurnDispatch:
    def _run(self, hero: Hero, state: GameState, actions: list[str]) -> MagicMock:
        from game.turn_manager import TurnManager
        ui = make_ui()
        ui.choose_action.side_effect = actions
        TurnManager(state).player_turn(hero, ui)
        return ui

    def test_move_calls_do_move(self):
        hero = make_hero(current_town="liangshan")
        town = make_town("liangshan", adjacent=["bianjing"])
        dst  = make_town("bianjing")
        state = make_state(hero, town, dst)
        hero.action_points = 1
        ui = make_ui()
        ui.choose_action.side_effect = ["move"]
        ui.choose_destination.return_value = "bianjing"
        from game.turn_manager import TurnManager
        TurnManager(state).player_turn(hero, ui)
        ui.choose_destination.assert_called_once()
        assert hero.current_town == "bianjing"

    def test_investigate_costs_1_ap(self):
        hero = make_hero()
        hero.action_points = 2
        state = make_state(hero, make_town())
        with patch("questionary.press_any_key_to_continue") as mq:
            mq.return_value.ask.return_value = None
            ui = self._run(hero, state, ["investigate", "end"])
        assert hero.action_points == 0  # 2-1 investigate, then end→0

    def test_recruit_costs_1_ap(self):
        hero = make_hero()
        hero.action_points = 2
        state = make_state(hero, make_town())
        state.factions["liangshan"].gold = 9999
        ui = self._run(hero, state, ["recruit", "end"])
        assert hero.action_points == 0

    def test_siege_costs_2_ap(self):
        hero = make_hero(current_town="bianjing", current_army=2000)
        hero.action_points = 3
        town = make_town("bianjing", faction="imperial")
        state = make_state(hero, town)
        from game.combat_manager import BattleResult
        from game.turn_manager import TurnManager
        ui = make_ui()
        ui.choose_action.side_effect = ["siege", "end"]
        tm = TurnManager(state)
        tm.combat_manager.siege_battle = MagicMock(
            return_value=BattleResult(winner="imperial", attacker_losses=100, defender_losses=0)
        )
        tm.player_turn(hero, ui)
        assert hero.action_points == 0  # 3 - 2 (siege) = 1, then end→0

    def test_rest_costs_1_ap(self):
        hero = make_hero(hp=50)
        hero.action_points = 2
        state = make_state(hero, make_town())
        ui = self._run(hero, state, ["rest", "end"])
        assert hero.action_points == 0
        assert hero.hp == 70

    def test_admin_costs_1_ap(self):
        hero = make_hero()
        hero.action_points = 2
        town = make_town()
        state = make_state(hero, town)
        ui = self._run(hero, state, ["admin", "end"])
        assert hero.action_points == 0

    def test_map_does_not_cost_ap(self):
        hero = make_hero()
        hero.action_points = 1
        state = make_state(hero, make_town())
        ui = self._run(hero, state, ["map", "end"])
        ui.show_map.assert_called_once()
        assert hero.action_points == 0

    def test_end_immediately_zeroes_ap(self):
        hero = make_hero()
        hero.action_points = 3
        state = make_state(hero, make_town())
        self._run(hero, state, ["end"])
        assert hero.action_points == 0

