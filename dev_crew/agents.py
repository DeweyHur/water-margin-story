"""게임 개발 크루 에이전트 정의."""
from __future__ import annotations

from crewai import Agent

from config.llm_config import (
    get_design_llm, get_code_llm, get_review_llm,
    get_groq_tool_llm, get_manager_llm,
)
from tools.python_runner_tool import PythonRunnerTool
from tools.file_tools import SimpleFileReadTool, SimpleFileWriteTool, PatchProjectFileTool

_python_runner = PythonRunnerTool()
_file_read = SimpleFileReadTool()
_file_write = SimpleFileWriteTool()
_file_patch = PatchProjectFileTool()


def project_manager() -> Agent:
    """수석 매니저 — 70B 요사, 위임·검수 전담. 도구 없음, 위임만."""
    return Agent(
        role="수석 프로젝트 매니저",
        goal=(
            "디렉터의 요청을 파악하고 하위 에이전트에게 업무를 배분한다. "
            "최종 결과물이 디렉터의 의도를 100% 이행했는지 확인 후 승인한다. "
            "조금이라도 누락되면 반려하고 수정을 요청한다."
        ),
        backstory=(
            "완벽주의자 수석 매니저로, 비서실장어를 출걸한 듯한 지휘 능력을 갖춤다. "
            "Water Margin Story 코드베이스와 제코마역할을 깊이 이해하며 "
            "응답이 요구사항을 충족하지 못하면 절대 주그리지 않는다."
        ),
        tools=[],
        llm=get_manager_llm(),
        verbose=True,
        allow_delegation=True,
        max_iter=6,
    )


def game_designer() -> Agent:
    """기능 기획 및 게임 밸런스 설계 전담 에이전트."""
    return Agent(
        role="게임 디자이너",
        goal=(
            "Water Margin Story의 게임 기획을 담당한다. "
            "요청받은 기능의 상세 스펙, 밸런스 수치, 데이터 구조 설계를 작성한다. "
            "수호지 세계관과 기존 코드베이스를 참고해 일관성 있는 설계를 한다."
        ),
        backstory=(
            "전략 RPG 전문 게임 디자이너로, 수호지 고전 소설에 깊은 이해를 갖고 있다. "
            "Pydantic 모델과 YAML 설정 중심의 아키텍처에 익숙하다. "
            "항상 멀티플레이어 확장성을 염두에 두고 설계한다."
        ),
        tools=[_file_read, _file_write],
        llm=get_groq_tool_llm(temperature=0.5),
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )


def game_developer() -> Agent:
    """Python 코드 구현 전담 에이전트."""
    return Agent(
        role="게임 개발자",
        goal=(
            "게임 디자이너의 스펙을 바탕으로 프로덕션 수준의 Python 코드를 작성한다. "
            "기존 코드베이스 스타일(Pydantic v2, crewAI, Rich, 타입 힌트)을 따른다. "
            "완전히 동작하는 코드를 파일에 저장하고, python_runner로 직접 실행해 검증한다."
        ),
        backstory=(
            "Python 전문 개발자로 crewAI, Pydantic, Rich 라이브러리에 능숙하다. "
            "클린 코드, 단일 책임 원칙, 테스트 가능한 설계를 중시한다. "
            "코드를 저장한 뒤 반드시 python_runner로 import 및 기본 동작을 확인한다."
        ),
        tools=[_file_read, _file_write, _file_patch, _python_runner],
        llm=get_code_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=15,
    )


def storyteller() -> Agent:
    """수호지 세계관 기반 한국어 서사 컨텐츠 작성 에이전트."""
    return Agent(
        role="스토리텔러",
        goal=(
            "수호지(水滸傳) 세계관에 충실한 한국어 게임 컨텐츠를 생성한다. "
            "이벤트 텍스트, 영웅 배경 설명, 마을 설명, 전투 나레이션을 작성한다. "
            "역사적 고증과 극적 재미를 동시에 살린다."
        ),
        backstory=(
            "수호지 전문 작가이자 게임 시나리오 작가다. "
            "108 호한 각각의 성격과 고사를 깊이 이해하고 있다. "
            "12세기 북송 시대 분위기를 생생하게 살리는 한국어 문장을 쓴다."
        ),
        tools=[_file_read, _file_write],
        llm=get_design_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )


def code_reviewer() -> Agent:
    """코드 품질 검토 및 개선 제안 에이전트."""
    return Agent(
        role="코드 리뷰어",
        goal=(
            "작성된 코드가 기존 아키텍처와 일관성이 있는지 검토하고, "
            "버그·엣지케이스·성능 문제를 찾아낸다. "
            "최종 결과물이 즉시 실행 가능한 상태인지 확인한다."
        ),
        backstory=(
            "시니어 Python 개발자로 코드 리뷰와 품질 보증을 전담한다. "
            "crewAI, Pydantic v2, Python 3.11 이상의 관용구에 정통하다. "
            "실용성을 중시하여 구체적인 수정 코드를 제안한다."
        ),
        tools=[_file_read, _file_write],
        llm=get_review_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=4,
    )


def game_tester() -> Agent:
    """QA 테스트 전담 에이전트 — 실제 게임 실행으로 버그를 재현·분석한다."""
    return Agent(
        role="QA 테스터",
        goal=(
            "Water Margin Story를 python_runner로 실제 실행해서 버그를 재현한다. "
            "traceback을 직접 확인하고 원인을 분석한 뒤, "
            "재현 코드와 근본 원인 분석 결과를 개발자에게 전달한다."
        ),
        backstory=(
            "Python QA 엔지니어로 실제 실행 기반 테스트를 중시한다. "
            "코드만 읽는 것으로는 부족하며, 항상 python_runner로 실행해서 "
            "실제 traceback을 확인한 뒤 버그를 보고한다. "
            "재현 가능한 최소 코드 스니펫을 만들어 개발자에게 넘긴다."
        ),
        tools=[_file_read, _python_runner],
        llm=get_review_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )


def ui_designer() -> Agent:
    """UI/UX 설계 전담 에이전트 — Rich 터미널 UI 설계."""
    return Agent(
        role="UI 디자이너",
        goal=(
            "Water Margin Story의 터미널 UI를 더 직관적이고 아름답게 만들어라. "
            "Rich 콘솔 컴포넌트(Panel, Table, Layout, Live, Columns)와 "
            "ANSI 스타일링을 최대한 활용하는 UI를 설계한다."
        ),
        backstory=(
            "TUI(Text User Interface) 전문 디자이너로 Rich 라이브러리에 정통하다. "
            "코드와 UI를 읽어보고 현재 구조를 파악한 뒤 "
            "실현 가능한 스펙을 작성하고 /tmp/wm_ui_design.md에 저장한다."
        ),
        tools=[_file_read, _file_write],
        llm=get_design_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )


def ui_developer() -> Agent:
    """UI 코드 구현 전담 에이전트 — ui/terminal_ui.py만 수정한다."""
    return Agent(
        role="UI 개발자",
        goal=(
            "ui/terminal_ui.py를 수정하여 UI 디자이너의 스펙을 구현한다. "
            "python_runner로 변경 후 import에러가 없는지 확인한다. "
            "game/, models/, config/ 파일은 절대 수정하지 않는다."
        ),
        backstory=(
            "Python Rich TUI 개발자로 ui/terminal_ui.py에만 집중한다. "
            "코드를 저장한 뒤 python_runner로 import 에러 없는지 검증한다. "
            "게임 로직 파일은 읽기만 하고 절대 수정하지 않는다."
        ),
        tools=[_file_read, _file_write, _file_patch, _python_runner],
        llm=get_code_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )
