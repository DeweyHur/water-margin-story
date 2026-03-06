from __future__ import annotations

from typing import Optional

import questionary
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import VSplit, Window, HSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from models.game_state import GameState
from models.hero import Hero
from models.town import Town

_STYLE = questionary.Style([
    ("selected", "fg:#ffcc00 bold"),
    ("pointer", "fg:#ff5555 bold"),
    ("highlighted", "fg:#aaffaa"),
    ("answer", "fg:#ffffff bold"),
    ("question", "fg:#aaaaff bold"),
])


def _select(message: str, choices: list[str], display: list[str] | None = None) -> str:
    """커서(↑↓) + 엔터로 선택. display가 있으면 표시용 텍스트 따로 사용."""
    if display:
        mapping = dict(zip(display, choices))
        result = questionary.select(
            message, choices=display, style=_STYLE
        ).ask()
        return mapping[result] if result is not None else choices[0]
    result = questionary.select(message, choices=choices, style=_STYLE).ask()
    return result if result is not None else choices[0]


class TerminalUI:
    """Rich + questionary 터미널 UI."""

    def __init__(self) -> None:
        self.console = Console()

    def show_title(self) -> None:
        self.console.print(Panel.fit(
            "[bold red]수호지: 북송의 황혼 (Water Margin: Strategy Simulation)[/]\n"
            "[yellow]전략 시뮬레이션 확장판[/]",
            subtitle="v2.0 Strategy Update"
        ))

    def choose_hero(self, heroes: list[Hero]) -> Hero:
        table = Table(title="영웅 선택")
        table.add_column("이름", style="bold")
        table.add_column("별명", style="magenta")
        table.add_column("세력", style="green")
        table.add_column("무력", justify="right")
        table.add_column("지력", justify="right")
        table.add_column("통솔", justify="right")
        for h in heroes:
            table.add_row(
                h.name_ko, h.nickname, h.faction_id,
                str(h.strength), str(h.intelligence), str(h.leadership)
            )
        self.console.print(table)

        display = [
            f"{h.name_ko} ({h.nickname}) — 무력:{h.strength} 지력:{h.intelligence} 통솔:{h.leadership}"
            for h in heroes
        ]
        ids = [h.id for h in heroes]
        chosen_id = _select("플레이할 영웅을 선택하세요 (↑↓ + Enter)", ids, display)
        return next(h for h in heroes if h.id == chosen_id)

    def show_turn_header(self, state: GameState) -> None:
        self.console.rule(f"[bold yellow]제 {state.turn} 턴 (남은 턴: {state.turns_remaining()})[/]")
        player_hero = next((h for h in state.heroes.values() if h.is_player_controlled), None)
        if player_hero:
            faction = state.factions.get(player_hero.faction_id)
            if faction:
                status = (
                    f"[bold]세력:[/] {faction.name_ko} | "
                    f"[bold]금전:[/] {faction.gold} | [bold]군량:[/] {faction.food} | "
                    f"[bold]명성:[/] {faction.prestige} | [bold]안정도:[/] {state.dynasty_stability}"
                )
                self.console.print(Panel(status, title="세력 현황", border_style="blue"))

    def choose_action(self, hero: Hero, state: GameState) -> str:
        town = state.towns[hero.current_town]
        self.console.print(
            f"\n[bold cyan]{hero.name_ko}[/] "
            f"(위치: {town.name_ko}, 병력: {hero.current_army},"
            f" AP: {hero.action_points})")

        choices = [
            ("move",        "이동       — 인접 지역으로 이동"),
            ("investigate", "조사       — 현재 마을 탐문"),
            ("recruit",     "모병       — 병력 충원"),
            ("siege",       "공성       — 마을 점령 시도"),
            ("rest",        "휴식       — AP 회복"),
            ("map",         "지도       — 거점 정보 확인 (AP 소모 없음)"),
            ("end",         "턴 종료    — 다음 턴으로"),
        ]
        ids = [c[0] for c in choices]
        display = [f"{c[0]:12} {c[1]}" for c in choices]
        return _select("행동을 선택하세요 (↑↓ + Enter)", ids, display)

    def choose_destination(self, hero: Hero, town: Town, state: GameState) -> Optional[str]:
        table = Table(title=f"{town.name_ko} 인접 지역")
        table.add_column("이름", style="bold")
        table.add_column("지배 세력", style="green")
        for adj_id in town.adjacent:
            adj_town = state.towns[adj_id]
            faction_name = (
                state.factions[adj_town.controlled_by_faction].name_ko
                if adj_town.controlled_by_faction else "중립"
            )
            table.add_row(adj_town.name_ko, faction_name)
        self.console.print(table)

        adj_towns = town.adjacent
        display = [
            state.towns[tid].name_ko + " (" + (
                state.factions[state.towns[tid].controlled_by_faction].name_ko
                if state.towns[tid].controlled_by_faction else "중립"
            ) + ")"
            for tid in adj_towns
        ] + ["취소"]
        ids = adj_towns + ["c"]
        chosen = _select("이동할 지역을 선택하세요 (↑↓ + Enter)", ids, display)
        return None if chosen == "c" else chosen

    def show_message(self, message: str) -> None:
        self.console.print(message)

    def show_setup_complete(self, state: GameState, hero: Hero) -> None:
        self.console.print(
            f"\n[bold green]게임 준비 완료![/] "
            f"{hero.name_ko}의 여정이 {state.towns[hero.current_town].name_ko}에서 시작됩니다."
        )

    def show_game_over(self, state: GameState) -> None:
        if state.phase == "won":
            self.console.print(Panel.fit(
                "[bold yellow]축하합니다! 천하를 평정하고 새로운 질서를 세웠습니다![/]", title="승리"
            ))
        else:
            self.console.print(Panel.fit(
                "[bold red]송나라가 멸망하고 중원이 혼란에 빠졌습니다...[/]", title="패배"
            ))

    # ------------------------------------------------------------------
    # Interactive map (prompt_toolkit full-screen cursor navigation)
    # ------------------------------------------------------------------

    def show_map(self, state: GameState) -> Optional[str]:
        """Full-screen cursor-navigable map.

        ↑↓ arrows move the cursor between towns.
        Enter selects the highlighted town and returns its id.
        Escape / q returns None (cancel).
        """
        _TYPE_ICON = {"village": "마을", "fortress": "요새", "metropolis": "대도시"}
        towns = list(state.towns.values())
        cursor = [0]
        result: list[Optional[str]] = [None]

        # ---- renderers -----------------------------------------------

        def left_text():
            lines: list[tuple[str, str]] = []
            lines.append(("bold underline", " 거점 목록\n"))
            lines.append(("", "─" * 28 + "\n"))
            for i, town in enumerate(towns):
                faction = state.factions.get(town.controlled_by_faction)
                faction_name = faction.name_ko[:4] if faction else "중립"
                if i == cursor[0]:
                    lines.append(("bold fg:ansiyellow reverse", f" ▶ {town.name_ko:<8} {faction_name}\n"))
                else:
                    lines.append(("", f"   {town.name_ko:<8} {faction_name}\n"))
            lines.append(("", "\n"))
            lines.append(("fg:ansibrightblack", " ↑↓이동  Enter선택  q취소"))
            return lines

        def right_text():
            town = towns[cursor[0]]
            faction = state.factions.get(town.controlled_by_faction)
            faction_name = faction.name_ko if faction else "중립"
            adj_names = [
                state.towns[a].name_ko
                for a in town.adjacent
                if a in state.towns
            ]
            type_label = _TYPE_ICON.get(town.town_type, town.town_type)
            wall_bar = "█" * int(town.wall_integrity() * 10) + "░" * (10 - int(town.wall_integrity() * 10))
            lines: list[tuple[str, str]] = [
                ("bold underline", f" {town.name_ko}  {town.name_zh}\n"),
                ("", "─" * 36 + "\n"),
                ("", f" 유형  : {type_label}\n"),
                ("", f" 세력  : {faction_name}\n"),
                ("", f" 방어  : {'★' * town.defense_level}{'☆' * (10 - town.defense_level)}\n"),
                ("", f" 주둔  : {town.garrison_strength}/10\n"),
                ("", f" 성벽  : [{wall_bar}] {town.wall_hp}/{town.max_wall_hp}\n"),
                ("", f" 인구  : {town.population:,}\n"),
                ("", f" 세금  : {town.tax_yield}  식량: {town.food_yield}\n"),
                ("", "\n 인접 거점:\n"),
            ]
            for adj in adj_names:
                lines.append(("fg:ansigreen", f"   · {adj}\n"))
            if not adj_names:
                lines.append(("fg:ansibrightblack", "   (없음)\n"))
            return lines

        # ---- key bindings --------------------------------------------

        kb = KeyBindings()

        @kb.add("up")
        def _up(event):
            cursor[0] = (cursor[0] - 1) % len(towns)
            event.app.invalidate()

        @kb.add("down")
        def _down(event):
            cursor[0] = (cursor[0] + 1) % len(towns)
            event.app.invalidate()

        @kb.add("enter")
        def _select(event):
            result[0] = towns[cursor[0]].id
            event.app.exit()

        @kb.add("escape")
        @kb.add("q")
        def _cancel(event):
            event.app.exit()

        # ---- layout --------------------------------------------------

        layout = Layout(
            HSplit([
                VSplit([
                    Window(
                        content=FormattedTextControl(left_text),
                        width=30,
                    ),
                    Window(width=1, char="│"),
                    Window(
                        content=FormattedTextControl(right_text),
                    ),
                ]),
            ])
        )

        app: Application = Application(
            layout=layout,
            key_bindings=kb,
            full_screen=True,
            mouse_support=False,
            color_depth=None,
        )
        app.run()
        return result[0]