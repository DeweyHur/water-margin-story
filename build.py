#!/usr/bin/env python
"""
게임 개발 크루 실행 진입점

사용법:
    python build.py                  # 화살표 메뉴
    python build.py "요청 내용"       # 기능 개발
    python build.py test             # 스모크 테스트
"""
from __future__ import annotations

import sys
from pathlib import Path

import questionary
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

load_dotenv()

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from dev_crew.crew import DevMode, GameDevCrew
from config.llm_config import llm_available

console = Console()

EXAMPLES = [
    "영웅 클래스별 특수 스킬 시스템 추가",
    "전투 시스템 개선: 방어·회피 메커니즘 추가",
    "고구 도주 AI 개선: BFS 경로 탐색 적용",
    "세이브/로드 기능 구현",
    "전투 결과를 Rich Panel로 화려하게 표시",
    "새 랜덤 이벤트 10개 추가 (수호지 고사 기반)",
]

_STYLE = questionary.Style([
    ("qmark",       "fg:#ffcc00 bold"),
    ("question",    "bold"),
    ("answer",      "fg:#00cc88 bold"),
    ("pointer",     "fg:#ffcc00 bold"),
    ("highlighted", "fg:#ffcc00 bold"),
    ("selected",    "fg:#00cc88"),
])


def run_interactive() -> None:
    console.print(
        Panel(
            "[bold yellow]Water Margin Story — 게임 개발 크루[/]\n"
            "에이전트들이 직접 게임을 개발합니다.",
            border_style="cyan",
        )
    )

    if not llm_available():
        console.print("[red]API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.[/]")
        return

    while True:
        action = questionary.select(
            "메뉴를 선택하세요",
            choices=["[1] 개발", "[2] 스모크 테스트", "[0] 종료"],
            style=_STYLE,
        ).ask()

        if action is None or "[0]" in action:
            console.print("[dim]종료합니다.[/]")
            break

        if "[2]" in action:
            console.rule("[bold green]스모크 테스트 시작[/]")
            crew = GameDevCrew()
            try:
                result = crew.run(mode=DevMode.TEST)
                console.rule("[bold green]완료[/]")
                console.print(Panel(result, title="결과", border_style="green"))
            except Exception as e:
                console.print(f"[red]오류: {e}[/]")

        elif "[1]" in action:
            console.print("\n[dim]요청 예시:[/]")
            for ex in EXAMPLES:
                console.print(f"  [dim]• {ex}[/]")

            request = questionary.text(
                "개발 요청을 입력하세요",
                style=_STYLE,
            ).ask()

            if not request or not request.strip():
                console.print("[red]요청 내용을 입력해야 합니다.[/]")
                continue

            console.rule("[bold green]개발 크루 작업 시작[/]")
            crew = GameDevCrew()
            try:
                result = crew.run(request=request.strip(), mode=DevMode.FEATURE)
                console.rule("[bold green]작업 완료[/]")
                console.print(Panel(result, title="최종 결과", border_style="green"))
            except Exception as e:
                console.print(f"[red]오류 발생: {e}[/]")

        again = questionary.select(
            "계속하시겠습니까?",
            choices=["[y] 계속", "[n] 종료"],
            style=_STYLE,
        ).ask()
        if again is None or "[n]" in again:
            console.print("[dim]종료합니다.[/]")
            break


def run_cli(args: list[str]) -> None:
    if not llm_available():
        console.print("[red]API_KEY 미설정[/]")
        sys.exit(1)

    first = args[0].lower()
    crew = GameDevCrew()

    if first == "test":
        result = crew.run(mode=DevMode.TEST)
    else:
        request = " ".join(args)
        result = crew.run(request=request, mode=DevMode.FEATURE)

    console.print(Panel(result, title="결과", border_style="green"))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_cli(sys.argv[1:])
    else:
        run_interactive()
