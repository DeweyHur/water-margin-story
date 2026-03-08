"""게임 개발 크루 태스크 빌더."""
from __future__ import annotations

from crewai import Agent, Task

# 전체 파일 목록
_FILES = (
    "models/hero.py, models/town.py, models/game_state.py, models/army.py, models/event.py, "
    "game/engine.py, game/turn_manager.py, game/event_system.py, game/combat_manager.py, "
    "ui/terminal_ui.py, config/heroes.yaml, config/towns.yaml, config/events.yaml"
)

# UI 전용 파일 목록 (전투 포함)
_UI_FILES = (
    "ui/terminal_ui.py, game/combat_manager.py, game/turn_manager.py, "
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
            "   content는 아래 형식의 순수 텍스트 (마크다운 금지, 백틱 금지, '#' 금지):\n"
            "   수정파일: ui/terminal_ui.py\n"
            "   추가함수: show_map(game_state)\n"
            "   수정파일: models/game_state.py\n"
            "   추가필드: map_cursor_pos str\n"
            "   순서: game_state -> engine -> terminal_ui\n\n"
            f"기능 요청: {feature_request}\n\n"
            "주의: 코드 스니펫 절대 금지. 함수명과 파라미터 이름만 나열."
        ),
        expected_output="/tmp/wm_design.md 저장 완료 확인.",
        agent=designer,
    )


def implement_feature_task(feature_request: str, developer: Agent) -> Task:
    """설계+구현 통합 태스크 - 파일 직접 읽고 수정."""
    return Task(
        description=(
            "아래 순서대로 도구를 호출하라.\n\n"
            "1. read_project_file 호출: file_path='ui/terminal_ui.py'\n"
            "2. read_project_file 호출: file_path='game/combat_manager.py'\n"
            "3. read_project_file 호출: file_path='game/turn_manager.py'\n"
            "4. read_project_file 호출: file_path='models/game_state.py'\n"
            "5. read_project_file 호출: file_path='models/town.py'\n"
            "6. 기능 요청을 구현하기 위해 수정이 필요한 파일을 모두 파악하라.\n"
            "7. 각 수정 파일마다 저장 — 규칙:\n"
            "   - 기존 함수·메서드·클래스만 교체할 때: patch_project_file(file_path, old_code, new_code) 호출.\n"
            "   - 새 파일 생성 또는 파일 전체 재작성할 때만: write_project_file 호출.\n"
            "   - ui/terminal_ui.py, game/combat_manager.py 등 200줄 이상 파일은\n"
            "     반드시 patch_project_file로 특정 함수/메서드만 교체하라.\n"
            "   - ⚠️ patch_project_file new_code 한도: 2500자/40줄 이하. 초과하면 에러 반환 —\n"
            "     함수를 private helper 메서드(각 ~30줄)로 쪼갠 뒤 각각 별도 patch 호출하라.\n"
            "     한 번에 한 메서드만 patch 하라.\n"
            "   - 같은 파일에 여러 patch가 필요하면 순서대로 하나씩 호출하라.\n"
            "8. python_runner 호출로 아래 코드를 실행해 구현을 검증하라 (AssertionError가 나면 해당 항목을 구현하고 다시 patch):\n"
            "code='\n"
            "import sys; sys.path.insert(0, \".\")\n"
            "from ui.terminal_ui import TerminalUI\n"
            "from game.combat_manager import CombatManager\n"
            "ui = TerminalUI()\n"
            "assert hasattr(ui, \"show_combat_preview\"), \"FAIL: show_combat_preview missing in TerminalUI\"\n"
            "assert hasattr(ui, \"show_faction_change_animation\"), \"FAIL: show_faction_change_animation missing in TerminalUI\"\n"
            "src_cm = open(\"game/combat_manager.py\").read()\n"
            "assert \"Live\" in src_cm, \"FAIL: rich.live.Live not used in combat_manager.py\"\n"
            "src_tm = open(\"game/turn_manager.py\").read()\n"
            "assert \"show_combat_preview\" in src_tm, \"FAIL: show_combat_preview not called in turn_manager.py\"\n"
            "assert \"show_faction_change_animation\" in src_tm, \"FAIL: show_faction_change_animation not called in turn_manager.py\"\n"
            "print(\"VERIFY_OK\")\n"
            "'\n\n"
            f"기능 요청: {feature_request}\n\n"
            "구현 가이드 (이 패턴을 반드시 사용하라):\n"
            "  [전투 미리보기] TerminalUI에 show_combat_preview(hero_town_id, target_town_id, state) 추가.\n"
            "    - console.clear() 후 지도를 그리되, 공격 출발지→목표 사이에 ASCII 화살표선(→ 또는 ===►)을 출력.\n"
            "    - _render_static_map을 활용하되, 두 거점을 강조 표시.\n"
            "    - input() 또는 questionary로 '전투 시작 (Enter)' 확인을 받는다.\n"
            "  [전투 화면 스크롤 방지] combat_manager.py의 siege_battle·field_battle에서 Rich Live 컨텍스트 사용.\n"
            "    - from rich.live import Live 임포트 추가.\n"
            "    - 각 단계(phase) 출력을 Live(renderable, refresh_per_second=4) 안에서 업데이트.\n"
            "    - 단계 사이 time.sleep은 1.0~1.5초로 늘려 플레이어가 읽을 수 있게 한다.\n"
            "  [애니메이션] TerminalUI에 show_faction_change_animation(town_id, old_faction_id, new_faction_id, state) 추가.\n"
            "    - 0.5초 간격으로 console.clear() + _render_static_map 3회 반복 (깜박임).\n"
            "    - 마지막엔 점령 메시지를 Panel로 출력.\n"
            "  [turn_manager 연결] _do_siege:\n"
            "    - siege_battle 호출 전 ui.show_combat_preview(hero.current_town, town.id, state) 호출.\n"
            "    - 승리 시 ui.show_faction_change_animation(town.id, old_faction, hero.faction_id, state) 호출.\n"
            "  [combat_manager 수정] siege_battle 시그니처에 ui=None 파라미터 추가 불필요.\n"
            "    Live 컨텍스트는 combat_manager 내부에서 자체 처리. turn_manager에서 따로 넘길 것 없음.\n"
            "코드 규칙: Python 3.11+, 타입 힌트, Pydantic v2, "
            "from __future__ import annotations, 기존 import 절대 제거 금지. "
            "기존 함수·클래스·메서드 절대 삭제 금지 — 새 코드만 추가하라."
        ),
        expected_output=(
            "python_runner 결과 'VERIFY_OK' 포함 + 변경 파일 목록 및 추가 함수명."
        ),
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
            "앞선 리뷰어 결과(context)를 읽고 즉시 아래 순서대로 도구를 호출하라.\n\n"
            "1. context에서 '수정 필요 파일' 목록과 '없는 기능 명세'를 파악한다.\n"
            "2. read_project_file 호출: 수정 필요 파일을 읽는다.\n"
            "3. 파일 저장 — 누락된 기능을 모두 구현하라:\n"
            "   - 기존 함수·메서드·클래스만 교체할 때: patch_project_file(file_path, old_code, new_code) 호출.\n"
            "   - 새 파일 생성 또는 파일 전체 재작성할 때만: write_project_file 호출.\n"
            "   - ui/terminal_ui.py 등 200줄 이상 파일은 반드시 patch_project_file로 특정 함수만 교체하라.\n"
            "   - ⚠️ patch_project_file new_code 한도: 2500자/40줄 이하. 초과 시 helper 메서드로 분리.\n"
            "   ⚠️ '구현 완성도 YES'만으로 건너뛰지 마라. python_runner로 직접 검증 후 PASS해야 완료.\n"
            "4. python_runner 호출로 아래 코드를 실행해 구현을 검증하라 (AssertionError가 나면 해당 항목 구현 후 재실행):\n"
            "code='\n"
            "import sys; sys.path.insert(0, \".\")\n"
            "from ui.terminal_ui import TerminalUI\n"
            "from game.combat_manager import CombatManager\n"
            "ui = TerminalUI()\n"
            "assert hasattr(ui, \"show_combat_preview\"), \"FAIL: show_combat_preview missing\"\n"
            "assert hasattr(ui, \"show_faction_change_animation\"), \"FAIL: show_faction_change_animation missing\"\n"
            "src_cm = open(\"game/combat_manager.py\").read()\n"
            "assert \"Live\" in src_cm, \"FAIL: Live not used in combat_manager.py\"\n"
            "src_tm = open(\"game/turn_manager.py\").read()\n"
            "assert \"show_combat_preview\" in src_tm, \"FAIL: show_combat_preview not called in turn_manager\"\n"
            "assert \"show_faction_change_animation\" in src_tm, \"FAIL: show_faction_change_animation not called\"\n"
            "print(\"FIX_OK\")\n"
            "'\n\n"
            "코드 규칙: Python 3.11+, 타입 힌트, Pydantic v2, "
            "from __future__ import annotations. "
            "기존 함수·클래스 삭제 금지 — 새 코드만 추가."
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


def review_feature_task(feature_request: str, reviewer: Agent) -> Task:
    """기능 구현 여부를 확인하는 리뷰 태스크."""
    return Task(
        description=(
            f"관련 파일({_UI_FILES})을 read_project_file로 각각 읽어라.\n\n"
            "다음을 반드시 검토하라:\n"
            "1. 기능 요청이 실제로 구현되었는가? "
            "   (새 함수/메서드가 코드에 존재하는가?) → 구현 완성도 YES/NO\n"
            "2. ⚠️ 호출 체인 추적 필수: 기능이 단순히 정의만 되어 있지 않고,"
            "   실제로 호출되는지 확인하라.\n"
            "   예: show_combat_preview가 terminal_ui.py에 있어도"
            "   turn_manager.py의 _do_siege에서 ui.show_combat_preview(...) 호출이 없으면 NO.\n"
            "   예: siege_battle이 Live 컨텍스트를 쓴다고 해도"
            "   실제로 with Live(...) 블록이 코드에 있어야 YES.\n"
            "3. 이번 기능 요청에 필요한 새 함수 목록을 반드시 하나씩 코드에서 찾아서 존재를 확인하라:\n"
            "   - terminal_ui.py 에 'def show_combat_preview' 문자열 — 있음/없음\n"
            "   - terminal_ui.py 에 'def show_faction_change_animation' 문자열 — 있음/없음\n"
            "   - combat_manager.py 에 'Live' 문자열 — 있음/없음\n"
            "   - turn_manager.py 에 'show_combat_preview' 문자열 — 있음/없음\n"
            "   - turn_manager.py 에 'show_faction_change_animation' 문자열 — 있음/없음\n"
            "   위 항목 중 하나라도 없으면 구현 완성도 NO.\n"
            "4. import 경로, Pydantic v2 문법, 타입 힌트, Python 3.11+ 준수 여부\n"
            "5. 기존 기능이 삭제되거나 손상되지 않았는가?\n"
            "6. 엣지케이스 처리 여부\n\n"
            f"기능 요청: {feature_request}\n\n"
            "검토 결과를 아래 형식으로 Final Answer에 출력하라 "
            "(파일 저장 불필요 — 이 출력이 다음 개발자에게 컨텍스트로 직접 전달된다):\n"
            "구현 완성도: YES/NO\n"
            "없는 기능 명세: (없는 함수·로직·호출 목록 — 구체적으로)\n"
            "수정 필요 파일: (파일 경로 목록)\n"
            "품질 점수: X/5\n"
            "종합 의견: ..."
        ),
        expected_output="구현 완성도 YES/NO · 없는 것 명세 · 수정 필요 파일 목록 · 품질 점수 포함.",
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
    (
        "테스트7_지도렌더링",
        "import yaml, pathlib\n"
        "from io import StringIO\n"
        "from rich.console import Console\n"
        "from models.game_state import GameState\n"
        "from models.hero import Hero\n"
        "from models.town import Town\n"
        "from models.faction import Faction\n"
        "from ui.terminal_ui import TerminalUI\n"
        "gs = GameState()\n"
        "towns_data = yaml.safe_load(pathlib.Path('config/towns.yaml').read_text())\n"
        "for t in towns_data['towns']:\n"
        "    gs.towns[t['id']] = Town(**t)\n"
        "heroes_data = yaml.safe_load(pathlib.Path('config/heroes.yaml').read_text())\n"
        "factions_data = yaml.safe_load(pathlib.Path('config/factions.yaml').read_text())\n"
        "for f in factions_data['factions']:\n"
        "    gs.factions[f['id']] = Faction(**f)\n"
        "first = heroes_data['heroes'][0]\n"
        "gs.heroes[first['id']] = Hero(**first)\n"
        "hero = gs.heroes[first['id']]\n"
        "ui = TerminalUI()\n"
        "buf = StringIO()\n"
        "ui.console = Console(file=buf, highlight=False)\n"
        "ui._render_static_map(gs, hero.current_town)\n"
        "assert len(buf.getvalue()) > 0, '지도 출력 없음'\n"
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