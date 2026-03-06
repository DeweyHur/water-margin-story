"""게임 개발 크루 태스크 빌더."""
from __future__ import annotations

from crewai import Agent, Task

# 전체 파일 목록
_FILES = (
    "models/hero.py, models/town.py, models/game_state.py, models/army.py, models/event.py, "
    "game/engine.py, game/turn_manager.py, game/event_system.py, game/combat_manager.py, "
    "ui/terminal_ui.py, config/heroes.yaml, config/towns.yaml, config/events.yaml"
)

# UI 전용 파일 목록
_UI_FILES = (
    "ui/terminal_ui.py, game/engine.py, "
    "models/game_state.py, models/hero.py, models/town.py"
)


def design_feature_task(feature_request: str, designer: Agent) -> Task:
    return Task(
        description=(
            "도구를 한 번에 하나씩 순서대로 호출하라.\n\n"
            "1. read_project_file 호출: file_path='ui/terminal_ui.py'\n"
            "2. read_project_file 호출: file_path='game/engine.py'\n"
            "3. read_project_file 호출: file_path='models/game_state.py'\n"
            "4. write_project_file 호출: file_path='/tmp/wm_design.md'\n"
            "   내용에 다음을 반드시 포함할 것 (코드 블록 금지, 인덴트 텍스트로)::\n"
            "   - 바꿼 파일 목록 (정확한 경로)\n"
            "   - 각 파일별: 추가/수정할 함수멝, 시그니처, 왕늘리는 코드 스니펫 (2-5줄)\n"
            "   - 새 Pydantic 필드가 있으면 필드명과 타입\n"
            "   - 구현 순서 (어떤 파일을 먼저 고친다)\n\n"
            f"기능 요청: {feature_request}"
        ),
        expected_output="/tmp/wm_design.md 저장 완료 확인.",
        agent=designer,
    )


def implement_feature_task(feature_request: str, developer: Agent) -> Task:
    return Task(
        description=(
            "파일 1개씩 순서대로 처리하라. 여러 파일을 동시에 수정하지 말 것.\n\n"
            "1. read_project_file 호출: file_path='/tmp/wm_design.md'\n"
            "2. 설계에서 첫 번째 수정 파일을 확인한다\n"
            "3. read_project_file 호출: 첫 번째 파일 읽기\n"
            "4. write_project_file 호출: 코드 수정 후 저장\n"
            "5. python_runner 호출: 저장한 모듈 import 검증\n"
            "   code='import sys; sys.path.insert(0,\".\"); "
            "from ui.terminal_ui import TerminalUI; "
            "from models.game_state import GameState; print(\"VERIFY_OK\")'\n"
            "6. 설계에 다음 파일이 있으면 3-5를 반복\n\n"
            f"구현 대상: {feature_request}\n\n"
            "코드 규칙: Python 3.11+, 타입 힌트, Pydantic v2 BaseModel, "
            "from __future__ import annotations, 기존 import 절대 제거 금지. "
            "코드를 텍스트로 출력하지 말 것 — write_project_file로 저장할 것."
        ),
        expected_output="python_runner 결과 'VERIFY_OK' 포함 여부.",
        agent=developer,
    )


def generate_content_task(content_request: str, storyteller: Agent) -> Task:
    return Task(
        description=(
            "도구를 반드시 한 번에 하나씩 순서대로 호출하라.\n\n"
            "1. read_project_file 호출: file_path='config/events.yaml'\n"
            "2. read_project_file 호출: file_path='config/heroes.yaml'\n"
            "3. read_project_file 호출: file_path='config/towns.yaml'\n"
            "4. write_project_file 호출: 동일한 YAML 포맷으로 컨텐츠 추가 저장\n\n"
            f"컨텐츠 요청: {content_request}\n\n"
            "수호지 세계관, 한국어, 게임 밸런스를 유지하라. "
            "YAML을 텍스트로 출력하지 말 것 — write_project_file로 저장할 것."
        ),
        expected_output="write_project_file 저장 완료 확인.",
        agent=storyteller,
    )


def developer_fix_from_tester_task(developer: Agent) -> Task:
    return Task(
        description=(
            "도구를 반드시 한 번에 하나씩 순서대로 호출하라.\n\n"
            "1. 앞선 QA 테스터 보고서에서 수정할 파일을 파악한다\n"
            "2. read_project_file 호출: 해당 파일 읽기\n"
            "3. write_project_file 호출: 최소 변경으로 버그 수정 후 저장\n"
            "4. python_runner 호출: "
            "code='import sys; sys.path.insert(0,\".\"); "
            "import models; import game; print(\"FIX_OK\")'\n\n"
            "코드 규칙: Python 3.11+, 타입 힌트, Pydantic v2, "
            "from __future__ import annotations. "
            "코드를 텍스트로 출력하지 말 것 — write_project_file로 저장할 것."
        ),
        expected_output="python_runner 결과 'FIX_OK' 포함 여부.",
        agent=developer,
    )


def developer_fix_from_review_task(developer: Agent) -> Task:
    return Task(
        description=(
            "도구를 반드시 한 번에 하나씩 순서대로 호출하라.\n\n"
            "1. read_project_file 호출: file_path='/tmp/wm_review.md'\n"
            "2. read_project_file 호출: 리뷰에서 지목된 파일 읽기\n"
            "3. write_project_file 호출: 지적 사항 수정 후 저장\n"
            "4. python_runner 호출: "
            "code='import sys; sys.path.insert(0,\".\"); "
            "import models; import game; print(\"FIX_OK\")'\n\n"
            "품질 점수 7점 미만이면 전면 개선, 7점 이상이면 지적 항목만 수정. "
            "코드를 텍스트로 출력하지 말 것 — write_project_file로 저장할 것."
        ),
        expected_output="python_runner 결과 'FIX_OK' 포함 여부.",
        agent=developer,
    )


def developer_implement_for_content_task(developer: Agent) -> Task:
    return Task(
        description=(
            "도구를 반드시 한 번에 하나씩 순서대로 호출하라.\n\n"
            f"1. read_project_file 호출: 관련 파일({_FILES}) 중 필요한 것 읽기\n"
            "2. 앞선 스토리텔러 컨텐츠가 참조하는 기능/필드/EventType이 코드에 없으면 구현\n"
            "3. (수정 있을 때만) write_project_file 호출: 최소 변경으로 저장\n"
            "4. python_runner 호출: "
            "code='import sys; sys.path.insert(0,\".\"); "
            "import models; import game; print(\"VERIFY_OK\")'\n\n"
            "없는 것이 없으면 4번(python_runner)만 실행하라. "
            "코드를 텍스트로 출력하지 말 것."
        ),
        expected_output="python_runner 결과 'VERIFY_OK' 포함 여부.",
        agent=developer,
    )


def review_content_quality_task(reviewer: Agent) -> Task:
    return Task(
        description=(
            f"관련 파일({_FILES})을 read_project_file로 읽어라.\n"
            "YAML 포맷 일치, 세계관 일관성, 밸런스 수치, "
            "import/타입힌트/Pydantic v2 준수, 엣지케이스를 검토하라.\n"
            "검토 결과(YAML 이슈·코드 이슈·품질 점수·종합 의견)를 "
            "write_project_file로 /tmp/wm_content_review.md에 저장하라."
        ),
        expected_output="/tmp/wm_content_review.md 저장 완료 확인. 품질 점수 포함.",
        agent=reviewer,
    )


def review_code_task(reviewer: Agent) -> Task:
    return Task(
        description=(
            f"관련 파일({_FILES})을 read_project_file로 읽어라.\n"
            "읽은 후 import 경로, Pydantic v2 문법, 타입 힌트, 엣지케이스, "
            "GameState 직렬화 호환성을 검토하라.\n"
            "검토 결과(문제점 목록·수정 스니펫·품질 점수·종합 의견)를 "
            "write_project_file로 /tmp/wm_review.md에 저장하라."
        ),
        expected_output="/tmp/wm_review.md 저장 완료 확인. 품질 점수 포함.",
        agent=reviewer,
    )


SMOKE_TESTS = [
    (
        "테스트1_임포트",
        "import models; import models.hero; import models.town; import models.game_state; "
        "import game; import game.engine; import game.combat_manager; "
        "import ui; import ui.terminal_ui; import tools; print('PASS')",
    ),
    (
        "테스트2_GameState",
        "from models.game_state import GameState\n"
        "gs = GameState()\n"
        "print('turns_remaining:', gs.turns_remaining())\n"
        "print('is_over:', gs.is_over())\n"
        "print('PASS')",
    ),
    (
        "테스트3_Hero_Town_Army",
        "import yaml, pathlib\n"
        "heroes = yaml.safe_load(pathlib.Path('config/heroes.yaml').read_text())\n"
        "towns  = yaml.safe_load(pathlib.Path('config/towns.yaml').read_text())\n"
        "from models.hero import Hero; from models.town import Town\n"
        "h = Hero(**heroes['heroes'][0]); t = Town(**towns['towns'][0])\n"
        "print('Hero:', h.name_ko, '  Town:', t.name_ko)\n"
        "print('PASS')",
    ),
    (
        "테스트4_CombatManager",
        "from game.combat_manager import CombatManager\n"
        "from models.game_state import GameState\n"
        "cm = CombatManager(GameState())\n"
        "print('field_battle:', callable(getattr(cm, 'field_battle', None)))\n"
        "print('siege_battle:', callable(getattr(cm, 'siege_battle', None)))\n"
        "print('PASS')",
    ),
    (
        "테스트5_TurnManager_EventSystem",
        "from game.turn_manager import TurnManager\n"
        "from game.event_system import EventSystem\n"
        "from models.game_state import GameState\n"
        "gs = GameState(); tm = TurnManager(gs); es = EventSystem(gs)\n"
        "print('TurnManager:', type(tm).__name__)\n"
        "print('EventSystem:', type(es).__name__)\n"
        "print('PASS')",
    ),
    (
        "테스트6_AI턴실행",
        "import yaml, pathlib, random\n"
        "random.seed(42)\n"
        "from models.game_state import GameState\n"
        "from models.hero import Hero\n"
        "from models.town import Town\n"
        "from models.faction import Faction\n"
        "from game.turn_manager import TurnManager\n"
        "from game.event_system import EventSystem\n"
        "from game.combat_manager import CombatManager\n"
        "# 최소 게임 스테이트 구성\n"
        "gs = GameState()\n"
        "heroes_data = yaml.safe_load(pathlib.Path('config/heroes.yaml').read_text())\n"
        "towns_data = yaml.safe_load(pathlib.Path('config/towns.yaml').read_text())\n"
        "factions_data = yaml.safe_load(pathlib.Path('config/factions.yaml').read_text())\n"
        "for h in heroes_data['heroes']:\n"
        "    gs.heroes[h['id']] = Hero(**h)\n"
        "for t in towns_data['towns']:\n"
        "    gs.towns[t['id']] = Town(**t)\n"
        "for f in factions_data['factions']:\n"
        "    gs.factions[f['id']] = Faction(**f)\n"
        "tm = TurnManager(gs)\n"
        "# AI 영웅 3명 최소 1턴씩 실행\n"
        "ai_heroes = [h for h in gs.heroes.values() if not h.is_player_controlled][:3]\n"
        "for hero in ai_heroes:\n"
        "    hero.current_army = 1500\n"
        "    tm.ai_turn(hero)\n"
        "print('PASS')",
    ),
]


def smoke_test_task(tester: Agent) -> Task:
    tests_text = "\n".join(
        f"[{name}]\npython_runner 호출 코드:\n```python\n{code}\n```"
        for name, code in SMOKE_TESTS
    )
    return Task(
        description=(
            "아래 각 테스트마다 python_runner 도구를 호출하라 (직접 실행, 설명 금지).\n"
            "각 테스트가 끝나면 PASS/FAIL과 출력을 기록하고 다음 테스트로 넘어가라.\n\n"
            + tests_text
        ),
        expected_output=(
            "각 테스트별 PASS/FAIL, 실제 출력 또는 traceback, "
            "FAIL이면 오류 파일명과 줄 번호."
        ),
        agent=tester,
    )


def make_fix_from_failures_task(failure_report: str, developer: Agent) -> Task:
    """스모크 테스트 실패 결과를 받아 개발자가 수정하는 태스크."""
    return Task(
        description=(
            "도구를 반드시 한 번에 하나씩 순서대로 호출하라.\n\n"
            "1. 실패 보고서를 분석하여 수정할 파일을 파악한다\n"
            "2. read_project_file 호출: 해당 파일 읽기\n"
            "3. write_project_file 호출: 최소 변경으로 버그 수정 후 저장\n"
            "4. python_runner 호출: "
            "code='import sys; sys.path.insert(0,\".\"); "
            "<수정한 모듈> import; print(\"FIX_OK\")'\n\n"
            f"실패 보고서:\n{failure_report}\n\n"
            "코드 규칙: Python 3.11+, 타입 힌트, Pydantic v2, "
            "from __future__ import annotations. "
            "코드를 텍스트로 출력하지 말 것 — write_project_file로 저장할 것."
        ),
        expected_output="python_runner 결과 'FIX_OK' 포함 여부.",
        agent=developer,
    )


def bug_fix_task(bug_report: str, tester: Agent) -> Task:
    """하위 호환용 — smoke_test_task 사용 권장."""
    return smoke_test_task(tester)


# ------------------------------------------------------------------
# UI tasks
# ------------------------------------------------------------------

def design_ui_task(ui_request: str, designer: Agent) -> Task:
    return Task(
        description=(
            "도구를 반드시 한 번에 하나씩 순서대로 호출하라.\n\n"
            "1. read_project_file 호출: file_path='ui/terminal_ui.py'\n"
            "2. read_project_file 호출: file_path='game/engine.py'\n"
            "3. read_project_file 호출: file_path='models/game_state.py'\n"
            "4. read_project_file 호출: file_path='models/hero.py'\n"
            "5. read_project_file 호출: file_path='models/town.py'\n"
            "6. write_project_file 호출: file_path='/tmp/wm_ui_design.md', "
            "content=설계 문서(변경할 메서드 목록, 사용할 라이브러리, 게임 로직 변경 없음 확인, "
            "코드 예시는 인덴트된 일반 텍스트로 — 백틱 코드블록 사용 금지)\n\n"
            f"UI 요청: {ui_request}"
        ),
        expected_output="/tmp/wm_ui_design.md 저장 완료 확인.",
        agent=designer,
    )


def implement_ui_task(ui_request: str, developer: Agent) -> Task:
    return Task(
        description=(
            "도구를 반드시 한 번에 하나씩 순서대로 호출하라.\n\n"
            "1. read_project_file 호출: file_path='/tmp/wm_ui_design.md'\n"
            "2. read_project_file 호출: file_path='ui/terminal_ui.py'\n"
            "3. write_project_file 호출: file_path='ui/terminal_ui.py', "
            "content=수정된 전체 파일 내용\n"
            "4. python_runner 호출: "
            "code='from ui.terminal_ui import TerminalUI; print(\"IMPORT_OK\")'\n\n"
            f"UI 요청: {ui_request}\n\n"
            "제약: game/, models/, config/ 파일 수정 금지. "
            "코드를 텍스트로 출력하지 말 것 — 반드시 write_project_file로 저장할 것."
        ),
        expected_output="python_runner 실행 결과 'IMPORT_OK' 포함 여부.",
        agent=developer,
    )