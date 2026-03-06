"""crewAI tool: 실제 Python 코드를 실행하고 출력/예외를 캡처한다."""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

_PROJECT_ROOT = Path(__file__).parent.parent
_PYTHON = str(_PROJECT_ROOT / ".venv" / "bin" / "python")


class PythonRunnerInput(BaseModel):
    code: str = Field(
        description=(
            "실행할 Python 코드 (문자열). "
            "프로젝트 루트에서 실행되므로 'from models.game_state import GameState' 같은 "
            "import를 바로 사용할 수 있다. "
            "버그를 재현하려면 실제 오류가 발생하는 코드 경로를 그대로 호출하라."
        )
    )


class PythonRunnerTool(BaseTool):
    name: str = "python_runner"
    description: str = (
        "실제 Python 코드를 프로젝트 환경에서 실행하고 stdout/stderr/traceback을 반환한다. "
        "버그 재현, 모듈 import 확인, 게임 로직 단위 실행에 사용한다. "
        "입력: code(실행할 Python 코드 문자열). "
        "출력: 실행 결과 또는 예외 메시지."
    )
    args_schema: type[BaseModel] = PythonRunnerInput

    def _run(self, code: str) -> str:
        timeout = 30
        # 들여쓰기 정규화
        code = textwrap.dedent(code)

        # .env 로드를 자동 prepend
        full_code = (
            "import sys, os\n"
            f"sys.path.insert(0, {str(_PROJECT_ROOT)!r})\n"
            "os.chdir(" + repr(str(_PROJECT_ROOT)) + ")\n"
            "from dotenv import load_dotenv; load_dotenv()\n"
            + code
        )

        try:
            result = subprocess.run(
                [_PYTHON, "-c", full_code],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(_PROJECT_ROOT),
            )
        except subprocess.TimeoutExpired:
            return f"[TIMEOUT] {timeout}초 내에 실행이 완료되지 않았습니다."
        except FileNotFoundError:
            # .venv가 없는 환경이면 시스템 python 으로 재시도
            try:
                result = subprocess.run(
                    [sys.executable, "-c", full_code],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(_PROJECT_ROOT),
                )
            except Exception as e:
                return f"[ERROR] Python 실행 실패: {e}"

        output_parts: list[str] = []
        if result.stdout.strip():
            output_parts.append(f"[STDOUT]\n{result.stdout.strip()}")
        if result.stderr.strip():
            output_parts.append(f"[STDERR/TRACEBACK]\n{result.stderr.strip()}")
        if result.returncode != 0:
            output_parts.append(f"[EXIT CODE] {result.returncode}")

        return "\n\n".join(output_parts) if output_parts else "[OK] 출력 없음, 정상 종료."
