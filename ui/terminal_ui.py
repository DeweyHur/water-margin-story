from __future__ import annotations

import time
from typing import Optional

import questionary
from prompt_toolkit import Application
from prompt_toolkit.shortcuts import prompt as _pt_prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from game.combat_manager import BattleResult, BattleRoundData
from models.army import Army
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
        "bold black on bright_white":  "bold fg:ansiblack bg:ansiwhite",
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

    def choose_hero(self, heroes: list[Hero], state: GameState) -> Hero:
        """Full-screen hero picker: left = list + detail, right = map + faction/position legend."""
        _CLASS_KO: dict[str, str] = {
            "warrior":    "무장 (武將)",
            "strategist": "군사 (軍師)",
            "ranger":     "유협 (遊俠)",
            "rogue":      "의적 (義賊)",
        }

        cursor = [0]
        confirmed: list[Optional[Hero]] = [None]

        def left_text() -> list[tuple[str, str]]:
            h = heroes[cursor[0]]
            class_ko = _CLASS_KO.get(h.hero_class.value, h.hero_class.value)
            faction = state.factions.get(h.faction_id)
            fname = faction.name_ko if faction else "무소속"
            fc = faction.color if faction else "bright_black"
            ptk_fc = self._RICH_TO_PTK.get(fc, "")
            town = state.towns.get(h.current_town)
            tname = town.name_ko if town else "?"

            lines: list[tuple[str, str]] = [
                ("bold underline", " 영웅 선택\n"),
                ("", "─" * 32 + "\n"),
            ]
            for i, hero in enumerate(heroes):
                marker = "▶" if i == cursor[0] else " "
                style = "bold fg:ansiyellow reverse" if i == cursor[0] else "fg:ansibrightblack"
                lines.append((style, f" {marker} {hero.name_ko}  「{hero.nickname}」\n"))

            lines += [
                ("", "─" * 32 + "\n"),
                ("bold fg:ansicyan", f" {h.name_ko} ({h.name_zh})\n"),
                ("bold fg:ansimagenta", f" 「{h.nickname}」\n"),
                ("fg:ansibrightblack", f" {class_ko}\n"),
                ("", "\n"),
                ("", f" 무력  {h.strength:2d}  지력  {h.intelligence:2d}\n"),
                ("", f" 기민  {h.agility:2d}  통솔  {h.leadership:2d}\n"),
                ("", f" 명성  {h.reputation}\n"),
                ("", "\n"),
                ("fg:ansibrightblack", " 출발지: "),
                ("bold fg:ansiyellow", f"{tname}\n"),
                (ptk_fc, f" 세력:   {fname}\n"),
                ("", "\n"),
            ]
            if h.description:
                desc = h.description
                wrap_w = 30
                while len(desc) > wrap_w:
                    lines.append(("fg:ansibrightblack", f" {desc[:wrap_w]}\n"))
                    desc = desc[wrap_w:]
                if desc:
                    lines.append(("fg:ansibrightblack", f" {desc}\n"))
            lines += [
                ("", "\n"),
                ("fg:ansibrightblack", " ↑↓  영웅 변경\n"),
                ("fg:ansibrightgreen", " Enter  선택\n"),
                ("fg:ansibrightred",   " q / Esc  시나리오로 돌아가기\n"),
            ]
            return lines

        def map_text() -> list[tuple[str, str]]:
            h = heroes[cursor[0]]
            canvas, cw, ch_h = self._build_map_canvas(state, h.current_town)
            lines: list[tuple[str, str]] = [
                ("bold underline", " 전략 지도 — 세력 분포 · 영웅 위치\n")
            ]
            lines += self._canvas_to_ptk_tokens(canvas, cw, ch_h)
            lines += self._map_legend_ptk_tokens()
            lines += [("bold fg:ansiyellow", " [현재선택] = 노란 배경\n"), ("", "\n")]
            lines.append(("bold underline", " 영웅 출발지\n"))
            for hero in heroes:
                t = state.towns.get(hero.current_town)
                tname = t.name_ko if t else "?"
                if hero is h:
                    lines.append(("bold fg:ansiyellow", f"  ▶ {hero.name_ko}  →  {tname}\n"))
                else:
                    lines.append(("fg:ansibrightblack", f"     {hero.name_ko}  →  {tname}\n"))
            return lines

        kb = KeyBindings()

        @kb.add("up")
        def _up(event):
            cursor[0] = (cursor[0] - 1) % len(heroes)
            event.app.invalidate()

        @kb.add("down")
        def _down(event):
            cursor[0] = (cursor[0] + 1) % len(heroes)
            event.app.invalidate()

        @kb.add("enter")
        def _enter(event):
            confirmed[0] = heroes[cursor[0]]
            event.app.exit()

        @kb.add("q")
        @kb.add("escape")
        def _back(event):
            confirmed[0] = None
            event.app.exit()

        layout = Layout(
            VSplit([
                Window(content=FormattedTextControl(left_text), width=34),
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

        # Flush any leftover keystrokes (e.g. the Enter that dismissed this app)
        import sys, termios
        try:
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except Exception:
            pass

        return confirmed[0]

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

    def show_ai_turn_summary(self, logs: list[str]) -> None:
        import questionary as _q

        if not logs:
            return

        lines = [f"  [dim]•[/] {line}" for line in logs[:14]]
        if len(logs) > 14:
            lines.append(f"  [dim]•[/] ... 외 {len(logs) - 14}건")

        self.console.print(Panel(
            "\n".join(lines),
            title="[bold red]상대 AI 턴 요약[/]",
            border_style="red",
            padding=(1, 2),
        ))
        _q.press_any_key_to_continue("[ 아무 키 ] AI 턴 결과 확인 후 계속...").ask()

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
                return "bold black on bright_white"  # 흰 배경 = 현재 위치 (세력색과 겹치지 않음)
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
            "[bright_black]· 미점령[/]  "
            "[bold black on bright_white] 현재위치 [/]  "
            "[bold black on bright_yellow] 대상 [/]"
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
            ("fg:ansibrightblack", "· 미점령"),  ("", "  "),
            ("bold fg:ansiblack bg:ansiwhite",  " 현재위치 "),  ("", "\n"),
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
        from models.hero import HeroClass as _HeroClass
        town = state.towns[hero.current_town]
        _is_own = town.controlled_by_faction == hero.faction_id
        _is_neutral = hero.faction_id == "neutral"
        _has_faction = hero.faction_id != "neutral" and state.factions.get(hero.faction_id) is not None
        _can_join = _is_neutral and town.controlled_by_faction is not None
        _is_enemy_town = town.controlled_by_faction not in (hero.faction_id, None)
        contactable = []
        for h in state.heroes.values():
            if h.id == hero.id or not h.is_alive() or h.current_town != hero.current_town:
                continue
            if h.is_player_controlled or h.following_hero_id:
                continue
            if hero.faction_id == "neutral":
                if h.faction_id == "neutral":
                    contactable.append(h)
            else:
                if h.faction_id in (hero.faction_id, "neutral"):
                    contactable.append(h)
        companions = [
            h for h in state.heroes.values()
            if h.following_hero_id == hero.id and h.is_alive()
        ]
        party_army = hero.current_army + sum(h.current_army for h in companions)

        # Class-specific action labels
        _class_action_labels = {
            _HeroClass.WARRIOR:    "결투       — 수비대장 격투 (무력)",
            _HeroClass.STRATEGIST: "모략       — 거점 교란·내정 지원 (지력)",
            _HeroClass.RANGER:     "정찰       — 인근 일괄 탐문 (기민)",
            _HeroClass.ROGUE:      "잠입       — 적 거점 침투·탈취 (기민)",
        }
        _class_label = _class_action_labels.get(hero.hero_class, "특기       — 전용 행동")
        _class_action_available = True
        if hero.hero_class in (_HeroClass.WARRIOR, _HeroClass.ROGUE):
            _class_action_available = _is_enemy_town

        choices: list[tuple[str, str]] = [
            ("move",        "이동       — 인접 지역으로 이동"),
            ("investigate", "조사       — 현재 마을 탐문"),
            ("recruit",     "모병       — 병력 충원"),
        ]
        if _is_own:
            choices.append(("admin", "내정       — 거점 행정 강화 (세금·식량 증가)"))
        else:
            if hero.current_army > 0 or not _is_neutral:
                choices.append(("siege", "공성       — 마을 점령 시도"))
        if contactable:
            choices.append(("rally", "집결       — 같은 지역 인재 컨택·동행 영입"))
        if _class_action_available:
            choices.append(("class_action", _class_label))
        if _can_join:
            choices.append(("join", "합류       — 현 세력에 가담"))
        _rest_desc = "휴식       — HP 회복 + 병력 보충" if _is_own else "휴식       — HP 회복 + 현지 탐문"
        choices += [
            ("rest", _rest_desc),
            ("map",  "지도       — 거점 정보 확인 (AP 소모 없음)"),
            ("end",  "턴 종료    — 다음 턴으로"),
        ]

        cursor = [0]
        result: list[str] = [choices[0][0]]
        faction = state.factions.get(hero.faction_id)

        _all_coords, _max_col, _max_row, _coord_to_id = self._get_map_grid_data(state)
        town_by_id = {t.id: t for t in state.towns.values()}

        # Class action relevant stat colour hint
        _class_stat_hint = {
            _HeroClass.WARRIOR:    ("무력", hero.strength),
            _HeroClass.STRATEGIST: ("지력", hero.intelligence),
            _HeroClass.RANGER:     ("기민", hero.agility),
            _HeroClass.ROGUE:      ("기민", hero.agility),
        }
        _stat_name, _stat_val = _class_stat_hint.get(hero.hero_class, ("통솔", hero.leadership))

        def left_text() -> list[tuple[str, str]]:
            fname = faction.name_ko if faction else "무소속"
            fcolor = self._RICH_TO_PTK.get(faction.color if faction else "bright_black", "")

            # 현재 위치 지배 세력
            town_faction = state.factions.get(town.controlled_by_faction or "")
            town_fname = town_faction.name_ko if town_faction else "무소속"
            tfcolor = self._RICH_TO_PTK.get(town_faction.color if town_faction else "bright_black", "fg:ansibrightblack")
            is_own = town.controlled_by_faction == hero.faction_id

            # Hero class label
            _class_ko = {
                _HeroClass.WARRIOR: "무장",
                _HeroClass.STRATEGIST: "군사",
                _HeroClass.RANGER: "유협",
                _HeroClass.ROGUE: "의적",
            }.get(hero.hero_class, "")

            lines: list[tuple[str, str]] = [
                ("bold fg:ansiyellow", f" 제 {state.turn} 턴  (남은: {state.turns_remaining()})\n"),
                ("", "─" * 28 + "\n"),
                ("bold fg:ansicyan", f" {hero.name_ko}"),
                ("fg:ansibrightblack", f"  [{_class_ko}]\n"),
                ("fg:ansibrightblack", " 세력  : "),
                (fcolor or "bold", f"{fname}\n"),
                ("", f" 병력  : {hero.current_army:,}  AP: {hero.action_points}\n"),
                ("fg:ansibrightblack", " 파티병력: "),
                ("bold fg:ansigreen", f"{party_army:,}\n"),
            ]
            if faction:
                lines += [
                    ("", f" 금전  : {faction.gold:,}   군량: {faction.food:,}\n"),
                ]
            else:
                # 재야 영웅: 개인 군자금 표시
                lines += [
                    ("fg:ansibrightblack", " 군자금: "),
                    ("fg:ansiyellow", f"{hero.personal_gold:,} 금\n"),
                ]
            # Class-specific stat highlight
            lines += [
                ("fg:ansibrightblack", f" {_stat_name}특기: "),
                ("bold fg:ansiyellow", f"{_stat_val}/10  "),
                ("fg:ansibrightblack", f"({_class_label[:4]})\n"),
            ]
            lines += [
                ("fg:ansibrightblack", " 동행  : "),
                ("", f"{len(companions)}명\n"),
            ]
            if companions:
                names = ", ".join(h.name_ko for h in companions[:2])
                extra = "" if len(companions) <= 2 else f" 외 {len(companions)-2}명"
                lines += [
                    ("fg:ansibrightblack", "  └ "),
                    ("fg:ansicyan", f"{names}{extra}\n"),
                ]
            lines += [
                ("fg:ansibrightblack", " 컨택 가능: "),
                ("", f"{len(contactable)}명\n"),
            ]
            if contactable:
                for h in contactable[:3]:
                    lines.append(("fg:ansibrightblack", f"  · {h.name_ko} ({h.hero_class.value})\n"))
                if len(contactable) > 3:
                    lines.append(("fg:ansibrightblack", f"  · 외 {len(contactable)-3}명\n"))
            lines += [
                ("", "─" * 28 + "\n"),
                ("bold underline", f" 현재 위치: {town.name_ko}\n"),
                ("", "─" * 28 + "\n"),
                ("fg:ansibrightblack", " 종류   : "),
                ("", f"{self._TYPE_ICON.get(town.town_type, '?')}\n"),
                ("fg:ansibrightblack", " 인구   : "),
                ("", f"{town.population:,}명\n"),
                ("fg:ansibrightblack", " 지배세력: "),
                (tfcolor, f"{town_fname}\n"),
            ]
            if town_faction:
                lines += [
                    ("fg:ansibrightblack", " 수비대 : "),
                    ("", f"{town.garrison_strength * 200:,}명\n"),
                    ("fg:ansibrightblack", " 방어도 : "),
                    ("", f"{'★' * town.defense_level}{'☆' * (10 - town.defense_level)}\n"),
                ]
                if town.max_wall_hp > 0:
                    wall_pct = int(town.wall_integrity() * 100)
                    wall_color = "fg:ansired" if wall_pct < 50 else "fg:ansigreen"
                    lines += [
                        ("fg:ansibrightblack", " 성벽   : "),
                        (wall_color, f"{wall_pct}%\n"),
                    ]
                if is_own:
                    lines += [
                        ("fg:ansibrightblack", " 세금/턴: "),
                        ("fg:ansiyellow", f"{town.tax_yield}\n"),
                        ("fg:ansibrightblack", " 식량/턴: "),
                        ("fg:ansigreen", f"{town.food_yield}\n"),
                        ("fg:ansibrightblack", " 내정도 : "),
                        ("", f"{town.admin_level}/10\n"),
                    ]
                else:
                    clue_bar = "■" * town.clue_level + "□" * (5 - town.clue_level)
                    lines += [
                        ("fg:ansibrightblack", " 탐문도 : "),
                        ("", f"{clue_bar} {town.clue_level}/5\n"),
                    ]
            else:
                clue_bar = "■" * town.clue_level + "□" * (5 - town.clue_level)
                lines += [
                    ("fg:ansibrightblack", " (무주공산)\n"),
                    ("fg:ansibrightblack", " 탐문도 : "),
                    ("", f"{clue_bar} {town.clue_level}/5\n"),
                ]
            if town.gao_qiu_presence:
                lines.append(("bold fg:ansired", " ⚠ 고구 세력 주둔 중\n"))

            lines += [
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

    def choose_party_candidate(self, hero: Hero, candidates: list[Hero], state: GameState) -> Optional[str]:
        labels = []
        values = []
        for h in candidates:
            labels.append(
                f"{h.name_ko} 「{h.nickname}」  무:{h.strength} 지:{h.intelligence} 기:{h.agility} 통:{h.leadership} 병:{h.current_army:,}"
            )
            values.append(h.id)

        picked = _select(
            f"동행 영웅 선택 — {hero.name_ko}과(와) 의기투합할 인물을 고르세요",
            values,
            labels,
        )
        return picked if picked else None

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

    def wait_for_continue(self, prompt: str = "[ 아무 키 ] 계속...") -> None:
        import questionary as _q

        _q.press_any_key_to_continue(prompt).ask()

    def show_action_blocked(self, reason: str, details: list[str] | None = None) -> None:
        """Show a detailed failure reason and wait for user acknowledgement."""
        import questionary as _q

        lines = [f"[bold red]행동 실패[/]", "", f"[white]{reason}[/]"]
        if details:
            lines.append("")
            lines.append("[bold yellow]확인 사항[/]")
            for item in details:
                lines.append(f"  [dim]•[/] {item}")

        self.console.print(Panel(
            "\n".join(lines),
            title="[bold red]진행 불가[/]",
            border_style="red",
            padding=(1, 2),
        ))
        _q.press_any_key_to_continue("[ 아무 키 ] 확인 후 행동 선택으로 돌아가기...").ask()

    def show_setup_complete(self, state: GameState, hero: Hero) -> None:
        from rich.columns import Columns

        self.console.clear()

        faction = state.factions.get(hero.faction_id)
        town = state.towns.get(hero.current_town)
        faction_color = faction.color if faction else "white"
        town_icon = self._TYPE_ICON.get(town.town_type, "") if town else ""

        # ── Class & skill label tables ─────────────────────────────────────
        _CLASS_KO: dict[str, str] = {
            "warrior":    "무장 (武將)",
            "strategist": "군사 (軍師)",
            "ranger":     "유협 (遊俠)",
            "rogue":      "의적 (義賊)",
        }
        _SKILL_KO: dict[str, str] = {
            "righteous_call": "의협 소집", "leadership_aura": "지휘 기운", "pardon_plea": "사면 탄원",
            "unrivaled_might": "천하무적", "spear_master": "창술 달인", "merchant_network": "상인 인맥",
            "chain_stratagem": "연환계", "ambush_plan": "매복 계책", "spy_network": "첩자망",
            "thunder_magic": "뇌법", "rain_call": "기우술", "taoist_arts": "도술",
            "blade_dance": "대도술", "cavalry_charge": "기병 돌격", "suppress_rebels": "토벌 전법",
            "serpent_spear": "장사 호기", "outlaw_rage": "무법 분노",
            "thunderstrike": "벼락 일격", "berserker_rush": "광전사 돌진", "wolf_mace": "쌍봉 난무",
            "twin_whips": "쌍편술", "iron_cavalry": "철갑 기병", "army_drill": "군사 훈련",
            "eagle_eye": "매의 눈", "rapid_arrow": "속사술", "mounted_archery": "기마 궁술",
            "noble_network": "귀족 인맥", "harbor_fugitive": "항구 은신", "big_purse": "큰 지갑",
            "estate_guard": "장원 수비", "hidden_dart": "암기술", "logistics": "병참술",
            "dignified_bear": "위엄 거인", "prison_break": "탈옥", "gallop_charge": "질풍 돌격",
            "iron_staff": "철봉술", "uproot_willow": "발목술", "zen_fury": "선기 분노",
            "tiger_slayer": "호랑이 사냥", "drunk_fist": "취권", "dual_blades": "쌍도",
            "berserk": "광폭", "twin_axes": "쌍도끼", "unstoppable": "불굴",
            "wrestling_master": "씨름 달인", "infiltrate": "잠입", "crossbow_ace": "쇠뇌 명수",
            "river_swim": "도강술", "water_ambush": "수중 매복", "fish_merchant": "어물상",
            "logistic_master": "군수 달인", "army_cook": "군 요리사", "morale_boost": "사기 고취",
            "iron_rod": "철봉술", "night_patrol": "야간 순찰", "jailbreak": "탈옥술",
        }

        class_label = _CLASS_KO.get(hero.hero_class.value, hero.hero_class.value)

        # ── Title panel ────────────────────────────────────────────────────
        title_text = (
            f"[bold yellow]{hero.name_ko}[/]  [dim]({hero.name_zh})[/]  "
            f"[bold magenta]「{hero.nickname}」[/]\n"
            f"[dim]계열:[/] [{faction_color}]{class_label}[/]   "
            f"[dim]출발지:[/] [cyan]{town_icon} {town.name_ko if town else '?'}[/]   "
            f"[dim]소속:[/] [{faction_color}]{faction.name_ko if faction else '무소속'}[/]"
        )
        self.console.print(Panel(
            title_text,
            title="[bold yellow]✦  영웅 소개  ✦[/]",
            border_style="yellow",
            padding=(1, 4),
        ))
        self.console.print()

        # ── Description ────────────────────────────────────────────────────
        if hero.description:
            self.console.print(Panel(
                f"[italic]{hero.description}[/]",
                title="[dim]인물 배경[/]",
                border_style="dim white",
            ))
            self.console.print()

        # ── Stat bar helper ────────────────────────────────────────────────
        def _bar(val: int, mx: int = 10) -> str:
            filled = round(val * 8 / mx)
            return "[yellow]" + "█" * filled + "[/][dim]" + "░" * (8 - filled) + "[/]"

        # ── Ability stats panel ────────────────────────────────────────────
        stats_lines = [
            f"[bold]무력[/]   {_bar(hero.strength)}  [cyan]{hero.strength:2d}[/]",
            f"[bold]지력[/]   {_bar(hero.intelligence)}  [cyan]{hero.intelligence:2d}[/]",
            f"[bold]기민[/]   {_bar(hero.agility)}  [cyan]{hero.agility:2d}[/]",
            f"[bold]통솔[/]   {_bar(hero.leadership)}  [cyan]{hero.leadership:2d}[/]",
            "",
            f"[bold]명성[/]   [cyan]{hero.reputation}[/]",
        ]
        stats_panel = Panel(
            "\n".join(stats_lines),
            title="[bold]능력치[/]",
            border_style="cyan",
        )

        # ── Possessions & power panel (가진 것들) ──────────────────────────
        skills_display = [
            f"  · {_SKILL_KO.get(s, s.replace('_', ' '))}"
            for s in hero.skills
        ]
        items_lines = [
            f"[bold]병력[/]   [green]{hero.current_army:,}[/]",
            f"[bold]체력[/]   [green]{hero.hp} / {hero.max_hp}[/]",
            f"[bold]행동력[/] [green]{hero.action_points} AP[/]",
            "",
            "[bold]보유 기술[/]",
        ] + (skills_display if skills_display else ["  [dim](기술 없음)[/]"])
        items_panel = Panel(
            "\n".join(items_lines),
            title="[bold]가진 것들[/]",
            border_style="green",
        )

        self.console.print(Columns([stats_panel, items_panel], equal=True, expand=True))
        self.console.print()

        # ── Companions panel (동료) ────────────────────────────────────────
        if hero.faction_id != "neutral":
            companions = [
                h for h in state.heroes.values()
                if h.id != hero.id and h.faction_id == hero.faction_id
            ][:6]
            comp_title = "동료 — 같은 세력"
        else:
            companions = [
                h for h in state.heroes.values()
                if h.id != hero.id and h.current_town == hero.current_town
            ][:6]
            comp_title = "동료 — 같은 지역"

        if companions:
            comp_lines = [
                f"[bold]{c.name_ko}[/] [dim]{c.nickname}[/]  "
                f"[bright_blue]{_CLASS_KO.get(c.hero_class.value, '')}[/]"
                for c in companions
            ]
        else:
            comp_lines = ["[dim](알려진 동료 없음)[/]"]

        companions_panel = Panel(
            "\n".join(comp_lines),
            title=f"[bold magenta]{comp_title}[/]",
            border_style="magenta",
        )

        # ── Faction panel (세력) ───────────────────────────────────────────
        if faction:
            controlled = [
                state.towns[tid].name_ko
                for tid in faction.controlled_towns
                if tid in state.towns
            ]
            controlled_str = (
                "  ".join(f"[cyan]{n}[/]" for n in controlled)
                if controlled else "[dim]없음[/]"
            )
            faction_lines = [
                f"[bold]세력명[/]  [{faction_color}]{faction.name_ko} ({faction.name_zh})[/]",
                "",
                f"[bold]금전[/]   [yellow]{faction.gold:,}[/]",
                f"[bold]군량[/]   [yellow]{faction.food:,}[/]",
                f"[bold]명성[/]   [yellow]{faction.prestige}[/]",
                "",
                "[bold]점령 거점[/]",
                f"  {controlled_str}",
            ]
        else:
            faction_lines = ["[dim]소속 세력 없음[/]"]

        faction_panel = Panel(
            "\n".join(faction_lines),
            title="[bold]내 세력[/]",
            border_style=faction_color if faction else "dim",
        )

        self.console.print(Columns([companions_panel, faction_panel], equal=True, expand=True))
        self.console.print()

        questionary.press_any_key_to_continue("[ Enter ] 또는 아무 키나 눌러 첫 턴을 시작하세요...", style=_STYLE)

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

    def _show_town_detail(self, town_id: str, state: GameState) -> None:
        """Rich-rendered detailed town panel, gated by clue_level."""
        from rich.columns import Columns

        town = state.towns.get(town_id)
        if not town:
            return

        player_hero = state.get_player_hero()
        is_player_town = player_hero and player_hero.current_town == town_id
        clue = 5 if is_player_town else town.clue_level

        faction = state.factions.get(town.controlled_by_faction or "")
        faction_color = faction.color if faction else "bright_black"
        type_label = self._TYPE_ICON.get(town.town_type, town.town_type)

        HIDDEN = "[dim]???[/]"

        def _bar(val: int, mx: int, width: int = 8) -> str:
            filled = round(val * width / mx)
            return "[yellow]" + "█" * filled + "[/][dim]" + "░" * (width - filled) + "[/]"

        # ── Title ─────────────────────────────────────────────────────────
        title_lines = [
            f"[bold cyan]{town.name_ko}[/]  [dim]({town.name_zh})[/]  {type_label}",
        ]
        if clue >= 1:
            fname = f"[{faction_color}]{faction.name_ko}[/]" if faction else "[dim]미점령[/]"
            title_lines.append(f"[dim]세력:[/] {fname}")
        else:
            title_lines.append(f"[dim]세력:[/] {HIDDEN}")

        adj_names = ", ".join(
            state.towns[a].name_ko for a in town.adjacent if a in state.towns
        ) or "없음"
        title_lines.append(f"[dim]인접:[/] [bright_black]{adj_names}[/]")

        clue_bar = "[yellow]" + "■" * clue + "[/][dim]" + "□" * (5 - clue) + "[/]"
        if not is_player_town:
            title_lines.append(f"[dim]단서:[/] {clue_bar}  {clue}/5")

        self.console.print(Panel(
            "\n".join(title_lines),
            title=f"[bold yellow]지역 상세 정보[/]",
            border_style="yellow",
            padding=(0, 2),
        ))
        self.console.print()

        # ── Left: Military / Economy ───────────────────────────────────────
        mil_lines: list[str] = ["[bold underline]군사[/]\n"]
        if clue >= 2:
            mil_lines += [
                f"[dim]수비 등급[/]  {_bar(town.defense_level, 10)}  {town.defense_level}/10",
                f"[dim]수비대   [/]  {town.garrison_strength * 200:,}명",
            ]
        else:
            mil_lines += [
                f"[dim]수비 등급[/]  {HIDDEN}",
                f"[dim]수비대   [/]  {HIDDEN}",
            ]
        if clue >= 3:
            wall_pct = int(town.wall_hp / town.max_wall_hp * 100)
            wbar = _bar(town.wall_hp, town.max_wall_hp)
            mil_lines += [
                f"[dim]성벽     [/]  {wbar}  {town.wall_hp}/{town.max_wall_hp}  ({wall_pct}%)",
                f"[dim]주둔 가능[/]  {town.max_garrison:,}명",
            ]
        else:
            mil_lines += [
                f"[dim]성벽     [/]  {HIDDEN}",
            ]

        eco_lines: list[str] = ["\n[bold underline]경제[/]\n"]
        if clue >= 1:
            pop_ranges = [(0, 5000, "소규모"), (5000, 15000, "보통"), (15000, 30000, "대도시"), (30000, 999999, "거대도시")]
            pop_label = next((lbl for lo, hi, lbl in pop_ranges if lo <= town.population < hi), "?")
            eco_lines.append(f"[dim]인구[/]  {town.population:,}  [bright_black]({pop_label})[/]")
        else:
            eco_lines.append(f"[dim]인구[/]  {HIDDEN}")
        if clue >= 2:
            eco_lines += [
                f"[dim]세금[/]  {town.tax_yield}/턴",
                f"[dim]식량[/]  {town.food_yield}/턴",
            ]
        else:
            eco_lines += [
                f"[dim]세금[/]  {HIDDEN}",
                f"[dim]식량[/]  {HIDDEN}",
            ]

        mil_panel = Panel(
            "\n".join(mil_lines + eco_lines),
            title="[bold]현황[/]",
            border_style="cyan",
        )

        # ── Right: Intel / Heroes ─────────────────────────────────────────
        intel_lines: list[str] = ["[bold underline]고구 관련 정보[/]\n"]
        if is_player_town or clue >= 3:
            if town.gao_qiu_presence == 0:
                intel_lines.append("[dim]고구 흔적 없음[/]")
            elif town.gao_qiu_presence == 1:
                intel_lines.append("[yellow]고구 관련 인물이 통과했다는 소문[/]")
            elif town.gao_qiu_presence == 2:
                intel_lines.append("[yellow]고구 측근이 이 지역에 있었던 흔적[/]")
            else:
                intel_lines.append("[bold red]고구(高俅)가 이 지역에 있음 — 확인됨![/]")
        else:
            intel_lines.append(f"[dim]단서 부족 (조사 필요)[/]")

        # Heroes in this town
        heroes_here = [
            h for h in state.heroes.values()
            if h.current_town == town_id
        ]
        intel_lines.append("\n[bold underline]이 지역의 인물[/]\n")
        if heroes_here:
            for h in heroes_here:
                is_player = h.is_player_controlled
                prefix = "[bold yellow]★ [/]" if is_player else "  "
                hfaction = state.factions.get(h.faction_id)
                hcolor = hfaction.color if hfaction else "bright_black"
                if clue >= 2 or is_player or h.faction_id == (player_hero.faction_id if player_hero else ""):
                    intel_lines.append(
                        f"{prefix}[bold]{h.name_ko}[/] [{hcolor}]{h.nickname}[/]\n"
                        f"   [dim]{h.faction_id}[/]  병력 {h.current_army:,}"
                    )
                else:
                    intel_lines.append(f"  [dim]??? (신원 불명)[/]")
        else:
            intel_lines.append("[dim](알려진 인물 없음)[/]")

        # Town description
        town_desc = getattr(town, "description", None)
        if town_desc and clue >= 1:
            intel_lines += ["\n[bold underline]배경[/]\n", f"[italic dim]{town_desc}[/]"]

        intel_panel = Panel(
            "\n".join(intel_lines),
            title="[bold]정보[/]",
            border_style="magenta",
        )

        self.console.print(Columns([mil_panel, intel_panel], equal=True, expand=True))
        self.console.print()

        import questionary as _q
        _q.press_any_key_to_continue(" [ 아무 키 ] 지도로 돌아가기...").ask()

    def show_map(self, state: GameState) -> Optional[str]:
        """Full-screen 2D map with cursor navigation.

        Left panel  : town list (↑↓ to move cursor)
        Right panel : ASCII 2D grid map + brief info
        Enter = view detailed town info, Escape/q = close map.
        """
        towns = list(state.towns.values())
        town_by_id = {t.id: t for t in towns}
        cursor = [0]
        open_detail: list[Optional[str]] = [None]

        player_hero = state.get_player_hero()
        hero_town = player_hero.current_town if player_hero else ""

        def left_text() -> list[tuple[str, str]]:
            lines: list[tuple[str, str]] = [
                ("bold underline", " 거점 목록\n"),
                ("", "─" * 28 + "\n"),
            ]
            for i, t in enumerate(towns):
                faction = state.factions.get(t.controlled_by_faction or "")
                fcolor = self._RICH_TO_PTK.get(faction.color if faction else "bright_black", "")
                is_here = t.id == hero_town
                here_mark = "★" if is_here else " "
                clue = 5 if is_here else t.clue_level

                # Army icon based on garrison_strength
                gs = t.garrison_strength
                army_icon = "◉" if gs >= 8 else "●" if gs >= 5 else "○" if gs >= 2 else "·"
                # Admin icon — only shown if player knows (own town or clue≥2)
                admin_known = is_here or clue >= 2
                adm = t.admin_level
                admin_icon = ("▲" if adm >= 7 else "△" if adm >= 4 else "▽") if admin_known else "?"

                if i == cursor[0]:
                    lines.append(("bold fg:ansiyellow reverse",
                                  f" ▶ {here_mark}{t.name_ko:<6}\n"))
                    faction_name = faction.name_ko[:4] if faction else "미점령"
                    lines.append((fcolor or "fg:ansibrightblack",
                                  f"   세력:{faction_name:<4}  정보:{clue}/5\n"))
                    lines.append(("", f"   병:{army_icon}{gs}/10  내정:{admin_icon}{adm if admin_known else '?'}/10\n"))
                else:
                    lines.append(("",
                                  f"   {here_mark}{t.name_ko:<6} {army_icon}{admin_icon}\n"))
            lines += [("", "\n"),
                      ("fg:ansibrightblack", " ↑↓  거점 변경\n"),
                      ("fg:ansibrightgreen", " Enter  상세 보기\n"),
                      ("fg:ansibrightred",   " q / Esc  닫기\n")]
            return lines

        def map_text() -> list[tuple[str, str]]:
            sel_id = towns[cursor[0]].id
            sel = town_by_id[sel_id]
            clue = 5 if sel_id == hero_town else sel.clue_level

            # ── Player faction block ───────────────────────────────────────
            lines: list[tuple[str, str]] = []
            if player_hero:
                pfaction = state.factions.get(player_hero.faction_id)
                pfc = self._RICH_TO_PTK.get(pfaction.color if pfaction else "white", "")
                pfname = pfaction.name_ko if pfaction else player_hero.faction_id
                p_towns = [t for t in towns if t.controlled_by_faction == player_hero.faction_id]
                lines += [
                    ("bold underline", " 내 세력\n"),
                    ("", "─" * 48 + "\n"),
                    ("fg:ansibrightblack", " 세력  : "),
                    (pfc or "bold", f"{pfname}\n"),
                    ("fg:ansibrightblack", " 영웅  : "),
                    ("bold", f"{player_hero.name_ko}  "),
                    ("fg:ansibrightblack", "거점 "),
                    ("bold", f"{player_hero.current_town}\n"),
                ]
                if pfaction:
                    lines += [
                        ("fg:ansibrightblack", " 자금  : "),
                        ("fg:ansiyellow",      f"{pfaction.gold:,} 관\n"),
                        ("fg:ansibrightblack", " 식량  : "),
                        ("fg:ansigreen",       f"{pfaction.food:,} 석\n"),
                    ]
                lines += [
                    ("fg:ansibrightblack", " 거점  : "),
                    ("bold", f"{len(p_towns)}곳  "),
                ]
                for pt in p_towns[:6]:
                    fc2 = self._RICH_TO_PTK.get(pfaction.color if pfaction else "white", "")
                    lines.append((fc2 or "", f"{pt.name_ko} "))
                if len(p_towns) > 6:
                    lines.append(("fg:ansibrightblack", f"+{len(p_towns)-6}…"))
                lines.append(("", "\n"))
                lines.append(("", "\n"))

            # ── Map canvas ─────────────────────────────────────────────────
            canvas, cw, ch_h = self._build_map_canvas(state, hero_town, sel_id)
            lines += [("bold underline", " 전략 지도\n")]
            lines += self._canvas_to_ptk_tokens(canvas, cw, ch_h)
            lines += self._map_legend_ptk_tokens()

            # ── All factions overview ──────────────────────────────────────
            lines += [
                ("", "\n"),
                ("bold underline", " 전체 세력\n"),
                ("", "─" * 48 + "\n"),
            ]
            for fid, faction in state.factions.items():
                fc = self._RICH_TO_PTK.get(faction.color, "")
                f_towns = [t for t in towns if t.controlled_by_faction == fid]
                is_player_f = player_hero and fid == player_hero.faction_id
                marker = " ◀나" if is_player_f else "   "
                town_names = " ".join(t.name_ko for t in f_towns[:5])
                if len(f_towns) > 5:
                    town_names += f" +{len(f_towns)-5}"
                f_gold = f"{faction.gold:,}관" if is_player_f else "?"
                lines += [
                    (fc or "bold", f"{faction.name_ko:<6}"),
                    ("fg:ansibrightblack", marker + "  "),
                    ("", f"{len(f_towns)}거점  "),
                    ("fg:ansibrightblack", f"{f_gold}\n"),
                    ("fg:ansibrightblack", f"         {town_names}\n") if f_towns else ("", ""),
                ]

            # ── Selected town info ─────────────────────────────────────────
            faction = state.factions.get(sel.controlled_by_faction or "")
            fname = faction.name_ko if faction else "미점령"
            fc = self._RICH_TO_PTK.get(faction.color if faction else "bright_black", "")
            type_label = self._TYPE_ICON.get(sel.town_type, sel.town_type)
            HIDDEN = "???"

            lines += [
                ("", "\n"),
                ("bold fg:ansiyellow", f" ▶ {sel.name_ko} ({sel.name_zh})  {type_label}\n"),
                ("", "─" * 48 + "\n"),
                ("fg:ansibrightblack", " 세력  : "), (fc, f"{fname}\n"),
            ]
            if clue >= 2:
                lines.append(("", f" 수비  : {'★' * sel.defense_level}{'☆' * (10 - sel.defense_level)}"
                                   f"   병력 : {sel.garrison_strength * 200:,}\n"))
            else:
                lines.append(("fg:ansibrightblack", f" 수비  : {HIDDEN}   병력 : {HIDDEN}\n"))
            if clue >= 1:
                lines.append(("", f" 인구  : {sel.population:,}\n"))
            else:
                lines.append(("fg:ansibrightblack", f" 인구  : {HIDDEN}\n"))
            clue_bar = "■" * clue + "□" * (5 - clue)
            if sel_id != hero_town:
                lines.append(("fg:ansibrightblack", f" 단서  : {clue_bar}  {clue}/5\n"))
            lines.append(("fg:ansibrightgreen", " Enter → 상세 보기\n"))
            return lines

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
            open_detail[0] = towns[cursor[0]].id
            event.app.exit()

        @kb.add("escape")
        @kb.add("q")
        def _quit(event):
            open_detail[0] = None
            event.app.exit()

        layout = Layout(
            VSplit([
                Window(content=FormattedTextControl(left_text), width=28),
                Window(width=1, char="│"),
                Window(content=FormattedTextControl(map_text)),
            ])
        )

        # Loop: map browse → detail view → back to map
        while True:
            open_detail[0] = None
            Application(
                layout=layout,
                key_bindings=kb,
                full_screen=True,
                mouse_support=False,
            ).run()
            if open_detail[0] is None:
                break
            # Show detail then re-open map
            self.console.clear()
            self._show_town_detail(open_detail[0], state)


    # ------------------------------------------------------------------
    # Battle display helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hp_bar(current: int, maximum: int, width: int = 20, color: str = "cyan") -> str:
        if maximum <= 0:
            return "[grey50]" + "░" * width + "[/]"
        filled = int(width * current / maximum)
        bar = "█" * filled + "░" * (width - filled)
        pct = int(100 * current / maximum)
        return f"[{color}]{bar}[/] {pct:3d}%"

    @staticmethod
    def _morale_color(morale: int) -> str:
        if morale < 30:
            return "bold red"
        if morale < 60:
            return "yellow"
        if morale < 80:
            return "green"
        return "bold green"

    def _army_panel(self, army: Army, title: str, style: str = "blue") -> Panel:
        mc = self._morale_color(army.morale)
        unit_icons = {"infantry": "⚔️ 보병", "cavalry": "🐴 기병",
                      "archer": "🏹 궁병", "navy": "⚓ 수군"}
        icon = unit_icons.get(army.unit_type.value, "⚔️")
        content = (
            f"[bold]{army.name}[/]  {icon}\n"
            f"병력: {self._hp_bar(army.troops, army.max_troops, 18, 'cyan')}"
            f"  {army.troops:,}/{army.max_troops:,}\n"
            f"사기: [{mc}]{self._hp_bar(army.morale, 100, 18, mc)}  {army.morale}[/{mc}]\n"
            f"전투력: [bold yellow]{army.combat_power:.0f}[/]"
        )
        if army.catapults or army.siege_towers or army.battering_rams:
            content += (
                f"\n[dim]투석기:{army.catapults}  운제:{army.siege_towers}"
                f"  충차:{army.battering_rams}[/]"
            )
        return Panel(content, title=f"[bold]{title}[/]", style=style, padding=(0, 1))

    def _wall_panel(self, town: Town) -> Panel:
        integrity = town.wall_integrity()
        color = "green" if integrity > 0.5 else ("yellow" if integrity > 0.2 else "red")
        bar = self._hp_bar(town.wall_hp, town.max_wall_hp, 24, color)
        if integrity >= 0.9:
            wall_char = "████████████████████"
            wall_color = "bold white"
        elif integrity >= 0.6:
            wall_char = "████▓▓▓▓████▓▓▓▓████"
            wall_color = "bold yellow"
        elif integrity >= 0.3:
            wall_char = "██░░▓▓░░██░░▓▓░░██░░"
            wall_color = "yellow"
        else:
            wall_char = "░░░░▒▒░░░░▒▒░░░░▒▒░░"
            wall_color = "red"
        content = (
            f"  [{wall_color}]{wall_char}[/{wall_color}]\n"
            f"  [{wall_color}]{'  🏯  ' + town.name_ko + '  🏯':^20}[/{wall_color}]\n"
            f"  [{wall_color}]{wall_char}[/{wall_color}]\n\n"
            f"성벽 내구도: {bar}  {town.wall_hp}/{town.max_wall_hp}"
        )
        return Panel(content, title="[bold white]성벽[/bold white]", style="white", padding=(0, 1))

    def _battle_status_table(
        self,
        attacker: Army,
        defender: Army,
        att_label: str,
        def_label: str,
        town: Optional[Town] = None,
    ) -> Table:
        """Single-frame status table used inside Rich Live."""
        t = Table.grid(padding=(0, 2))
        t.add_column(min_width=42)
        t.add_column(min_width=42)
        if town:
            t.add_column(min_width=26)
            t.add_row(
                self._army_panel(attacker, att_label, "red"),
                self._army_panel(defender, def_label, "blue"),
                self._wall_panel(town),
            )
        else:
            t.add_row(
                self._army_panel(attacker, att_label, "red"),
                self._army_panel(defender, def_label, "blue"),
            )
        return t

    # ------------------------------------------------------------------
    # Recruit preview
    # ------------------------------------------------------------------

    def show_recruit_preview(
        self,
        hero: Hero,
        town: Town,
        recruit_count: int,
        cost: int,
        faction_gold: int,
    ) -> bool:
        """Preview panel before recruitment. Returns False if user cancels."""
        can_afford = faction_gold >= cost
        stat_bar = self._hp_bar(hero.leadership, 10, 16, "yellow")

        lines = [
            "",
            f"  [bold yellow]\u2605 \ud1b5\uc194\ub825[/]  {stat_bar}  [bold yellow]{hero.leadership}[/]",
            f"  [dim](\ubaa8\uc9d1 \uaddc\ubaa8 = \ud1b5\uc194\ub825 \xd7 100)[/]",
            "",
            "  " + "\u2500" * 36,
            f"  \ud604\uc7ac \ubcd1\ub825   [dim]{hero.current_army:,}\uba85[/]",
            f"  \ubaa8\uc9d1 \uc608\uc0c1   [bold green]+{recruit_count:,}\uba85[/]",
            f"  \uc608\uc0c1 \ud569\uacc4   [bold]{hero.current_army + recruit_count:,}\uba85[/]",
            "",
            (f"  \ube44\uc6a9  [bold red]-{cost} \uae08[/]  [dim](\ubcf4\uc720: {faction_gold:,})[/]  [bold red]\u274c \ubd80\uc871[/]"
             if not can_afford else
             f"  \ube44\uc6a9  [bold yellow]-{cost} \uae08[/]  [dim](\ubcf4\uc720: {faction_gold:,})[/]"),
        ]
        self.console.print(Panel(
            "\n".join(lines),
            title=f"[bold yellow]\ubaa8\ubcd1 \uc608\uc0c1 \u2014 {hero.name_ko}[/]",
            border_style="yellow",
            padding=(0, 1),
        ))
        if not can_afford:
            import questionary as _q
            _q.press_any_key_to_continue("[ \uc544\ubb34 \ud0a4 ] \ub3cc\uc544\uac00\uae30...").ask()
            return False
        import questionary as _q
        return bool(_q.confirm("  \ubaa8\ubcd1\ud558\uc2dc\uaca0\uc2b5\ub2c8\uae4c?", default=True, style=_STYLE).ask())

    # ------------------------------------------------------------------
    # Admin preview
    # ------------------------------------------------------------------

    def show_admin_preview(
        self,
        hero: Hero,
        town: Town,
        gain: int,
    ) -> bool:
        """Preview panel before admin action. Returns False if user cancels."""
        new_level = min(10, town.admin_level + gain)
        old_tax  = int(town.tax_yield  * town.admin_level / 5)
        new_tax  = int(town.tax_yield  * new_level / 5)
        old_food = int(town.food_yield * town.admin_level / 5)
        new_food = int(town.food_yield * new_level / 5)

        stat_bar = self._hp_bar(hero.intelligence, 10, 16, "cyan")

        def _adm_bar(val: float, width: int = 16) -> str:
            filled = int(round(val * width / 10))
            return "[yellow]" + "\u2588" * filled + "[/][dim]" + "\u2591" * (width - filled) + "[/]"

        lines = [
            "",
            f"  [bold cyan]\u2605 \uc9c0\ub825[/]  {stat_bar}  [bold cyan]{hero.intelligence}[/]",
            f"  [dim](\ub0b4\uc815 \uc0c1\uc2b9\ud3ed = \uc9c0\ub825 \xf7 4,  \ucd5c\uc18c +1)[/]",
            "",
            "  " + "\u2500" * 36,
            (f"  \ub0b4\uc815 \uc218\uc900  "
             f"{_adm_bar(town.admin_level)} [dim]{town.admin_level}[/]  \u2192  "
             f"{_adm_bar(new_level)} [bold yellow]{new_level}[/]  / 10"
             + (f"  [bold yellow](+{gain})[/]" if gain > 0 else "")),
            "",
            (f"  \uc138\uae08 \uc218\uc785  [dim]{old_tax}[/] \u2192 [bold green]{new_tax}[/] / \ud134"
             + (f"  [green](+{new_tax - old_tax})[/]" if new_tax > old_tax else "")),
            (f"  \uc2dd\ub7c9 \uc218\uc785  [dim]{old_food}[/] \u2192 [bold green]{new_food}[/] / \ud134"
             + (f"  [green](+{new_food - old_food})[/]" if new_food > old_food else "")),
        ]
        self.console.print(Panel(
            "\n".join(lines),
            title=f"[bold yellow]\ub0b4\uc815 \uac15\ud654 \uc608\uc0c1 \u2014 {hero.name_ko}[/]",
            border_style="yellow",
            padding=(0, 1),
        ))
        import questionary as _q
        return bool(_q.confirm("  \ub0b4\uc815\uc744 \uac15\ud654\ud558\uc2dc\uaca0\uc2b5\ub2c8\uae4c?", default=True, style=_STYLE).ask())

    # ------------------------------------------------------------------
    # Recruit animation
    # ------------------------------------------------------------------

    def show_recruit_animation(
        self,
        hero: Hero,
        town: Town,
        old_army: int,
        recruit_count: int,
        cost: int,
    ) -> None:
        """Animated troop counter ticking up during recruitment."""
        import questionary

        new_army = old_army + recruit_count
        steps = 12
        faction_name = town.name_ko

        def _frame(current: int) -> Table:
            bar = self._hp_bar(current, max(new_army, 1), 24, "cyan")
            t = Table.grid(padding=(0, 1))
            t.add_column()
            t.add_row(f"[bold cyan]{faction_name}[/] 모병 진행 중\n")
            t.add_row(
                f"[dim]병력[/]  {bar}"
                f"  [bold yellow]{current:,}[/][dim]/{new_army:,}명[/]\n"
            )
            t.add_row(
                f"[dim]증가[/]  [bold green]+{recruit_count:,}명[/]   "
                f"[dim]비용[/]  [bold red]-{cost}[/] 금\n"
            )
            return t

        with Live(console=self.console, refresh_per_second=20, transient=False) as live:
            for step in range(steps + 1):
                current = int(old_army + recruit_count * step / steps)
                live.update(
                    Panel(_frame(current),
                          title=f"[bold yellow]모병 — {hero.name_ko}[/]",
                          border_style="yellow", padding=(1, 2))
                )
                time.sleep(0.06)
            # Final flash: highlight the completed row
            live.update(
                Panel(_frame(new_army),
                      title="[bold green]모병 완료 ✓[/]",
                      border_style="bright_green", padding=(1, 2))
            )
            time.sleep(0.4)
        questionary.press_any_key_to_continue("[ 아무 키 ] 계속...").ask()

    # ------------------------------------------------------------------
    # Admin animation
    # ------------------------------------------------------------------

    def show_admin_animation(
        self,
        hero: Hero,
        town: Town,
        old_level: int,
        new_level: int,
    ) -> None:
        """Animated admin bar + income counters ticking up."""
        import questionary

        old_tax = int(town.tax_yield * old_level / 5)
        new_tax = int(town.tax_yield * new_level / 5)
        old_food = int(town.food_yield * old_level / 5)
        new_food = int(town.food_yield * new_level / 5)
        steps = 14

        def _admin_bar(val: float, width: int = 20) -> str:
            filled = int(round(val * width / 10))
            return "[yellow]" + "█" * filled + "[/][dim]" + "░" * (width - filled) + "[/]"

        def _frame(frac: float) -> Table:
            cur_level = old_level + (new_level - old_level) * frac
            cur_tax   = old_tax   + (new_tax   - old_tax)   * frac
            cur_food  = old_food  + (new_food  - old_food)  * frac
            t = Table.grid(padding=(0, 1))
            t.add_column()
            t.add_row(f"[bold cyan]{town.name_ko}[/] 내정 강화\n")
            t.add_row(
                f"내정 수준  {_admin_bar(cur_level)}"
                f"  [bold yellow]{cur_level:.1f}[/] / 10\n"
            )
            t.add_row(
                f"세금 수입  [dim]{old_tax}[/] → "
                f"[bold green]{int(cur_tax):,}[/] / 턴\n"
            )
            t.add_row(
                f"식량 수입  [dim]{old_food}[/] → "
                f"[bold green]{int(cur_food):,}[/] / 턴\n"
            )
            return t

        with Live(console=self.console, refresh_per_second=20, transient=False) as live:
            for step in range(steps + 1):
                frac = step / steps
                live.update(
                    Panel(_frame(frac),
                          title=f"[bold yellow]내정 강화 — {hero.name_ko}[/]",
                          border_style="yellow", padding=(1, 2))
                )
                time.sleep(0.07)
            # Final frame: exact values, green border flash
            live.update(
                Panel(_frame(1.0),
                      title="[bold green]내정 강화 완료 ✓[/]",
                      border_style="bright_green", padding=(1, 2))
            )
            time.sleep(0.4)
        questionary.press_any_key_to_continue("[ 아무 키 ] 계속...").ask()

    # ------------------------------------------------------------------
    # Step 1 — Combat location announcement
    # ------------------------------------------------------------------

    def show_battle_announcement(
        self,
        attacker_town_id: str,
        target_town_id: str,
        state: GameState,
    ) -> None:
        """Step 1: 어느 지역에서 전투가 일어나는지 지도와 함께 보여줌."""
        attacker_town = state.towns.get(attacker_town_id)
        target_town = state.towns.get(target_town_id)
        a_name = attacker_town.name_ko if attacker_town else attacker_town_id
        t_name = target_town.name_ko if target_town else target_town_id

        self.console.clear()
        self.console.print(Panel(
            f"[bold red]⚔️  공성전 발발![/]\n\n"
            f"  [cyan]{a_name}[/]  ━━▶  [bold yellow]{t_name}[/]\n\n"
            f"  [dim]{a_name} 주둔 병력이 {t_name}을(를) 공격합니다.[/]",
            title="[bold red]전투 선포[/]",
            border_style="red",
            padding=(1, 4),
        ))
        self.console.print()
        self._render_static_map(state, attacker_town_id, highlight_town_id=target_town_id)
        _pt_prompt("\n  [ Enter ] 전투 배치 확인으로 → ")

    # ------------------------------------------------------------------
    # Step 2 — Army deployment overview
    # ------------------------------------------------------------------

    def show_battle_deployment(
        self,
        attacker: Army,
        defender: Army,
        town: Town,
        attacker_general: Optional[Hero] = None,
        defender_general: Optional[Hero] = None,
    ) -> None:
        """Step 2: 군대 배치 개괄."""
        self.console.clear()
        self.console.rule("[bold yellow]⚔️  전투 배치[/]")
        self.console.print()

        # Generals row
        if attacker_general or defender_general:
            ag_name = f"[bold red]{attacker_general.name_ko}[/] 「{attacker_general.nickname}」" if attacker_general else "[dim]지휘관 없음[/]"
            dg_name = f"[bold blue]{defender_general.name_ko}[/] 「{defender_general.nickname}」" if defender_general else "[dim]지휘관 없음[/]"
            gen_table = Table.grid(padding=(0, 4))
            gen_table.add_column(min_width=40, justify="center")
            gen_table.add_column(min_width=40, justify="center")
            gen_table.add_row(
                Panel(ag_name, title="[bold]공격 지휘관[/]", border_style="red"),
                Panel(dg_name, title="[bold]수비 지휘관[/]", border_style="blue"),
            )
            self.console.print(gen_table)

        self.console.print(Columns([
            self._army_panel(attacker, "공격군", "red"),
            self._wall_panel(town),
            self._army_panel(defender, "수비군", "blue"),
        ]))
        self.console.print()
        _pt_prompt("  [ Enter ] 전투 시작 → ")

    # ------------------------------------------------------------------
    # Step 3 — Round-by-round animation callback
    # ------------------------------------------------------------------

    def make_round_callback(
        self,
        attacker: Army,
        defender: Army,
        town: Optional[Town],
    ):
        """
        Returns a callback(BattleRoundData) that animates the round in-place
        using Rich Live, then waits for Enter.
        """
        console = self.console

        def _on_round(rd: BattleRoundData) -> None:
            phase_label = {
                "bombardment": "💣 포격 단계",
                "assault":     f"⚔️  {rd.round_num}라운드 돌격",
                "field":       f"⚔️  {rd.round_num}라운드",
            }.get(rd.phase, f"라운드 {rd.round_num}")

            console.clear()
            console.rule(f"[bold white]{phase_label}[/]")
            console.print()

            # ── Animated gauge update (빠른 롤링, 0.5s) ──────────────────
            steps = 8
            with Live(console=console, refresh_per_second=12) as live:
                for step in range(steps + 1):
                    frac = step / steps
                    # Interpolate troop/morale between before→after
                    a_tr = int(rd.att_troops_before + (rd.att_troops_after - rd.att_troops_before) * frac)
                    a_mo = int(rd.att_morale_before + (rd.att_morale_after - rd.att_morale_before) * frac)
                    d_tr = int(rd.def_troops_before + (rd.def_troops_after - rd.def_troops_before) * frac)
                    d_mo = int(rd.def_morale_before + (rd.def_morale_after - rd.def_morale_before) * frac)

                    # Build temporary army snapshots for the panel
                    a_snap = attacker.model_copy(update={"troops": max(0, a_tr), "morale": max(0, a_mo)})
                    d_snap = defender.model_copy(update={"troops": max(0, d_tr), "morale": max(0, d_mo)})

                    if town is not None:
                        w_hp  = int(rd.wall_hp_before + (rd.wall_hp_after - rd.wall_hp_before) * frac)
                        t_snap = town.model_copy(update={"wall_hp": max(0, w_hp)})
                        frame = self._battle_status_table(a_snap, d_snap, "공격군 ⚔️", f"수비군 🛡  ({town.name_ko})", t_snap)
                    else:
                        frame = self._battle_status_table(a_snap, d_snap, "공격군 ⚔️", "수비군 🛡")

                    live.update(frame)
                    time.sleep(0.06)

            # ── Round events ─────────────────────────────────────────────
            console.print()
            for ev in rd.events:
                console.print(f"  [yellow]{ev}[/]")
            console.print()
            _pt_prompt("  [ Enter ] 다음 라운드 → ")

        return _on_round

    # ------------------------------------------------------------------
    # Step 4 — Battle result screen
    # ------------------------------------------------------------------

    def show_battle_result(
        self,
        result: BattleResult,
        attacker: Army,
        defender: Army,
        town: Town,
    ) -> None:
        """Step 4: 전투 결과."""
        won = result.winner == attacker.faction_id
        self.console.clear()
        self.console.rule("[bold white]⚔️  전투 결과[/]")
        self.console.print()

        # Final army status
        self.console.print(Columns([
            self._army_panel(
                attacker,
                f"{'✅ 승리' if won else '❌ 패배'} — {attacker.name}",
                "green" if won else "red",
            ),
            self._army_panel(
                defender,
                f"{'❌ 패배' if won else '✅ 승리'} — {defender.name}",
                "red" if won else "green",
            ),
        ]))
        self.console.print()

        # Summary panel
        if won:
            result_text = (
                f"[bold green]✅ 공성전 승리![/]\n\n"
                f"  [bold]{attacker.name}[/]이(가) [bold yellow]{town.name_ko}[/]을(를) 점령했다!\n\n"
                f"  공격군 손실: [red]{result.attacker_losses:,}명[/]   "
                f"수비군 손실: [cyan]{result.defender_losses:,}명[/]   "
                f"성벽 피해: [yellow]{result.wall_damage} HP[/]\n"
                f"  전투 라운드: {result.turns_fought}"
            )
            style = "green"
        else:
            result_text = (
                f"[bold red]❌ 공성전 실패![/]\n\n"
                f"  [bold]{attacker.name}[/]이(가) [bold yellow]{town.name_ko}[/] 점령에 실패했다.\n\n"
                f"  공격군 손실: [red]{result.attacker_losses:,}명[/]   "
                f"수비군 손실: [cyan]{result.defender_losses:,}명[/]   "
                f"성벽 피해: [yellow]{result.wall_damage} HP[/]\n"
                f"  전투 라운드: {result.turns_fought}"
            )
            style = "red"
        self.console.print(Panel(result_text, title="[bold]전투 결과[/]", border_style=style, padding=(1, 4)))
        self.console.print()
        _pt_prompt("  [ Enter ] 지도로 돌아가기 → ")

    # ------------------------------------------------------------------
    # Step 5 — Post-battle map highlight
    # ------------------------------------------------------------------

    def show_battle_map_update(
        self,
        town_id: str,
        old_faction_id: Optional[str],
        new_faction_id: str,
        state: GameState,
        captured: bool,
    ) -> None:
        """Step 5: 점령 결과를 지도에서 시각적으로 보여줌."""
        town = state.towns.get(town_id)
        t_name = town.name_ko if town else town_id

        old_faction = state.factions.get(old_faction_id or "")
        new_faction = state.factions.get(new_faction_id)
        old_name = old_faction.name_ko if old_faction else (old_faction_id or "미점령")
        new_name = new_faction.name_ko if new_faction else new_faction_id

        self.console.clear()
        if captured:
            self.console.print(Panel(
                f"[bold yellow]{t_name}[/] 점령!\n\n"
                f"  [dim]{old_name}[/]  ➜  [bold green]{new_name}[/]",
                title="[bold green]영토 변화[/]",
                border_style="green",
                padding=(1, 4),
            ))
        else:
            self.console.print(Panel(
                f"[bold yellow]{t_name}[/] 수성 성공\n\n"
                f"  [bold cyan]{old_name}[/] 지속 통제",
                title="[bold cyan]영토 유지[/]",
                border_style="cyan",
                padding=(1, 4),
            ))
        self.console.print()

        # Blink highlight on map (3 flashes)
        player_hero = state.get_player_hero()
        hero_town = player_hero.current_town if player_hero else town_id
        for flash in range(6):
            self.console.clear()
            if flash % 2 == 0:
                self._render_static_map(state, hero_town, highlight_town_id=town_id)
            else:
                self._render_static_map(state, hero_town)
            time.sleep(0.35)

        self.console.clear()
        self._render_static_map(state, hero_town, highlight_town_id=town_id)
        self.console.print()
        _pt_prompt("  [ Enter ] 계속 → ")

    # ------------------------------------------------------------------
    # Legacy compat wrappers (kept for any AI-path callers)
    # ------------------------------------------------------------------

    def show_combat_preview(self, hero_town_id: str, target_town_id: str, state: GameState) -> None:
        """Redirects to step-1 announcement."""
        self.show_battle_announcement(hero_town_id, target_town_id, state)

    def show_faction_change_animation(
        self,
        town_id: str,
        old_faction_id: str,
        new_faction_id: str,
        state: GameState,
    ) -> None:
        """Redirects to step-5 map update."""
        self.show_battle_map_update(town_id, old_faction_id, new_faction_id, state, captured=True)
