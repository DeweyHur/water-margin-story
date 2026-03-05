"""게임 개발 크루 — crewAI Crew 조립 및 실행."""
from __future__ import annotations

from enum import Enum

from crewai import Crew, Process

from dev_crew.agents import game_designer, game_developer, storyteller, code_reviewer
from dev_crew.tasks import (
    design_feature_task,
    implement_feature_task,
    generate_content_task,
    review_code_task,
)


class DevMode(str, Enum):
    FEATURE = "feature"       # 새 기능 기획 + 구현 + 리뷰
    CONTENT = "content"       # 이벤트/영웅/마을 컨텐츠 생성
    REVIEW = "review"         # 기존 코드 리뷰만


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
        raise ValueError(f"Unknown mode: {mode}")

    # ------------------------------------------------------------------
    # Feature development: design → implement → review
    # ------------------------------------------------------------------

    def _run_feature(self, request: str) -> str:
        designer = game_designer()
        developer = game_developer()
        reviewer = code_reviewer()

        design_task = design_feature_task(request, designer)
        impl_task = implement_feature_task(request, developer)
        # impl_task reads the design from context of previous task
        impl_task.context = [design_task]
        review_task = review_code_task(reviewer)
        review_task.context = [impl_task]

        crew = Crew(
            agents=[designer, developer, reviewer],
            tasks=[design_task, impl_task, review_task],
            process=Process.sequential,
            verbose=True,
            memory=False,
            max_rpm=4,   # free tier 12k TPM: 4 RPM + max_tokens 한도로 TPM 초과 방지
        )
        result = crew.kickoff()
        return str(result)

    # ------------------------------------------------------------------
    # Content generation: storyteller only
    # ------------------------------------------------------------------

    def _run_content(self, request: str) -> str:
        writer = storyteller()
        content_task = generate_content_task(request, writer)

        crew = Crew(
            agents=[writer],
            tasks=[content_task],
            process=Process.sequential,
            verbose=True,
            max_rpm=8,
        )
        result = crew.kickoff()
        return str(result)

    # ------------------------------------------------------------------
    # Code review only
    # ------------------------------------------------------------------

    def _run_review(self) -> str:
        reviewer = code_reviewer()
        review_task = review_code_task(reviewer)

        crew = Crew(
            agents=[reviewer],
            tasks=[review_task],
            process=Process.sequential,
            verbose=True,
            max_rpm=8,
        )
        result = crew.kickoff()
        return str(result)
