"""게임 개발 크루 태스크 빌더."""
from __future__ import annotations

from crewai import Agent, Task

# 에이전트에게 전달할 현재 프로젝트 구조 요약 (디렉토리 탐색 최소화)
_PROJECT_SUMMARY = """\
## 현재 프로젝트 구조
```
models/hero.py       → Hero(Pydantic) : id, name_ko, name_zh, nickname, hero_class, strength, intelligence, agility, reputation, current_town, hp, max_hp, action_points, is_player_controlled, player_id
models/town.py       → Town: id, name_ko, adjacent(list[str]), gao_qiu_presence, clue_level, garrison_strength
models/game_state.py → GameState: turn, max_turns, heroes(dict), towns(dict), gao_qiu_location, dynasty_stability, winner_id, player_ids
models/event.py      → GameEvent, EventType(enum)
game/engine.py       → GameEngine: run(), _setup(), _process_turn(), _final_battle()
game/turn_manager.py → TurnManager: player_turn(), ai_turn(), _do_investigate(), _do_rest()
game/event_system.py → EventSystem: fire_dynasty_events(), fire_random_events()
config/heroes.yaml   → 8명 영웅 설정
config/towns.yaml    → 9개 마을 설정 (liangshan, bianjing 등)
config/events.yaml   → random_events, dynasty_events
ui/terminal_ui.py    → Rich 기반 터미널 UI
agents/              → crewAI NPC 에이전트 (gao_qiu, hero, advisor)
tools/               → MovementTool, CombatTool, InvestigationTool
```
주요 파일은 FileReadTool로 직접 읽어 내용을 확인하라.
"""


def design_feature_task(feature_request: str, designer: Agent) -> Task:
    """게임 디자이너가 기능 스펙을 작성하는 태스크."""
    return Task(
        description=(
            f"{_PROJECT_SUMMARY}\n"
            f"## 기능 요청\n{feature_request}\n\n"
            "## 작업 지시\n"
            "1. 필요한 파일을 FileReadTool로 읽어 기존 코드 구조를 파악하라.\n"
            "2. 요청된 기능의 상세 설계 문서를 작성하라:\n"
            "   - 기능 개요 및 목적\n"
            "   - 영향받는 파일/모듈 목록\n"
            "   - 새로운 Pydantic 모델 또는 YAML 필드 정의\n"
            "   - 게임 밸런스 수치 (해당 시)\n"
            "   - 구현 순서 및 우선순위\n"
            "3. 멀티플레이어 확장성을 고려한 설계를 포함하라.\n"
        ),
        expected_output=(
            "구조화된 기능 설계 문서 (마크다운 형식).\n"
            "영향받는 파일 목록과 각 파일의 변경 사항 요약 포함."
        ),
        agent=designer,
    )


def implement_feature_task(feature_request: str, developer: Agent) -> Task:
    """게임 개발자가 코드를 구현하는 태스크."""
    return Task(
        description=(
            f"{_PROJECT_SUMMARY}\n"
            f"## 구현 대상\n{feature_request}\n\n"
            "## 작업 지시\n"
            "1. 위 프로젝트 구조를 참고하여 FileReadTool로 관련 파일을 읽어라.\n"
            "2. 이전 에이전트(게임 디자이너)의 설계에 따라 구현하라.\n"
            "3. 코드 작성 규칙:\n"
            "   - Python 3.11+, 타입 힌트 필수\n"
            "   - Pydantic v2 모델 사용 (BaseModel, Field)\n"
            "   - from __future__ import annotations 포함\n"
            "   - 기존 import 경로 그대로 사용\n"
            "4. 모든 변경/신규 파일을 FileWriterTool로 저장하라.\n"
            "5. 변경된 파일 목록과 각 변경 이유를 요약하라.\n"
        ),
        expected_output=(
            "구현 완료 보고서:\n"
            "- 생성/수정된 파일 목록\n"
            "- 각 파일의 주요 변경 사항\n"
            "- 실행 방법 (해당 시)\n"
            "- 알려진 제한 사항 또는 추가 작업 필요 항목"
        ),
        agent=developer,
    )


def generate_content_task(content_request: str, storyteller: Agent) -> Task:
    """스토리텔러가 게임 컨텐츠를 생성하는 태스크."""
    return Task(
        description=(
            f"## 컨텐츠 요청\n{content_request}\n\n"
            "## 작업 지시\n"
            "1. 기존 config/events.yaml, config/heroes.yaml, config/towns.yaml을 읽어라.\n"
            "2. 동일한 YAML 포맷으로 새 컨텐츠를 작성하라.\n"
            "3. 수호지 세계관에 충실하고, 한국어로 작성하라.\n"
            "4. 게임 밸런스를 해치지 않는 수치를 사용하라.\n"
            "5. 생성된 컨텐츠를 적절한 파일에 추가하거나 새 파일로 저장하라.\n"
        ),
        expected_output=(
            "YAML 형식의 게임 컨텐츠 (바로 설정 파일에 붙여넣기 가능한 형태).\n"
            "각 항목에 대한 간단한 설명 포함."
        ),
        agent=storyteller,
    )


def review_code_task(reviewer: Agent) -> Task:
    """코드 리뷰어가 최종 결과물을 검토하는 태스크."""
    return Task(
        description=(
            "## 코드 리뷰 지시\n"
            "이번 개발 세션에서 생성/수정된 코드를 검토하라.\n\n"
            "1. 다음 항목을 확인하라:\n"
            "   - import 경로가 올바른가?\n"
            "   - Pydantic v2 문법을 따르는가?\n"
            "   - 타입 힌트가 올바른가?\n"
            "   - 엣지케이스 처리가 있는가?\n"
            "   - GameState 직렬화 호환성을 유지하는가?\n"
            "2. 버그나 문제점이 있으면 수정 코드를 제시하라.\n"
            "3. 전체 품질 평가 (1-10점)와 종합 의견을 작성하라.\n"
        ),
        expected_output=(
            "코드 리뷰 보고서:\n"
            "- 발견된 문제점 목록 (파일명, 라인, 설명)\n"
            "- 수정 제안 코드 스니펫\n"
            "- 전체 품질 점수 및 종합 의견"
        ),
        agent=reviewer,
    )
