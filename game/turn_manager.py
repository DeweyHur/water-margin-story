"""Turn manager — handles player input and AI decision-making per hero turn."""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

from models import GameState, Hero, GameEvent, EventType
from models.army import Army, UnitType, ArmyStatus
from game.combat_manager import CombatManager

if TYPE_CHECKING:
    from ui.terminal_ui import TerminalUI


class TurnManager:
    def __init__(self, state: GameState) -> None:
        self.state = state
        self.combat_manager = CombatManager(state)

    # ------------------------------------------------------------------
    # Player turn
    # ------------------------------------------------------------------

    def player_turn(self, hero: Hero, ui: "TerminalUI") -> None:
        while hero.action_points > 0:
            action = ui.choose_action(hero, self.state)
            if action == "move":
                self._do_move_player(hero, ui)
            elif action == "investigate":
                self._do_investigate(hero)
                hero.action_points -= 1
            elif action == "recruit":
                self._do_recruit(hero, ui)
                hero.action_points -= 1
            elif action == "siege":
                self._do_siege(hero, ui)
                hero.action_points -= 2
            elif action == "rest":
                self._do_rest(hero)
                hero.action_points -= 1
            elif action == "map":
                ui.show_map(self.state)   # AP 소모 없음
            elif action == "end":
                hero.action_points = 0
                break

    def _do_move_player(self, hero: Hero, ui: "TerminalUI") -> None:
        current_town = self.state.towns.get(hero.current_town)
        if not current_town or not current_town.adjacent:
            ui.show_message("이동할 수 있는 곳이 없습니다.")
            return
        dest_id = ui.choose_destination(hero, current_town, self.state)
        if dest_id:
            hero.current_town = dest_id
            hero.action_points -= hero.move_cost()
            ui.show_message(
                f"[green]{hero.name_ko}이(가) {self.state.towns[dest_id].name_ko}(으)로 이동했다.[/]"
            )

    def _do_recruit(self, hero: Hero, ui: "TerminalUI") -> None:
        town = self.state.towns[hero.current_town]
        faction = self.state.factions.get(hero.faction_id)
        
        if not faction:
            ui.show_message("세력이 없어 병사를 모집할 수 없습니다.")
            return

        # Cost: 10 gold per 100 soldiers
        recruit_count = hero.leadership * 100
        cost = (recruit_count // 100) * 10
        
        if faction.gold >= cost:
            faction.gold -= cost
            hero.current_army += recruit_count
            ui.show_message(f"[yellow]{town.name_ko}에서 병사 {recruit_count}명을 모집했습니다. (금전 {cost} 소모)[/]")
        else:
            ui.show_message("[red]금전이 부족하여 병사를 모집할 수 없습니다.[/]")

    def _do_siege(self, hero: Hero, ui: "TerminalUI") -> None:
        town = self.state.towns[hero.current_town]
        if town.controlled_by_faction == hero.faction_id:
            ui.show_message("이미 아군 세력이 점령한 지역입니다.")
            return

        # Build temporary attacker army from hero's current_army count
        troop_count = max(500, getattr(hero, "current_army", 0) or 1000)
        attacker = Army(
            id=f"att_{hero.id}",
            name=f"{hero.name_ko}군",
            faction_id=hero.faction_id,
            general_id=hero.id,
            unit_type=UnitType.INFANTRY,
            troops=troop_count,
            max_troops=troop_count,
            morale=80,
            training=hero.leadership if hasattr(hero, "leadership") else 5,
            equipment=hero.strength,
            catapults=max(0, troop_count // 500),
            siege_towers=max(0, troop_count // 1000),
        )
        # Defender army from town garrison
        def_count = max(300, town.garrison_strength * 200)
        defender = Army(
            id=f"def_{town.id}",
            name=f"{town.name_ko} 수비군",
            faction_id=town.controlled_by_faction or "imperial",
            unit_type=UnitType.INFANTRY,
            troops=def_count,
            max_troops=def_count,
            morale=70 + town.defense_level * 3,
            training=town.defense_level,
            equipment=town.defense_level,
            status=ArmyStatus.GARRISONED,
            location=town.id,
        )

        result = self.combat_manager.siege_battle(attacker, defender, town, attacker_general=hero)

        won = result.winner == hero.faction_id
        if won:
            hero.current_army = attacker.troops
            event = GameEvent(
                type=EventType.COMBAT,
                actor_id=hero.id,
                target_id=town.id,
                message=f"{hero.name_ko}이(가) {town.name_ko} 공성전에서 승리하여 점령했습니다.",
            )
        else:
            ui.show_message(f"[bold red]패배... {town.name_ko} 공성에 실패했습니다.[/]")
            hero.hp = max(1, hero.hp - 20)
            hero.current_army = attacker.troops
            event = GameEvent(
                type=EventType.COMBAT,
                actor_id=hero.id,
                target_id=town.id,
                message=f"{hero.name_ko}이(가) {town.name_ko} 공성전에서 패배했습니다.",
            )
        self.state.log_event(event)

    def _do_investigate(self, hero: Hero) -> None:
        town = self.state.towns.get(hero.current_town)
        if not town:
            return
        clue_gain = 1 + (hero.intelligence - 5) // 3
        town.clue_level = min(5, town.clue_level + clue_gain)

        event = GameEvent(
            type=EventType.INVESTIGATION,
            actor_id=hero.id,
            target_id=hero.current_town,
            message=(
                f"{hero.name_ko}이(가) {town.name_ko}에서 정보를 수집했다. "
                f"단서 수준: {town.clue_level}/5"
            ),
        )
        self.state.log_event(event)

    def _do_rest(self, hero: Hero) -> None:
        heal = 20
        hero.hp = min(hero.max_hp, hero.hp + heal)
        event = GameEvent(
            type=EventType.MOVEMENT,
            actor_id=hero.id,
            message=f"{hero.name_ko}이(가) 휴식을 취해 {heal} HP를 회복했다.",
        )
        self.state.log_event(event)

    # ------------------------------------------------------------------
    # AI turn
    # ------------------------------------------------------------------

    def ai_turn(self, hero: Hero) -> None:
        """AI hero turn: Simple heuristic for strategy."""
        while hero.action_points > 0:
            town = self.state.towns[hero.current_town]
            
            # 1. If low HP, rest
            if hero.hp < 30:
                self._do_rest(hero)
                hero.action_points -= 1
                continue
                
            # 2. If in enemy town and has army, siege
            if town.controlled_by_faction != hero.faction_id and hero.current_army > 500:
                # Use internal logic for AI siege
                self.combat_manager.resolve_siege(hero, town)
                hero.action_points -= 2
                continue

            # 3. If in friendly town and low army, recruit
            if town.controlled_by_faction == hero.faction_id and hero.current_army < 1000:
                faction = self.state.factions.get(hero.faction_id)
                if faction and faction.gold > 100:
                    recruit_count = hero.leadership * 100
                    faction.gold -= (recruit_count // 100) * 10
                    hero.current_army += recruit_count
                hero.action_points -= 1
                continue

            # 4. Otherwise, move to adjacent town (randomly)
            if town.adjacent:
                dest_id = random.choice(town.adjacent)
                hero.current_town = dest_id
                hero.action_points -= 1
            else:
                hero.action_points = 0
