from __future__ import annotations

from typing import Optional

import questionary
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import VSplit, Window
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

    # Grid coordinates (col, row) — geographically approximate
    _COORDS: dict[str, tuple[int, int]] = {
        "weizhou":   (0, 1), "taiyuan":   (3, 0), "cangzhou":  (6, 0),
        "daming":    (5, 1),
        "liangshan": (1, 3), "yunzhou":   (3, 3), "jizhou":    (5, 3),
        "qingzhou":  (7, 3), "dengzhou":  (9, 3),
        "dongping":  (1, 4), "dongchang": (5, 4),
        "mengzhou":  (2, 5),
        "bianjing":  (5, 6),
        "huazhou":   (5, 7),
        "jiangzhou": (5, 9), "yangzhou":  (7, 9),
        "hangzhou":  (7, 10), "suzhou":   (9, 10),
        "luzhou":    (6, 11),
        "jingnan":   (4, 12),
    }
    _SHORT: dict[str, str] = {
        "weizhou": "위주", "taiyuan": "태원", "cangzhou": "창주",
        "daming": "대명", "liangshan": "梁山", "yunzhou": "운주",
        "jizhou": "기주", "dongping": "동평", "qingzhou": "청주",
        "dengzhou": "등주", "dongchang": "동창", "bianjing": "변경",
        "mengzhou": "맹주", "huazhou": "화주", "jiangzhou": "강주",
        "hangzhou": "항주", "suzhou": "소주", "yangzhou": "양주",
        "luzhou": "노주", "jingnan": "형남",
    }
    _TYPE_ICON = {"village": "마을", "fortress": "요새", "metropolis": "대도시"}

    def __init__(self) -> None:
        self.console = Console()

    def show_title(self) -> None:
        self.console.clear()
        self.console.print(Panel.fit(
            "[bold red]수호지: 북송의 황혼 (Water Margin: Strategy Simulation)[/]\n"
            "[yellow]전략 시뮬레이션 확장판[/]",
            subtitle="v2.0 Strategy Update"
        ))

    def choose_hero(self, heroes: list[Hero]) -> Hero:
        self.console.clear()
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
        self.console.clear()
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

    def _get_map_grid_data(self, state: GameState) -> tuple[dict[str, tuple[int, int]], int, int, dict[tuple[int, int], str]]:
        """Prepares coordinate and grid size data for map rendering."""
        towns = list(state.towns.values())
        town_by_id = {t.id: t for t in towns}

        _all_coords: dict[str, tuple[int, int]] = {}
        _max_r = max(r for _, r in self._COORDS.values()) if self._COORDS else 0
        _extra_col = 0
        for t in towns:
            if t.id in self._COORDS:
                _all_coords[t.id] = self._COORDS[t.id]
            else:
                # Assign overflow coords for any town not in _COORDS
                _all_coords[t.id] = (_extra_col, _max_r + 2)
                _extra_col += 1

        _max_col = max(c for c, _ in _all_coords.values()) if _all_coords else 0
        _max_row = max(r for _, r in _all_coords.values()) if _all_coords else 0
        _coord_to_id: dict[tuple[int, int], str] = {
            v: k for k, v in _all_coords.items() if k in town_by_id
        }
        return _all_coords, _max_col, _max_row, _coord_to_id

    def _render_static_map(self, state: GameState, hero_current_town_id: str, highlight_town_id: Optional[str] = None) -> None:
        """Generates and prints a static, non-interactive ASCII map for display."""
        _all_coords, _max_col, _max_row, _coord_to_id = self._get_map_grid_data(state)
        town_by_id = {t.id: t for t in state.towns.values()}

        self.console.print("[bold underline] 전략 지도  (북→남 / 서→동)[/]")
        self.console.print("─" * 52)

        for row in range(_max_row + 1):
            line_parts: list[tuple[str, str]] = [("", "  ")]
            for col in range(_max_col + 1):
                tid = _coord_to_id.get((col, row))
                if tid is None:
                    line_parts.append(("", "       "))   # 7 cols blank
                else:
                    short = self._SHORT.get(tid, tid[:2])
                    t = town_by_id[tid]
                    if tid == highlight_town_id: # New highlight for selected/hovered town
                        style = "bold black on bright_yellow"
                    elif tid == hero_current_town_id:
                        style = "bold black on yellow"
                    elif t.controlled_by_faction == "liangshan":
                        style = "bright_green"
                    else:
                        style = "bright_red"
                    line_parts.append((style, f"[{short}]"))
                    line_parts.append(("", "  "))        # 2-col separator
            for style, text in line_parts:
                self.console.print(text, style=style, end="")
            self.console.print("")  # Newline at the end of each row
        self.console.print("─" * 52)     # Separator at the bottom

    def choose_action(self, hero: Hero, state: GameState) -> str:
        town = state.towns[hero.current_town]
        self.console.print(
            f"\n[bold cyan]{hero.name_ko}[/] "
            f"(위치: {town.name_ko}, 병력: {hero.current_army},"
            f" AP: {hero.action_points})"
        )

        # Display the static map here
        self._render_static_map(state, hero.current_town, highlight_town_id=None)

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
        self.console.clear()
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
        self.console.clear()
        if state.phase == "won":
            self.console.print(Panel.fit(
                "[bold yellow]축하합니다! 천하를 평정하고 새로운 질서를 세웠습니다![/]", title="승리"
            ))
        else:
            self.console.print(Panel.fit(
                "[bold red]송나라가 멸망하고 중원이 혼란에 빠졌습니다...[/]", title="패배"
            ))

    # ------------------------------------------------------------------
    # Interactive map — left: town list, right: 2D grid map + detail
    # ------------------------------------------------------------------

    def show_map(self, state: GameState) -> Optional[str]:
        """Full-screen 2D map with cursor navigation.

        Left panel  : town list (↑↓ to move cursor)
        Right panel : ASCII 2D grid map + selected town detail
        Enter = select town, Escape/q = cancel.
        """
        towns = list(state.towns.values())
        town_by_id = {t.id: t for t in towns}
        cursor = [0]
        result: list[Optional[str]] = [None]

        # Get grid data using the helper method
        _all_coords, _max_col, _max_row, _coord_to_id = self._get_map_grid_data(state)

        # ------------------------------------------------------------------
        def left_text() -> list[tuple[str, str]]:
            lines: list[tuple[str, str]] = [
                ("bold underline", " 거점 목록\n"),
                ("", "─" * 24 + "\n"),
            ]
            for i, t in enumerate(towns):
                faction = state.factions.get(t.controlled_by_faction)
                fname = faction.name_ko[:4] if faction else "중립"
                if i == cursor[0]:
                    lines.append(("bold fg:ansiyellow reverse",
                                  f" ▶ {t.name_ko:<7} {fname}\n"))
                else:
                    lines.append(("", f"   {t.name_ko:<7} {fname}\n"))
            lines += [("", "\n"), ("fg:ansibrightblack", " ↑↓이동  Enter선택  q취소")]
            return lines

        # ------------------------------------------------------------------
        def map_text() -> list[tuple[str, str]]:
            sel_id = towns[cursor[0]].id
            sel = town_by_id[sel_id]

            lines: list[tuple[str, str]] = [
                ("bold underline", " 전략 지도  (북→남 / 서→동)\n"),
                ("", "─" * 52 + "\n"),
            ]

            for row in range(_max_row + 1):
                lines.append(("", "  "))
                for col in range(_max_col + 1):
                    tid = _coord_to_id.get((col, row))
                    if tid is None:
                        lines.append(("", "       "))   # 7 cols blank
                    else:
                        short = self._SHORT.get(tid, tid[:2])
                        t = town_by_id[tid]
                        if tid == sel_id:
                            style = "bold fg:ansiblack bg:ansiyellow"
                        elif t.controlled_by_faction == "liangshan":
                            style = "fg:ansibrightgreen"
                        else:
                            style = "fg:ansibrightred"
                        lines.append((style, f"[{short}]"))
                        lines.append(("", "  "))        # 2-col separator
                lines.append(("", "\n"))

            # ---- selected town detail ----
            faction = state.factions.get(sel.controlled_by_faction)
            fname = faction.name_ko if faction else "중립"
            wbar = "█" * int(sel.wall_integrity() * 8) + "░" * (8 - int(sel.wall_integrity() * 8))
            adj = ", ".join(
                town_by_id[a].name_ko for a in sel.adjacent if a in town_by_id
            ) or "없음"
            type_label = self._TYPE_ICON.get(sel.town_type, sel.town_type)

            lines += [
                ("", "\n"),
                ("bold fg:ansiyellow", f" ▶ {sel.name_ko} ({sel.name_zh})  {type_label}\n"),
                ("", "─" * 52 + "\n"),
                ("", f" 세력 : {fname:<12}  방어 : {'★' * sel.defense_level}{'☆' * (10 - sel.defense_level)}\n"),
                ("", f" 성벽 : [{wbar}] {sel.wall_hp}/{sel.max_wall_hp}"
                     f"      인구 : {sel.population:,}\n"),
                ("", f" 세금 : {sel.tax_yield:<6} 식량 : {sel.food_yield}\n"),
                ("fg:ansibrightblack", f" 인접 : {adj}\n"),
            ]
            return lines

        # ------------------------------------------------------------------
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
        def _enter(event):
            result[0] = towns[cursor[0]].id
            event.app.exit()

        @kb.add("escape")
        @kb.add("q")
        def _quit(event):
            event.app.exit()

        layout = Layout(
            VSplit([
                Window(content=FormattedTextControl(left_text), width=26),
                Window(width=1, char="│"),
                Window(content=FormattedTextControl(map_text)),
            ])
        )

        Application(
            layout=layout,
            key_bindings=kb,
            full_screen=True,
            mouse_support=False,
        ).run()
        return result[0]
