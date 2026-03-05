from __future__ import annotations

from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt

from models.game_state import GameState
from models.hero import Hero
from models.town import Town


class TerminalUI:
    """Rich-based terminal user interface."""

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
        table.add_column("ID", style="cyan")
        table.add_column("이름", style="bold")
        table.add_column("별명", style="magenta")
        table.add_column("세력", style="green")
        table.add_column("무력", justify="right")
        table.add_column("지력", justify="right")
        table.add_column("통솔", justify="right")

        for h in heroes:
            table.add_row(
                h.id, h.name_ko, h.nickname, h.faction_id,
                str(h.strength), str(h.intelligence), str(h.leadership)
            )
        self.console.print(table)
        
        while True:
            choice = Prompt.ask("플레이할 영웅의 ID를 입력하세요", choices=[h.id for h in heroes])
            return next(h for h in heroes if h.id == choice)

    def show_turn_header(self, state: GameState) -> None:
        self.console.rule(f"[bold yellow]제 {state.turn} 턴 (남은 턴: {state.turns_remaining()})[/]")
        
        # Show Faction Status
        if state.player_ids:
            # Assuming player 1's hero faction
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
        self.console.print(f"\n[bold cyan]{hero.name_ko}[/] (위치: {town.name_ko}, 병력: {hero.current_army}, AP: {hero.action_points})")
        
        choices = ["move", "investigate", "recruit", "siege", "rest", "end"]
        return Prompt.ask("행동을 선택하세요", choices=choices)

    def choose_destination(self, hero: Hero, town: Town, state: GameState) -> Optional[str]:
        table = Table(title=f"{town.name_ko} 인접 지역")
        table.add_column("ID", style="cyan")
        table.add_column("이름", style="bold")
        table.add_column("지배 세력", style="green")

        for adj_id in town.adjacent:
            adj_town = state.towns[adj_id]
            faction_name = state.factions[adj_town.controlled_by_faction].name_ko if adj_town.controlled_by_faction else "중립"
            table.add_row(adj_id, adj_town.name_ko, faction_name)
        
        self.console.print(table)
        choice = Prompt.ask("이동할 지역 ID (취소: c)", choices=town.adjacent + ["c"])
        return None if choice == "c" else choice

    def show_message(self, message: str) -> None:
        self.console.print(message)

    def show_setup_complete(self, state: GameState, hero: Hero) -> None:
        self.console.print(f"\n[bold green]게임 준비 완료![/] {hero.name_ko}의 여정이 {state.towns[hero.current_town].name_ko}에서 시작됩니다.")

    def show_game_over(self, state: GameState) -> None:
        if state.phase == "won":
            self.console.print(Panel.fit("[bold yellow]축하합니다! 천하를 평정하고 새로운 질서를 세웠습니다![/]", title="승리"))
        else:
            self.console.print(Panel.fit("[bold red]송나라가 멸망하고 중원이 혼란에 빠졌습니다...[/]", title="패배"))
