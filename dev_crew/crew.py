"""게임 개발 크루 — crewAI Crew 조립 및 실행."""
from __future__ import annotations

import subprocess
import sys
from enum import Enum
from pathlib import Path

from crewai import Crew, Process

from dev_crew.agents import (
    game_designer, game_developer, storyteller, code_reviewer,
    game_tester, ui_designer, ui_developer, project_manager,
)
from dev_crew.tasks import (
    design_feature_task,
    implement_feature_task,
    generate_content_task,
    review_code_task,
    developer_fix_from_tester_task,
    developer_fix_from_review_task,
    developer_implement_for_content_task,
    review_content_quality_task,
    SMOKE_TESTS,
    make_fix_from_failures_task,
    design_ui_task,
    implement_ui_task,
)


class DevMode(str, Enum):
    FEATURE = "feature"       # 새 기능 기획 + 구현 + 리뷰
    CONTENT = "content"       # 이벤트/영웅/마을 컨텐츠 생성
    REVIEW = "review"         # 기존 코드 리뷰만
    TEST = "test"             # 자율 스모크 테스트 + 버그 픽스
    UI = "ui"                 # UI/UX 개선 (ui/terminal_ui.py 전용)


class GameDevCrew:
    """
    Water Margin Story 게임 개발 자동화 크루.

    사용 예시:
        crew = GameDevCrew()
        result = crew.run("전투 시스템: 영웅 클래스별 특수 스킬 추가")
        result = crew.run("새 랜덤 이벤트 10개 추가", mode=DevMode.CONTENT)
        result = crew.run(mode=DevMode.REVIEW)
    """

    def run(self, request: str = "", mode: DevMode = DevMode.FEATURE) -> str:
        if mode == DevMode.FEATURE:
            return self._run_feature(request)
        elif mode == DevMode.CONTENT:
            return self._run_content(request)
        elif mode == DevMode.REVIEW:
            return self._run_review()
        elif mode == DevMode.TEST:
            return self._run_test()
        elif mode == DevMode.UI:
            return self._run_ui(request)
        raise ValueError(f"Unknown mode: {mode}")

    # ------------------------------------------------------------------
    # Feature development: design → implement → review
    # ------------------------------------------------------------------

    def _run_feature(self, request: str) -> str:
        manager = project_manager()
        designer = game_designer()
        developer = game_developer()
        reviewer = code_reviewer()

        design_task = design_feature_task(request, designer)
        impl_task = implement_feature_task(request, developer)
        impl_task.context = [design_task]
        review_task = review_code_task(reviewer)
        review_task.context = [impl_task]

        crew = Crew(
            agents=[designer, developer, reviewer],
            tasks=[design_task, impl_task, review_task],
            process=Process.hierarchical,
            manager_agent=manager,
            verbose=True,
            memory=False,
        )
        result = crew.kickoff()
        return str(result)

    # ------------------------------------------------------------------
    # Content generation: storyteller → developer → reviewer
    # ------------------------------------------------------------------

    def _run_content(self, request: str) -> str:
        manager = project_manager()
        writer = storyteller()
        developer = game_developer()
        reviewer = code_reviewer()

        content_task = generate_content_task(request, writer)
        impl_task = developer_implement_for_content_task(developer)
        impl_task.context = [content_task]
        review_task = review_content_quality_task(reviewer)
        review_task.context = [content_task, impl_task]

        crew = Crew(
            agents=[writer, developer, reviewer],
            tasks=[content_task, impl_task, review_task],
            process=Process.hierarchical,
            manager_agent=manager,
            verbose=True,
        )
        result = crew.kickoff()
        return str(result)

    # ------------------------------------------------------------------
    # Code review: reviewer → developer fixes
    # ------------------------------------------------------------------

    def _run_review(self) -> str:
        manager = project_manager()
        reviewer = code_reviewer()
        developer = game_developer()

        review_task = review_code_task(reviewer)
        fix_task = developer_fix_from_review_task(developer)
        fix_task.context = [review_task]

        crew = Crew(
            agents=[reviewer, developer],
            tasks=[review_task, fix_task],
            process=Process.hierarchical,
            manager_agent=manager,
            verbose=True,
        )
        result = crew.kickoff()
        return str(result)

    # ------------------------------------------------------------------
    # UI development: ui_designer → ui_developer
    # ------------------------------------------------------------------

    def _run_ui(self, request: str) -> str:
        manager = project_manager()
        designer = ui_designer()
        developer = ui_developer()

        design_task = design_ui_task(request, designer)
        impl_task = implement_ui_task(request, developer)
        impl_task.context = [design_task]

        crew = Crew(
            agents=[designer, developer],
            tasks=[design_task, impl_task],
            process=Process.hierarchical,
            manager_agent=manager,
            verbose=True,
            memory=False,
        )
        result = crew.kickoff()
        return str(result)

    # ------------------------------------------------------------------
    # Smoke test: run tests in Python directly, agent only fixes failures
    # ------------------------------------------------------------------

    def _run_test(self) -> str:
        _PYTHON = str(Path(__file__).parent.parent / ".venv" / "bin" / "python")
        if not Path(_PYTHON).exists():
            _PYTHON = sys.executable
        _ROOT = str(Path(__file__).parent.parent)
        _PREAMBLE = (
            f"import sys, os\n"
            f"sys.path.insert(0, {_ROOT!r})\n"
            f"os.chdir({_ROOT!r})\n"
            "from dotenv import load_dotenv; load_dotenv()\n"
        )

        failures: list[str] = []
        lines: list[str] = []
        for name, code in SMOKE_TESTS:
            r = subprocess.run(
                [_PYTHON, "-c", _PREAMBLE + code],
                capture_output=True, text=True,
            )
            ok = "PASS" in r.stdout
            status = "PASS" if ok else "FAIL"
            lines.append(f"[{status}] {name}")
            print(f"  {lines[-1]}")
            if not ok:
                detail = (r.stdout + r.stderr).strip()[-600:]
                failures.append(f"[{name}]\n{detail}")

        report = "\n".join(lines)
        print(report)

        if not failures:
            return "모든 스모크 테스트 통과.\n" + report

        failure_report = "\n\n".join(failures)
        developer = game_developer()
        fix_task = make_fix_from_failures_task(failure_report, developer)

        crew = Crew(
            agents=[developer],
            tasks=[fix_task],
            process=Process.sequential,
            verbose=True,
        )
        result = crew.kickoff()
        return str(result)
