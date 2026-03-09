"""Combat manager — siege battles, field battles, and Rich battle visualization."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from models.army import Army, ArmyStatus, UnitType
from models.hero import Hero
from models.town import Town

if TYPE_CHECKING:
    from models.game_state import GameState


console = Console()


# ──────────────────────────────────────────────────────────────────────────────
# Result dataclasses
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class BattleResult:
    winner: str                  # faction id
    attacker_losses: int
    defender_losses: int
    wall_damage: int = 0
    turns_fought: int = 1
    narrative: list[str] = None   # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.narrative is None:
            self.narrative = []


# ──────────────────────────────────────────────────────────────────────────────
# Rendering helpers
# ──────────────────────────────────────────────────────────────────────────────

_UNIT_ICON = {
    UnitType.INFANTRY: "⚔️ 보병",
    UnitType.CAVALRY:  "🐴 기병",
    UnitType.ARCHER:   "🏹 궁병",
    UnitType.NAVY:     "⚓ 수군",
}

_MORALE_COLOR = {
    range(0,  30): "bold red",
    range(30, 60): "yellow",
    range(60, 80): "green",
    range(80, 101): "bold green",
}


def _morale_color(morale: int) -> str:
    for r, color in _MORALE_COLOR.items():
        if morale in r:
            return color
    return "white"


def _hp_bar(current: int, maximum: int, width: int = 20, color: str = "green") -> str:
    if maximum <= 0:
        return "[grey50]" + "░" * width + "[/]"
    filled = int(width * current / maximum)
    bar = "█" * filled + "░" * (width - filled)
    pct = int(100 * current / maximum)
    return f"[{color}]{bar}[/] {pct:3d}%"


def _army_panel(army: Army, title: str, style: str = "blue") -> Panel:
    icon = _UNIT_ICON.get(army.unit_type, "⚔️")
    mc = _morale_color(army.morale)
    content = (
        f"[bold]{army.name}[/]  {icon}\n"
        f"병력: {_hp_bar(army.troops, army.max_troops, 18, 'cyan')}  {army.troops:,}/{army.max_troops:,}\n"
        f"사기: [{mc}]{_hp_bar(army.morale, 100, 18, mc)}  {army.morale}[/{mc}]\n"
        f"전투력: [bold yellow]{army.combat_power:.0f}[/]"
    )
    if army.catapults or army.siege_towers or army.battering_rams:
        content += (
            f"\n[dim]투석기:{army.catapults}  운제:{army.siege_towers}  충차:{army.battering_rams}[/]"
        )
    return Panel(content, title=f"[bold]{title}[/]", style=style, padding=(0, 1))


def _wall_panel(town: Town) -> Panel:
    color = "green" if town.wall_integrity() > 0.5 else ("yellow" if town.wall_integrity() > 0.2 else "red")
    bar = _hp_bar(town.wall_hp, town.max_wall_hp, 24, color)
    lines = []
    integrity = town.wall_integrity()
    if integrity >= 0.9:
        lines = ["████████████████████"]
        wall_color = "bold white"
    elif integrity >= 0.6:
        lines = ["████▓▓▓▓████▓▓▓▓████"]
        wall_color = "bold yellow"
    elif integrity >= 0.3:
        lines = ["██░░▓▓░░██░░▓▓░░██░░"]
        wall_color = "yellow"
    else:
        lines = ["░░░░▒▒░░░░▒▒░░░░▒▒░░"]
        wall_color = "red"
    content = (
        f"  [{wall_color}]{lines[0]}[/{wall_color}]\n"
        f"  [{wall_color}]{'  🏯  ' + town.name_ko + '  🏯':^20}[/{wall_color}]\n"
        f"  [{wall_color}]{lines[0]}[/{wall_color}]\n\n"
        f"성벽 내구도: {bar}  {town.wall_hp}/{town.max_wall_hp}"
    )
    return Panel(content, title="[bold white]성벽[/bold white]", style="white", padding=(0, 1))


def _field_map(attacker: Army, defender: Army) -> Panel:
    a_icon = "🔴" if attacker.troops > 0 else "💀"
    d_icon = "🔵" if defender.troops > 0 else "💀"
    field = (
        "  ┌──────────────────────────────────────┐\n"
        f"  │  {a_icon} {attacker.name[:12]:<12}   VS   {defender.name[:12]:<12} {d_icon}  │\n"
        "  │                                      │\n"
        f"  │   ▶▶▶ [{_morale_color(attacker.morale)}]{attacker.troops:>5,}명[/]              "
        f"[{_morale_color(defender.morale)}]{defender.troops:>5,}명[/] ◀◀◀   │\n"
        "  └──────────────────────────────────────┘"
    )
    return Panel(field, title="[bold green]야전 전장[/]", style="green", padding=(0, 0))


# ──────────────────────────────────────────────────────────────────────────────
# CombatManager
# ──────────────────────────────────────────────────────────────────────────────

class CombatManager:
    """Handles army-level battles with Rich terminal visualization."""

    def __init__(self, state: "GameState") -> None:
        self.state = state

    # ------------------------------------------------------------------ siege

    def siege_battle(
        self,
        attacker: Army,
        defender: Army,
        town: Town,
        attacker_general: Optional[Hero] = None,
        defender_general: Optional[Hero] = None,
    ) -> BattleResult:
        """
        Multi-phase siege: bombardment → assault → hand-to-hand.
        Displays Rich ASCII art each phase.
        """
        narrative: list[str] = []
        total_att_loss = 0
        total_def_loss = 0
        total_wall_dmg = 0
        phase_num = 0

        console.clear()
        console.print(f"[bold red]{attacker.name} -> {town.name_ko}[/]")
        console.print()

        # ── Phase 1: Bombardment (투석기 포격) ──────────────────────────────
        if attacker.catapults > 0 or attacker.siege_towers > 0:
            phase_num += 1
            console.print(f"[bold yellow]【제{phase_num}단계】 포격 & 공성 준비[/]")
            console.print(Columns([_army_panel(attacker, "공격군", "red"), _wall_panel(town), _army_panel(defender, "수비군", "blue")]))

            wall_dmg = int(attacker.siege_power * random.uniform(0.6, 1.4) / 10)
            wall_dmg = max(5, min(wall_dmg, town.wall_hp // 2))
            town.wall_hp = max(0, town.wall_hp - wall_dmg)
            total_wall_dmg += wall_dmg

            msg = f"  투석기 {attacker.catapults}문이 불을 뿜는다!  성벽 -{wall_dmg} HP"
            narrative.append(msg)
            console.print(f"[bold red]{msg}[/]")
            time.sleep(1.2)

        # ── Phase 2: Main Assault (전면 돌격) ─────────────────────────────
        max_rounds = 5
        for rnd in range(1, max_rounds + 1):
            if not attacker.is_active() or not defender.is_active():
                break

            phase_num += 1
            

            console.print(f"[bold white]【제{phase_num}단계】 {rnd}번째 공격[/]")
            console.print(Columns([_army_panel(attacker, "공격군 ⚔️", "red"), _army_panel(defender, f"수비군 🛡 ({town.name_ko})", "blue")]))

            # Wall bonus for defender
            wall_bonus = 1.0 + town.wall_integrity() * 0.5

            att_power = attacker.combat_power * random.uniform(0.8, 1.2)
            def_power = defender.combat_power * wall_bonus * random.uniform(0.8, 1.2)

            # Hero bonus
            if attacker_general:
                att_power *= 1.0 + attacker_general.strength * 0.05
            if defender_general:
                def_power *= 1.0 + defender_general.strength * 0.05

            att_loss = max(10, int(def_power * random.uniform(0.05, 0.12)))
            def_loss = max(5, int(att_power * random.uniform(0.04, 0.10)))

            attacker.apply_casualties(att_loss)
            defender.apply_casualties(def_loss)
            attacker.suffer_morale_loss(random.randint(2, 6))
            defender.suffer_morale_loss(random.randint(1, 4))
            total_att_loss += att_loss
            total_def_loss += def_loss

            round_msg = (
                f"  공격군 -{att_loss}명 (사기 {attacker.morale}) / "
                f"수비군 -{def_loss}명 (사기 {defender.morale}) / "
                f"성벽 {town.wall_hp}HP"
            )
            narrative.append(round_msg)
            console.print(f"[yellow]{round_msg}[/]")
            time.sleep(0.2)

        # ── Determine winner ────────────────────────────────────────────────
        att_broken = not attacker.is_active()
        def_broken = not defender.is_active()

        if def_broken and not att_broken:
            winner = attacker.faction_id
            town.controlled_by_faction = attacker.faction_id
            town.garrison_strength = max(1, attacker.troops // 1000)
            result_msg = f"[bold green]✅ 공성전 승리! {attacker.name}이(가) {town.name_ko}을(를) 점령했다![/]"
        elif att_broken:
            winner = defender.faction_id
            result_msg = f"[bold red]❌ 공성전 실패! {attacker.name}이(가) 후퇴했다.[/]"
        else:
            winner = defender.faction_id  # defender holds by default if inconclusive
            result_msg = f"[bold yellow]⚔️  공성전 교착 — {defender.name}이(가) 성을 지켰다.[/]"

        console.print()
        console.print(Panel(result_msg, style="bold", padding=(1, 4)))
        console.print()

        return BattleResult(
            winner=winner,
            attacker_losses=total_att_loss,
            defender_losses=total_def_loss,
            wall_damage=total_wall_dmg,
            turns_fought=phase_num,
            narrative=narrative,
        )

    # ------------------------------------------------------------------ field

    def field_battle(
        self,
        attacker: Army,
        defender: Army,
        attacker_general: Optional[Hero] = None,
        defender_general: Optional[Hero] = None,
        allow_flanking: bool = True,
    ) -> BattleResult:
        """
        Open-field battle with flanking maneuvoers and cavalry charges.
        Displays Rich ASCII art each round.
        """
        narrative: list[str] = []
        total_att_loss = 0
        total_def_loss = 0

        console.print()
        console.rule(f"[bold green]⚔️  야전 개시: {attacker.name} vs {defender.name}  ⚔️[/]")
        console.print()

        for rnd in range(1, 7):
            if not attacker.is_active() or not defender.is_active():
                break

            console.print(f"[bold white]━━━ {rnd}라운드 ━━━[/]")
            console.print(_field_map(attacker, defender))

            att_power = attacker.combat_power * random.uniform(0.85, 1.15)
            def_power = defender.combat_power * random.uniform(0.85, 1.15)

            # Hero general bonuses
            if attacker_general:
                att_power *= 1.0 + attacker_general.strength * 0.04 + attacker_general.intelligence * 0.02
            if defender_general:
                def_power *= 1.0 + defender_general.strength * 0.04 + defender_general.intelligence * 0.02

            # Cavalry charge bonus (first round)
            cavalry_msg = ""
            if rnd == 1 and attacker.unit_type == UnitType.CAVALRY:
                att_power *= 1.5
                cavalry_msg = f"  🐴 [bold yellow]{attacker.name} 기병 돌격! 전투력 +50%[/]"
                narrative.append(cavalry_msg)
                console.print(cavalry_msg)
            elif rnd == 1 and defender.unit_type == UnitType.CAVALRY:
                def_power *= 1.5
                cavalry_msg = f"  🐴 [bold cyan]{defender.name} 기병 반격 돌격! 전투력 +50%[/]"
                narrative.append(cavalry_msg)
                console.print(cavalry_msg)

            # Flanking (rounds 2-3 only if attacker is cavalry or ranger-type)
            flank_msg = ""
            if allow_flanking and rnd in (2, 3) and attacker.unit_type == UnitType.CAVALRY:
                flank_chance = 0.35
                if random.random() < flank_chance:
                    flank_bonus = random.uniform(0.2, 0.5)
                    att_power *= 1.0 + flank_bonus
                    flank_msg = f"  ⚡ [bold magenta]측면 기습 성공! 추가 피해 +{int(flank_bonus*100)}%[/]"
                    narrative.append(flank_msg)
                    console.print(flank_msg)

            att_loss = max(5, int(def_power * random.uniform(0.04, 0.10)))
            def_loss = max(5, int(att_power * random.uniform(0.04, 0.10)))

            # Archer advantage vs cavalry
            if defender.unit_type == UnitType.ARCHER and attacker.unit_type == UnitType.CAVALRY:
                att_loss = int(att_loss * 1.3)
                console.print(f"  🏹 [yellow]{defender.name} 궁병이 기병에 집중 사격![/]")

            attacker.apply_casualties(att_loss)
            defender.apply_casualties(def_loss)
            attacker.suffer_morale_loss(random.randint(1, 5))
            defender.suffer_morale_loss(random.randint(1, 5))
            total_att_loss += att_loss
            total_def_loss += def_loss

            rnd_msg = (
                f"  {attacker.name} -{att_loss}명 [{attacker.morale}%사기] | "
                f"{defender.name} -{def_loss}명 [{defender.morale}%사기]"
            )
            narrative.append(rnd_msg)
            console.print(f"[dim]{rnd_msg}[/]")
            time.sleep(0.2)

        # ── Result ──────────────────────────────────────────────────────────
        att_broken = not attacker.is_active()
        def_broken = not defender.is_active()

        if def_broken and not att_broken:
            winner = attacker.faction_id
            result_msg = f"[bold green]✅ 야전 승리! {attacker.name}이(가) 적을 격파했다![/]"
        elif att_broken and not def_broken:
            winner = defender.faction_id
            result_msg = f"[bold red]❌ 야전 패배! {attacker.name}이(가) 도주했다![/]"
        elif att_broken and def_broken:
            # Both routed — attacker loses by default
            winner = defender.faction_id
            result_msg = "[bold yellow]⚔️  양군 모두 괴멸 — 전투 무승부[/]"
        else:
            # Inconclusive: higher remaining troops wins
            if attacker.troops >= defender.troops:
                winner = attacker.faction_id
                result_msg = f"[bold green]✅ 야전 판정승! {attacker.name} 우세[/]"
            else:
                winner = defender.faction_id
                result_msg = f"[bold cyan]🛡  야전 방어 성공! {defender.name} 진지 사수[/]"

        # Final state display
        console.print()
        console.print(Columns([
            _army_panel(attacker, f"{'승리' if winner == attacker.faction_id else '패배'} — {attacker.name}", "green" if winner == attacker.faction_id else "red"),
            _army_panel(defender, f"{'승리' if winner == defender.faction_id else '패배'} — {defender.name}", "green" if winner == defender.faction_id else "red"),
        ]))
        console.print(Panel(result_msg, style="bold", padding=(1, 4)))
        console.print()

        return BattleResult(
            winner=winner,
            attacker_losses=total_att_loss,
            defender_losses=total_def_loss,
            turns_fought=6,
            narrative=narrative,
        )

    # ------------------------------------------------------------------ hero duel

    def hero_duel(self, hero_a: Hero, hero_b: Hero) -> Hero:
        """
        Dramatic one-on-one duel between two generals.
        Returns the victor.
        """
        console.print()
        console.rule(f"[bold magenta]⚔️  장수 일기토: {hero_a.name_ko} vs {hero_b.name_ko}  ⚔️[/]")

        hp_a = hero_a.hp
        hp_b = hero_b.hp

        for rnd in range(1, 10):
            if hp_a <= 0 or hp_b <= 0:
                break

            # Build duel table
            table = Table(box=box.SIMPLE_HEAVY, show_header=False)
            table.add_column(width=30, justify="right")
            table.add_column(width=6, justify="center")
            table.add_column(width=30, justify="left")

            table.add_row(
                Text(f"{hero_a.name_ko} ({hero_a.nickname})", style="bold red"),
                Text(f"  VS  ", style="bold white"),
                Text(f"{hero_b.name_ko} ({hero_b.nickname})", style="bold blue"),
            )
            table.add_row(
                Text(f"HP: {_hp_bar(hp_a, hero_a.max_hp, 15, 'red')}"),
                Text(""),
                Text(f"HP: {_hp_bar(hp_b, hero_b.max_hp, 15, 'blue')}"),
            )
            console.print(table)

            dmg_a = max(1, int(hero_a.strength * random.uniform(0.8, 1.2)) - hero_b.agility // 3)
            dmg_b = max(1, int(hero_b.strength * random.uniform(0.8, 1.2)) - hero_a.agility // 3)

            # Skill-based critical hit
            if hero_a.intelligence > hero_b.intelligence and random.random() < 0.2:
                dmg_a = int(dmg_a * 1.5)
                console.print(f"  ✨ [bold yellow]{hero_a.name_ko} 비기 발동! 피해 ×1.5[/]")

            hp_a -= dmg_b
            hp_b -= dmg_a
            console.print(f"  {hero_a.name_ko} ↦ -{dmg_a}  |  {hero_b.name_ko} ↦ -{dmg_b}")
            time.sleep(0.25)

        victor = hero_a if hp_a > hp_b else hero_b
        loser = hero_b if hp_a > hp_b else hero_a

        # Apply damage to actual Hero models
        hero_a.hp = max(1, hp_a)
        hero_b.hp = max(1, hp_b)
        if hp_a <= 0:
            hero_a.hp = max(1, hero_a.hp // 2)
        if hp_b <= 0:
            hero_b.hp = max(1, hero_b.hp // 2)

        console.print(Panel(
            f"[bold yellow]🏆 {victor.name_ko}의 승리!  {loser.name_ko} 후퇴.[/]",
            style="bold",
            padding=(1, 4),
        ))
        return victor

    # ------------------------------------------------------------------ quick combat (legacy hero vs enemies)

    def resolve_combat(self, attacker: Hero, defense: int) -> bool:
        """
        Simple hero vs. garrison combat (legacy interface for TurnManager).
        Returns True if attacker wins.
        """
        att = attacker.strength + random.randint(1, 6)
        defs = defense + random.randint(1, 6)
        won = att > defs
        console.print(
            f"  [{'green' if won else 'red'}]{'✅ 전투 승리' if won else '❌ 전투 패배'}[/]  "
            f"({attacker.name_ko} 전투력 {att}  vs  수비군 {defs})"
        )
        if won:
            attacker.hp = max(1, attacker.hp - random.randint(5, 15))
        else:
            attacker.hp = max(1, attacker.hp - random.randint(20, 40))
        return won

    def resolve_siege(self, hero: Hero, town: Town) -> BattleResult:
        """
        AI-facing siege wrapper: hero + town 으로 Army를 임시 생성해
        siege_battle를 호출하고 도시 점령 여부를 갱신한다.
        """
        attacker = Army(
            id=f"army_{hero.id}",
            name=f"{hero.name_ko}의 군대",
            faction_id=hero.faction_id,
            general_id=hero.id,
            troops=max(1, hero.current_army),
            max_troops=max(1, hero.current_army),
            morale=80,
        )
        garrison = max(100, town.garrison_strength * 100)
        defender = Army(
            id=f"garrison_{town.id}",
            name=f"{town.name_ko} 수비군",
            faction_id=town.controlled_by_faction or "neutral",
            troops=garrison,
            max_troops=garrison,
            morale=70,
        )
        result = self.siege_battle(attacker, defender, town,
                                   attacker_general=hero)
        # 승리 시 영웅 병력 갱신
        hero.current_army = max(0, attacker.troops)
        return result