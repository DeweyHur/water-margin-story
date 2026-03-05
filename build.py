#!/usr/bin/env python
"""
게임 개발 크루 실행 진입점
────────────────────────
에이전트들이 Water Margin Story 게임을 직접 개발한다.

사용법:
    python build.py                          # 대화형 메뉴
    python build.py feature "전투 스킬 추가"  # 기능 개발
    python build.py content "새 이벤트 10개"  # 컨텐츠 생성
    python build.py review                   # 코드 리뷰
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

load_dotenv()

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from dev_crew.crew import DevMode, GameDevCrew
from config.llm_config import llm_available

console = Console()

MENU = """
[bold cyan]게임 개발 크루 메뉴[/]

  [1] 기능 개발   — 새 기능 기획·구현·리뷰 (디자이너 + 개발자 + 리뷰어)
  [2] 컨텐츠 생성 — 이벤트/영웅/마을 추가 (스토리텔러)
  [3] 코드 리뷰   — 현재 코드베이스 품질 검토 (리뷰어)
  [0] 종료
"""

EXAMPLES = {
    "1": [
        "영웅 클래스별 특수 스킬 시스템 추가",
        "전투 시스템 개선: 방어·회피 메커니즘 추가",
        "고구 도주 AI 개선: BFS 경로 탐색 적용",
        "세이브/로드 기능 구현",
        "영웅 간 동맹 시스템 추가",
    ],
    "2": [
        "새 랜덤 이벤트 10개 추가 (수호지 고사 기반)",
        "새 영웅 5명 추가 (천살성 호한 중심)",
        "새 마을 3개 추가 (북송 남부 지역)",
    ],
}


def print_examples(mode_key: str) -> None:
    examples = EXAMPLES.get(mode_key, [])
    if examples:
        console.print("\n[dim]요청 예시:[/]")
        for ex in examples:
            console.print(f"  [dim]• {ex}[/]")


def run_interactive() -> None:
    console.print(
        Panel(
            "[bold yellow]Water Margin Story — 게임 개발 크루[/]\n"
            "Gemini 에이전트들이 직접 게임을 개발합니다.",
            border_style="cyan",
        )
    )

    if not llm_available():
        console.print("[red]⚠  GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.[/]")
        return

    while True:
        console.print(MENU)
        choice = Prompt.ask("선택", choices=["0", "1", "2", "3"], default="0")

        if choice == "0":
            console.print("[dim]종료합니다.[/]")
            break

        mode_map = {"1": DevMode.FEATURE, "2": DevMode.CONTENT, "3": DevMode.REVIEW}
        mode = mode_map[choice]
        request = ""

        if choice in ("1", "2"):
            print_examples(choice)
            request = Prompt.ask("\n개발 요청 내용을 입력하세요")
            if not request.strip():
                console.print("[red]요청 내용을 입력해야 합니다.[/]")
                continue

        console.rule("[bold green]개발 크루 작업 시작[/]")
        crew = GameDevCrew()

        try:
            result = crew.run(request=request, mode=mode)
            console.rule("[bold green]작업 완료[/]")
            console.print(Panel(result, title="최종 결과", border_style="green"))
        except Exception as e:
            console.print(f"[red]오류 발생: {e}[/]")

        again = Prompt.ask("\n계속하시겠습니까?", choices=["y", "n"], default="y")
        if again == "n":
            break


def run_cli(args: list[str]) -> None:
    if not llm_available():
        console.print("[red]GEMINI_API_KEY 미설정[/]")
        sys.exit(1)

    mode_str = args[0].lower()
    request = " ".join(args[1:])

    mode_map = {"feature": DevMode.FEATURE, "content": DevMode.CONTENT, "review": DevMode.REVIEW}
    if mode_str not in mode_map:
        console.print(f"[red]알 수 없는 모드: {mode_str}[/]")
        console.print("사용 가능한 모드: feature, content, review")
        sys.exit(1)

    crew = GameDevCrew()
    result = crew.run(request=request, mode=mode_map[mode_str])
    console.print(Panel(result, title="결과", border_style="green"))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_cli(sys.argv[1:])
    else:
        run_interactive()
