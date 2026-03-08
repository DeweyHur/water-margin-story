from __future__ import annotations

from typing import Optional

import questionary
from prompt_toolkit import Application
from prompt_toolkit.shortcuts import prompt as _pt_prompt
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

    # ─── Grid (col, row): col = west→east, row = north→south ───────────────
    # Compact layout meant to fit in ~83 display cols (CELL_W=7, max_col=10)
    _COORDS: dict[str, tuple[int, int]] = {
        # Row 0 — 금·요 북방 접경
        "yanmen":    (4,  0),
        # Row 1 — 하북·산서
        "taiyuan":   (2,  1),  "zhending":  (5,  1),
        "daming":    (7,  1),  "cangzhou":  (9,  1),
        # Row 2 — 중북부·산동
        "weizhou":   (0,  2),  "yanzhou":   (1,  2),
        "xiangzhou": (4,  2),
        "yunzhou":   (7,  2),  "dongping":  (8,  2),
        "qingzhou":  (9,  2),  "dengzhou":  (10, 2),
        # Row 3 — 수도권·양산박
        "mengzhou":  (1,  3),  "bianjing":  (4,  3),
        "liangshan": (7,  3),  "jizhou":    (8,  3),  "dongchang": (9,  3),
        # Row 4 — 화이허 이남
        "huazhou":   (2,  4),
        # Row 6 — 양쯔강 북안
        "yangzhou":  (9,  6),
        # Row 7–8 — 강남
        "luzhou":    (6,  7),  "wuwei":     (7,  7),  "suzhou":    (9,  7),
        "jiangzhou": (6,  8),  "hangzhou":  (9,  8),
    }
    _SHORT: dict[str, str] = {
        "yanmen":    "안문",  "taiyuan":   "태원",  "zhending":  "진정",
        "daming":    "대명",  "cangzhou":  "창주",  "weizhou":   "위주",
        "yanzhou":   "연주",  "xiangzhou": "상주",  "yunzhou":   "운성",
        "dongping":  "동평",  "qingzhou":  "청주",  "dengzhou":  "등주",
        "mengzhou":  "맹주",  "bianjing":  "변경",  "liangshan": "양산",
        "jizhou":    "기주",  "dongchang": "동창",  "huazhou":   "화주",
        "yangzhou":  "양주",  "luzhou":    "노주",  "wuwei":     "무위",
        "jiangzhou": "강주",  "suzhou":    "소주",  "hangzhou":  "항주",
    }
    _TYPE_ICON = {"village": "현(縣)", "fortress": "채(寨)", "metropolis": "부(府)"}
    # Rich style name → prompt_toolkit style string
    _RICH_TO_PTK: dict[str, str] = {
        "bright_red":    "fg:ansibrightred",
        "bright_green":  "fg:ansibrightgreen",
        "bright_blue":   "fg:ansibrightblue",
        "bright_yellow": "fg:ansibrightyellow",
        "yellow":        "fg:ansiyellow",
        "cyan":          "fg:ansicyan",
        "magenta":       "fg:ansimagenta",
        "white":         "fg:ansiwhite",
        "bright_black":  "fg:ansibrightblack",
        "bold black on bright_yellow": "bold fg:ansiblack bg:ansibrightyellow",
        "bold black on yellow":        "bold fg:ansiblack bg:ansiyellow",
        "bold white":  "bold fg:ansiwhite",
        "bold bright_white": "bold fg:ansiwhite",
    }

    def __init__(self) -> None:
        self.console = Console()

    def show_title(self) -> None:
        self.console.clear()
        self.console.print(Panel.fit(
            "[bold red]水滸傳 — 수호지: 북송의 황혼[/]\n"
            "[yellow]108 호한의 합종연횡 전략 시뮬레이션[/]",
            subtitle="Water Margin: Strategy Simulation  v2.0"
        ))

    def choose_scenario(self, scenarios: list[dict]) -> dict:
        """Full-screen scenario selection before hero pick."""
        self.console.clear()
        self.console.print(Panel.fit(
            "[bold red]水滸傳[/]  [yellow]시나리오 선택[/]\n"
            "[dim]역사적 사건을 바탕으로 한 4개의 시나리오[/]",
            border_style="yellow"
        ))
        ids = [s["id"] for s in scenarios]
        display = [
            f"[{s['year']}년]  {s['name_ko']}  —  "
            f"{s['description'].strip().split(chr(10))[0].strip()[:40]}"
            for s in scenarios
        ]
        chosen_id = _select("시나리오 선택 (↑↓ + Enter)", ids, display)
        chosen = next(s for s in scenarios if s["id"] == chosen_id)

        # Show scenario detail
        self.console.clear()
        hint = chosen.get("background_hint", "")
        self.console.print(Panel(
            f"[bold yellow]{chosen['name_ko']}[/]\n\n"
            f"[white]{chosen['description'].strip()}[/]\n\n"
            + (f"[dim]{hint.strip()}[/]" if hint else ""),
            title=f"[bold red]{chosen['year']}년 시나리오",
            border_style="yellow",
        ))
        _pt_prompt("\n  [ Enter ] 키를 눌러 영웅 선택으로 이동... ")
        return chosen

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

    # ------------------------------------------------------------------
    # Shared map canvas builder
    # ------------------------------------------------------------------

    def _build_map_canvas(
        self,
        state: GameState,
        hero_current_town_id: str,
        highlight_town_id: Optional[str] = None,
        reachable_ids: Optional[set] = None,
    ) -> tuple[list[list[tuple[str, str]]], int, int]:
        """Build a shared character canvas for all map views.

        Returns (canvas, canvas_w, canvas_h).
        canvas[y][x] = (char, rich_style_str).
        Wide (CJK) chars occupy canvas[y][x] and canvas[y][x+1]=(\x00, style).
        """
        import unicodedata

        def _dw(s: str) -> int:
            w = 0
            for c in s:
                eaw = unicodedata.east_asian_width(c)
                w += 2 if eaw in ("W", "F") else 1
            return w

        _all_coords, _max_col, _max_row, _ = self._get_map_grid_data(state)
        town_by_id = {t.id: t for t in state.towns.values()}

        CELL_W = 7   # display columns per grid column
        CELL_H = 3   # canvas rows per grid row

        canvas_w = (_max_col + 1) * CELL_W + 6
        canvas_h = (_max_row + 1) * CELL_H + 2

        canvas: list[list[tuple[str, str]]] = [
            [(" ", "") for _ in range(canvas_w)] for _ in range(canvas_h)
        ]

        def _px(col: int) -> int:
            return col * CELL_W + 3

        def _py(row: int) -> int:
            return row * CELL_H + 1

        def _set(y: int, x: int, ch: str, style: str = "") -> None:
            if 0 <= y < canvas_h and 0 <= x < canvas_w:
                if canvas[y][x][0] == " ":
                    canvas[y][x] = (ch, style)

        def _bresenham(x0: int, y0: int, x1: int, y1: int) -> None:
            adx = abs(x1 - x0)
            ady = abs(y1 - y0)
            sx = 1 if x0 < x1 else -1
            sy = 1 if y0 < y1 else -1
            if adx == 0:
                line_ch = "|"
            elif ady == 0:
                line_ch = "-"
            elif (sx > 0) == (sy > 0):
                line_ch = "\\"
            else:
                line_ch = "/"
            err = adx - ady
            while True:
                _set(y0, x0, line_ch, "bright_black")
                if x0 == x1 and y0 == y1:
                    break
                e2 = 2 * err
                if e2 > -ady:
                    err -= ady
                    x0 += sx
                if e2 < adx:
                    err += adx
                    y0 += sy

        # ── 1. Draw connection lines (labels overwrite them later) ─────────
        seen_edges: set[frozenset] = set()
        for tid, town in town_by_id.items():
            if tid not in _all_coords:
                continue
            c0, r0 = _all_coords[tid]
            for adj_id in town.adjacent:
                edge: frozenset = frozenset({tid, adj_id})
                if edge in seen_edges or adj_id not in _all_coords:
                    continue
                seen_edges.add(edge)
                c1, r1 = _all_coords[adj_id]
                _bresenham(_px(c0), _py(r0), _px(c1), _py(r1))

        # ── 2. Faction color resolver ──────────────────────────────────────
        _faction_color: dict[str, str] = {
            "imperial":   "bright_red",
            "liangshan":  "bright_green",
            "erlongshan": "bright_blue",
            "qingfeng":   "magenta",
            "jin":        "yellow",
            "liao":       "cyan",
        }

        def _town_style(tid: str) -> str:
            if tid == highlight_town_id:
                return "bold black on bright_yellow"
            if tid == hero_current_town_id:
                return "bold black on yellow"
            if reachable_ids and tid in reachable_ids:
                return "bold white"
            t = town_by_id.get(tid)
            if not t:
                return "bright_black"
            fid = t.controlled_by_faction or ""
            return _faction_color.get(fid, "bright_black")  # bright_black = unclaimed

        # ── 3. Place town labels (overwrite lines) ─────────────────────────
        for tid, (col, row) in _all_coords.items():
            if tid not in town_by_id:
                continue
            short = self._SHORT.get(tid, tid[:2])  # 2 Hangul chars = 4 display cols
            label_dw = _dw(short)
            cx = _px(col) - label_dw // 2
            cy = _py(row)
            style = _town_style(tid)
            x = cx
            for ch in short:
                cw = _dw(ch)
                if 0 <= cy < canvas_h and 0 <= x < canvas_w:
                    canvas[cy][x] = (ch, style)
                    if cw == 2 and x + 1 < canvas_w:
                        canvas[cy][x + 1] = ("\x00", style)
                x += cw

        return canvas, canvas_w, canvas_h

    def _canvas_to_ptk_tokens(
        self,
        canvas: list[list[tuple[str, str]]],
        canvas_w: int,
        canvas_h: int,
    ) -> list[tuple[str, str]]:
        """Convert a Rich-style canvas to prompt_toolkit (style, text) token list."""
        tokens: list[tuple[str, str]] = []
        for y in range(canvas_h):
            for x in range(canvas_w):
                ch, style = canvas[y][x]
                if ch == "\x00":
                    continue
                ptk_style = self._RICH_TO_PTK.get(style, "")
                tokens.append((ptk_style, ch))
            tokens.append(("", "\n"))
        return tokens

    def _map_legend_rich(self) -> str:
        return (
            "[bright_red]■관군[/] [bright_green]■양산박[/] "
            "[bright_blue]■이룡산[/] [magenta]■청풍채[/] "
            "[cyan]■요나라[/] [yellow]■금나라[/] "
            "[bright_black]· 미점령[/]  [bold black on yellow] 현재위치 [/]"
        )

    def _map_legend_ptk_tokens(self) -> list[tuple[str, str]]:
        return [
            ("", "\n"),
            ("fg:ansibrightred",   "■관군"),    ("", "  "),
            ("fg:ansibrightgreen", "■양산박"),   ("", "  "),
            ("fg:ansibrightblue",  "■이룡산"),   ("", "  "),
            ("fg:ansimagenta",     "■청풍채"),   ("", "  "),
            ("fg:ansicyan",        "■요나라"),   ("", "  "),
            ("fg:ansiyellow",      "■금나라"),   ("", "  "),
            ("fg:ansibrightblack", "· 미점령\n"),
        ]

    def _render_static_map(
        self,
        state: GameState,
        hero_current_town_id: str,
        highlight_town_id: Optional[str] = None,
    ) -> None:
        """Rich-rendered ASCII map with connection lines between adjacent towns."""
        from rich.text import Text

        canvas, canvas_w, canvas_h = self._build_map_canvas(
            state, hero_current_town_id, highlight_town_id
        )

        rule_w = min(canvas_w, 80)
        self.console.print("[bold] 전략 지도  (북→남 / 서→동)[/]")
        self.console.print(self._map_legend_rich())
        self.console.print("─" * rule_w)

        for y in range(canvas_h):
            line = Text()
            x = 0
            while x < canvas_w:
                ch, style = canvas[y][x]
                if ch == "\x00":
                    x += 1
                    continue
                if style:
                    line.append(ch, style=style)
                else:
                    line.append(ch)
                x += 1
            self.console.print(line)

        self.console.print("─" * rule_w)

    def choose_action(self, hero: Hero, state: GameState) -> str:
        """Full-screen action selector: left = info + action list, right = 2D map."""
        choices = [
            ("move",        "이동       — 인접 지역으로 이동"),
            ("investigate", "조사       — 현재 마을 탐문"),
            ("recruit",     "모병       — 병력 충원"),
            ("siege",       "공성       — 마을 점령 시도"),
            ("rest",        "휴식       — AP 회복"),
            ("map",         "지도       — 거점 정보 확인 (AP 소모 없음)"),
            ("end",         "턴 종료    — 다음 턴으로"),
        ]

        cursor = [0]
        result: list[str] = [choices[0][0]]
        faction = state.factions.get(hero.faction_id)
        town = state.towns[hero.current_town]

        _all_coords, _max_col, _max_row, _coord_to_id = self._get_map_grid_data(state)
        town_by_id = {t.id: t for t in state.towns.values()}

        def left_text() -> list[tuple[str, str]]:
            fname = faction.name_ko if faction else "?"
            lines: list[tuple[str, str]] = [
                ("bold fg:ansiyellow", f" 제 {state.turn} 턴  (남은: {state.turns_remaining()})\n"),
                ("", "─" * 28 + "\n"),
                ("bold fg:ansicyan", f" {hero.name_ko}\n"),
                ("", f" 위치  : {town.name_ko}\n"),
                ("", f" 세력  : {fname}\n"),
            ]
            if faction:
                lines += [
                    ("", f" 금전  : {faction.gold}   군량: {faction.food}\n"),
                    ("", f" 명성  : {faction.prestige}   안정도: {state.dynasty_stability}\n"),
                ]
            lines += [
                ("", f" 병력  : {hero.current_army}  AP: {hero.action_points}\n"),
                ("", "─" * 28 + "\n"),
                ("bold underline", " 행동 선택\n"),
                ("", "─" * 28 + "\n"),
            ]
            for i, (cid, desc) in enumerate(choices):
                if i == cursor[0]:
                    lines.append(("bold fg:ansiyellow reverse", f" ▶ {desc}\n"))
                else:
                    lines.append(("", f"   {desc}\n"))
            lines += [("", "\n"), ("fg:ansibrightblack", " ↑↓이동  Enter선택")]
            return lines

        def map_text() -> list[tuple[str, str]]:
            canvas, cw, ch_h = self._build_map_canvas(state, hero.current_town)
            lines: list[tuple[str, str]] = [("bold underline", " 전략 지도\n")]
            lines += self._canvas_to_ptk_tokens(canvas, cw, ch_h)
            lines += self._map_legend_ptk_tokens()
            return lines

        kb = KeyBindings()

        @kb.add("up")
        def _up(event):
            cursor[0] = (cursor[0] - 1) % len(choices)
            event.app.invalidate()

        @kb.add("down")
        def _down(event):
            cursor[0] = (cursor[0] + 1) % len(choices)
            event.app.invalidate()

        @kb.add("enter")
        def _enter(event):
            result[0] = choices[cursor[0]][0]
            event.app.exit()

        layout = Layout(
            VSplit([
                Window(content=FormattedTextControl(left_text), width=30),
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

    def choose_destination(self, hero: Hero, town: Town, state: GameState) -> Optional[str]:
        """Full-screen map-based destination picker.

        Reachable (adjacent) towns are highlighted bold-white on the map.
        ↑↓ / Tab cycle through destinations in the left panel.
        Enter confirms, q / Escape cancels.
        """
        adj_ids = [tid for tid in town.adjacent if tid in state.towns]
        if not adj_ids:
            return None

        town_by_id = {t.id: t for t in state.towns.values()}
        cursor = [0]   # index into adj_ids
        result = [None]
        reachable_set = set(adj_ids)

        def left_text() -> list[tuple[str, str]]:
            sel_id = adj_ids[cursor[0]]
            sel = town_by_id.get(sel_id)
            faction = state.factions.get(sel.controlled_by_faction) if sel else None
            fname = faction.name_ko if faction else "미점령"
            fc = faction.color if faction else "bright_black"
            fstyle = self._RICH_TO_PTK.get(fc, "")

            lines: list[tuple[str, str]] = [
                ("bold underline", " 이동 목적지 선택\n"),
                ("", "─" * 28 + "\n"),
                ("fg:ansibrightblack", " 현재 위치\n"),
                ("bold fg:ansiyellow", f"  {town.name_ko} ({town.name_zh})\n"),
                ("", "\n"),
                ("fg:ansibrightblack", " 이동 대상\n"),
                ("bold fg:ansiwhite",
                 f"  → {sel.name_ko} ({sel.name_zh})\n" if sel else "  →\n"),
                (fstyle, f"  {fname}\n"),
                ("", "\n"),
                ("", "─" * 28 + "\n"),
            ]
            # Adjacent town list
            for i, tid in enumerate(adj_ids):
                t = town_by_id.get(tid)
                if not t:
                    continue
                if i == cursor[0]:
                    lines.append(("bold fg:ansiwhite", f" ▶ {t.name_ko}\n"))
                else:
                    lines.append(("fg:ansibrightblack", f"   {t.name_ko}\n"))
            lines += [
                ("", "\n"),
                ("fg:ansibrightblack", " ↑↓  목적지 변경\n"),
                ("fg:ansibrightgreen", " Enter  이동\n"),
                ("fg:ansibrightred",   " q / Esc  취소\n"),
            ]
            return lines

        def map_text() -> list[tuple[str, str]]:
            sel_id = adj_ids[cursor[0]]
            canvas, cw, ch_h = self._build_map_canvas(
                state, hero.current_town, sel_id, reachable_ids=reachable_set
            )
            lines: list[tuple[str, str]] = [("bold underline", " 전략 지도 — 이동\n")]
            lines += self._canvas_to_ptk_tokens(canvas, cw, ch_h)
            lines += self._map_legend_ptk_tokens()
            lines += [
                ("", "\n"),
                ("bold fg:ansiwhite", " ★ "),
                ("fg:ansibrightblack", "= 이동 가능 지역\n"),
            ]
            return lines

        kb = KeyBindings()

        @kb.add("up")
        def _up(event):
            cursor[0] = (cursor[0] - 1) % len(adj_ids)
            event.app.invalidate()

        @kb.add("down")
        def _down(event):
            cursor[0] = (cursor[0] + 1) % len(adj_ids)
            event.app.invalidate()

        @kb.add("enter")
        def _enter(event):
            result[0] = adj_ids[cursor[0]]
            event.app.exit()

        @kb.add("q")
        @kb.add("escape")
        def _cancel(event):
            result[0] = None
            event.app.exit()

        layout = Layout(
            VSplit([
                Window(content=FormattedTextControl(left_text), width=30),
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

    def show_message(self, message: str) -> None:
        self.console.print(message, justify="left")

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
            player_hero = state.get_player_hero()
            hero_town = player_hero.current_town if player_hero else ""

            canvas, cw, ch_h = self._build_map_canvas(state, hero_town, sel_id)
            lines: list[tuple[str, str]] = [("bold underline", " 전략 지도\n")]
            lines += self._canvas_to_ptk_tokens(canvas, cw, ch_h)
            lines += self._map_legend_ptk_tokens()

            # ── selected town detail ──────────────────────────────────────
            faction = state.factions.get(sel.controlled_by_faction)
            fname = faction.name_ko if faction else "중립 (미점령)"
            wbar = "█" * int(sel.wall_integrity() * 8) + "░" * (8 - int(sel.wall_integrity() * 8))
            adj = ", ".join(
                town_by_id[a].name_ko for a in sel.adjacent if a in town_by_id
            ) or "없음"
            type_label = self._TYPE_ICON.get(sel.town_type, sel.town_type)

            lines += [
                ("", "\n"),
                ("bold fg:ansiyellow", f" ▶ {sel.name_ko} ({sel.name_zh})  {type_label}\n"),
                ("", "─" * 52 + "\n"),
                ("", f" 세력 : {fname:<14}  방어 : {'★' * sel.defense_level}{'☆' * (10 - sel.defense_level)}\n"),
                ("", f" 성벽 : [{wbar}] {sel.wall_hp}/{sel.max_wall_hp}"
                     f"   인구 : {sel.population:,}\n"),
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


    def show_combat_preview(self, hero_town_id: str, target_town_id: str, state: GameState) -> None:
        hero_town = state.towns.get(hero_town_id)
        target_town = state.towns.get(target_town_id)
        h_name = hero_town.name_ko if hero_town else hero_town_id
        t_name = target_town.name_ko if target_town else target_town_id
        self.console.clear()
        self.console.print(f'  {h_name} ===> {t_name}  Attack Start!')
        self._render_static_map(state, hero_town_id, highlight_town_id=target_town_id)
        _pt_prompt('Press Enter to start battle...')

    def show_faction_change_animation(self, town_id: str, old_faction_id: str, new_faction_id: str, state: GameState) -> None:
        import time
        town = state.towns.get(town_id)
        t_name = town.name_ko if town else town_id
        for _ in range(3):
            self.console.clear()
            self._render_static_map(state, town_id, highlight_town_id=town_id)
            time.sleep(0.5)
        self.console.clear()
        self.console.print(f'  Captured: {t_name}  {old_faction_id} -> {new_faction_id}')
