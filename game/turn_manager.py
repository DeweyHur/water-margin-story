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
                self._do_investigate(hero, ui)
                hero.action_points -= 1
            elif action == "admin":
                self._do_admin(hero, ui)
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

        old_faction = town.controlled_by_faction
        old_faction = town.controlled_by_faction
        ui.show_combat_preview(hero.current_town, town.id, self.state)
        old_faction = town.controlled_by_faction
        ui.show_combat_preview(hero.current_town, town.id, self.state)
        result = self.combat_manager.siege_battle(attacker, defender, town, attacker_general=hero)

        won = result.winner == hero.faction_id
        if won:
            town.controlled_by_faction = hero.faction_id
            ui.show_faction_change_animation(town.id, old_faction, hero.faction_id, self.state)
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

    def _do_investigate(self, hero: Hero, ui: "TerminalUI") -> None:
        import random as _random
        from rich.panel import Panel
        from rich.table import Table
        from rich import box

        town = self.state.towns.get(hero.current_town)
        if not town:
            return

        clue_gain = max(1, 1 + (hero.intelligence - 5) // 3)
        old_level = town.clue_level
        town.clue_level = min(5, town.clue_level + clue_gain)

        # ── 고구 위치 단서 ──────────────────────────────────────────────
        gao_qiu_intel: str | None = None
        gao_town = self.state.towns.get(self.state.gao_qiu_location)
        gao_name = gao_town.name_ko if gao_town else "?"
        # 고구가 현재 마을에 있으면 gao_qiu_presence 갱신
        if hero.current_town == self.state.gao_qiu_location:
            town.gao_qiu_presence = min(3, town.gao_qiu_presence + 1)
        # 고구 intel: 단서 수준 + 지략에 따라 다른 수준 공개
        reveal_roll = hero.intelligence + town.clue_level
        if town.gao_qiu_presence >= 3:
            gao_qiu_intel = f"[bold red]확인![/] 고구(高俅)가 이 지역에 머물고 있다."
        elif town.gao_qiu_presence == 2:
            gao_qiu_intel = f"[yellow]단서:[/] 고구의 측근이 이 지역에 있었다는 흔적이 있다."
        elif hero.current_town == self.state.gao_qiu_location and reveal_roll >= 10:
            gao_qiu_intel = f"[yellow]소문:[/] 고위 관리가 최근 이 지역을 지나갔다는 말이 돈다."
        elif hero.current_town in (self.state.towns.get(self.state.gao_qiu_location, town)).adjacent and reveal_roll >= 12:
            gao_qiu_intel = f"[dim]소문:[/] 인근 지역에서 대군의 이동이 목격됐다고 한다."

        # ── 마을 정보 ──────────────────────────────────────────────────
        faction = self.state.factions.get(town.controlled_by_faction or "")
        faction_name = faction.name_ko if faction else "미점령"
        _type_ko = {"village": "현(縣)", "fortress": "채(寨) / 요새", "metropolis": "부(府)"}
        type_ko = _type_ko.get(town.town_type, town.town_type)
        wall_pct = int(town.wall_hp / town.max_wall_hp * 100)
        defense_bar = "█" * town.defense_level + "░" * (10 - town.defense_level)

        # ── 지역 소문 풀 ───────────────────────────────────────────────
        _RUMORS_BY_FACTION: dict[str, list[str]] = {
            "imperial": [
                "관군 병사들이 최근 증원됐다는 소문이 돈다.",
                "세금 징수가 강화되어 주민들의 불만이 쌓이고 있다.",
                "태위(太尉) 고구의 밀서가 이 지역 관리에게 전달됐다고 한다.",
                "최근 관군 장교가 교체됐다. 새 지휘관이 엄격하다는 평이다.",
                "포두(捕頭)들이 양산박 첩자를 색출하고 있다.",
            ],
            "liangshan": [
                "양산박 사람들이 주민들에게 식량을 나눠줬다는 이야기가 있다.",
                "이 지역 산채에서 훈련 소리가 들린다.",
                "양산박으로 도망친 젊은이들이 는다.",
                "호걸들이 인근에서 관군 수송대를 습격했다 한다.",
            ],
            "erlongshan": [
                "승려 복장을 한 거한이 마을을 지나갔다는 말이 있다.",
                "이룡산의 도적이 인근 상인을 습격했다.",
            ],
            "qingfeng": [
                "청풍채 병사들이 식량 징발을 나왔다는 소문이 있다.",
            ],
            "jin": [
                "금나라 상인들이 국경을 넘어 들어왔다.",
                "북방에서 금나라 기병이 보였다는 피난민이 있다.",
            ],
            "liao": [
                "요나라 돌격대가 안문관 근처에 나타났다는 소문이 있다.",
            ],
        }
        _GENERIC_RUMORS = [
            "주민들이 수군거린다. '천하가 어지럽다'고.",
            "길손들 사이에 영웅을 기다린다는 말이 돈다.",
            "관리들이 뇌물을 요구하며 행인을 괴롭히고 있다.",
            "최근 흉작으로 유민이 늘고 있다.",
            "이 지역에서 고수(高手)가 목격됐다는 소문이 있다.",
        ]
        faction_rumors = _RUMORS_BY_FACTION.get(town.controlled_by_faction or "", [])
        all_rumors = faction_rumors + _GENERIC_RUMORS
        num_rumors = min(len(all_rumors), 1 + (town.clue_level // 2))
        rumors = _random.sample(all_rumors, num_rumors)

        # ── 설명 단락이 있으면 표시 ────────────────────────────────────
        town_desc = getattr(town, "description", None)

        # ── 출력 ──────────────────────────────────────────────────────
        bar_old = "■" * old_level + "□" * (5 - old_level)
        bar_new = "■" * town.clue_level + "□" * (5 - town.clue_level)
        clue_str = (
            f"[dim]{bar_old}[/] → [bold yellow]{bar_new}[/]  "
            f"({old_level} → [bold]{town.clue_level}[/] / 5)"
        )

        lines: list[str] = [
            f"[bold cyan]{town.name_ko}[/] [dim]({town.name_zh})[/]  {type_ko}",
            f"[dim]세력:[/]  {faction_name}   [dim]수비:[/] {defense_bar} {town.defense_level}/10",
            f"[dim]성벽:[/]  {wall_pct}%  ({town.wall_hp}/{town.max_wall_hp})",
            f"[dim]주민:[/]  {town.population:,}명   [dim]수비대:[/] {town.garrison_strength * 200:,}",
            "",
            f"[bold]단서 수준[/]  {clue_str}",
        ]
        if town_desc:
            lines += ["", f"[italic dim]{town_desc}[/]"]
        if rumors:
            lines += ["", "[bold]입수한 소문[/]"]
            for r in rumors:
                lines.append(f"  [dim]·[/] {r}")
        if gao_qiu_intel:
            lines += ["", f"[bold]고구 행방[/]  {gao_qiu_intel}"]
        elif town.clue_level < 3:
            lines += ["", "[dim]고구 행방: 단서 부족 — 더 조사해야 한다.[/]"]

        ui.console.print(Panel(
            "\n".join(lines),
            title=f"[bold yellow]조사 결과 — {hero.name_ko}[/]",
            border_style="yellow",
            padding=(1, 2),
        ))
        import questionary
        questionary.press_any_key_to_continue("[ 아무 키 ] 계속...").ask()

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

    def _do_admin(self, hero: Hero, ui: "TerminalUI") -> None:
        """Increase admin_level of current town (must be controlled by player's faction)."""
        from rich.panel import Panel

        town = self.state.towns.get(hero.current_town)
        if not town:
            return
        if town.controlled_by_faction != hero.faction_id:
            ui.show_message(
                "[red]아군 거점이 아니면 내정을 강화할 수 없습니다.[/]"
            )
            return
        if town.admin_level >= 10:
            ui.show_message(
                f"[yellow]{town.name_ko}는 이미 내정이 최고 수준(10)에 달해 있습니다.[/]"
            )
            return

        gain = max(1, hero.intelligence // 4)  # 지력이 높을수록 빠르게 올라감
        old = town.admin_level
        town.admin_level = min(10, town.admin_level + gain)

        old_income_g = int(town.tax_yield * old / 5)
        new_income_g = int(town.tax_yield * town.admin_level / 5)
        old_income_f = int(town.food_yield * old / 5)
        new_income_f = int(town.food_yield * town.admin_level / 5)

        def _bar(val: int, mx: int = 10, width: int = 10) -> str:
            filled = round(val * width / mx)
            return "[yellow]" + "█" * filled + "[/][dim]" + "░" * (width - filled) + "[/]"

        lines = [
            f"[bold cyan]{town.name_ko}[/] 내정 강화",
            "",
            f"내정 수준  {_bar(old)} {old} → [bold yellow]{_bar(town.admin_level)} {town.admin_level}[/] / 10",
            "",
            f"세금 수입  [dim]{old_income_g}[/] → [bold green]{new_income_g}[/] / 턴",
            f"식량 수입  [dim]{old_income_f}[/] → [bold green]{new_income_f}[/] / 턴",
        ]
        ui.console.print(Panel(
            "\n".join(lines),
            title=f"[bold yellow]내정 강화 — {hero.name_ko}[/]",
            border_style="yellow",
            padding=(1, 2),
        ))

        event = GameEvent(
            type=EventType.MOVEMENT,
            actor_id=hero.id,
            target_id=hero.current_town,
            message=(
                f"{hero.name_ko}이(가) {town.name_ko} 내정을 강화했다. "
                f"내정 수준: {old} → {town.admin_level}"
            ),
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
