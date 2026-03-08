"""Simple file read/write/patch tools with minimal schema for LLM compatibility."""
from __future__ import annotations

from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class _ReadInput(BaseModel):
    file_path: str = Field(description="읽을 파일 경로 (프로젝트 루트 기준 상대 경로 또는 절대 경로)")


class _WriteInput(BaseModel):
    file_path: str = Field(description="저장할 파일 경로 (프로젝트 루트 기준 상대 경로 또는 절대 경로)")
    content: str = Field(description="파일에 저장할 전체 내용")


class _PatchInput(BaseModel):
    file_path: str = Field(description="수정할 파일 경로 (프로젝트 루트 기준 상대 경로 또는 절대 경로)")
    old_code: str = Field(
        description=(
            "파일에서 교체할 기존 코드 블록. "
            "함수 전체(def ...부터 마지막 줄까지) 또는 클래스 전체를 정확히 복사해야 한다. "
            "공백·들여쓰기·줄바꿈이 파일 내용과 완전히 일치해야 한다."
        )
    )
    new_code: str = Field(
        description="old_code를 대체할 새 코드. 들여쓰기와 형식을 old_code와 맞춰야 한다."
    )


def _resolve(file_path: str) -> Path:
    path = Path(file_path)
    if not path.is_absolute():
        root = Path(__file__).parent.parent
        path = root / file_path
    return path


class SimpleFileReadTool(BaseTool):
    name: str = "read_project_file"
    description: str = "프로젝트 파일 전체 내용을 읽는다. file_path만 필요."
    args_schema: type[BaseModel] = _ReadInput

    def _run(self, file_path: str) -> str:
        path = _resolve(file_path)
        if not path.exists():
            return f"ERROR: File not found: {file_path}"
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            return f"ERROR reading {file_path}: {e}"


_MAX_WRITE_CHARS = 4000  # Groq output token 한도 초과 방지


class SimpleFileWriteTool(BaseTool):
    name: str = "write_project_file"
    description: str = (
        "새 파일 생성 또는 짧은 파일 전체 저장 전용 (4000자 이하). "
        "기존 파일의 함수·클래스 교체는 반드시 patch_project_file 사용. "
        "200줄 이상 파일은 patch_project_file로 특정 함수만 교체할 것."
    )
    args_schema: type[BaseModel] = _WriteInput

    def _run(self, file_path: str, content: str) -> str:
        if len(content) > _MAX_WRITE_CHARS:
            return (
                f"ERROR: content too large ({len(content)} chars > {_MAX_WRITE_CHARS} limit). "
                "Use patch_project_file to replace only the changed function/class block. "
                "Read the file first, then patch only the specific function that needs to change."
            )
        path = _resolve(file_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return f"OK: saved {file_path} ({len(content)} chars)"
        except Exception as e:
            return f"ERROR writing {file_path}: {e}"


_MAX_PATCH_CHARS = 2500  # Groq tool call JSON 페이로드 한도 초과 방지


class PatchProjectFileTool(BaseTool):
    name: str = "patch_project_file"
    description: str = (
        "파일에서 특정 함수나 클래스 블록만 교체한다. 파일 전체를 덮어쓰지 않는다. "
        "old_code는 파일에서 교체할 기존 코드(def/class 블록 전체)를 완전히 일치하도록 복사. "
        "new_code는 대체할 새 코드(들여쓰기 동일). "
        "new_code는 2500자 이하로 제한 — 크면 더 작은 helper 메서드로 분리한 후 각각 patch하라."
    )
    args_schema: type[BaseModel] = _PatchInput

    def _run(self, file_path: str, old_code: str, new_code: str) -> str:
        if len(new_code) > _MAX_PATCH_CHARS:
            return (
                f"ERROR: new_code too large ({len(new_code)} chars > {_MAX_PATCH_CHARS} limit). "
                "Groq tool call JSON payload limit 초과 방지를 위해 new_code 는 2500자 이하여야 한다. "
                "함수를 더 작은 private helper 메서드(치당 40줄 이하)로 분리하고 각 메서드를 별도로 patch하라. "
                "예: _build_left_panel(), _build_map_grid(), _build_town_detail() 등으로 억지로 쪼개서 작성."
            )
        path = _resolve(file_path)
        if not path.exists():
            return f"ERROR: File not found: {file_path}"
        try:
            original = path.read_text(encoding="utf-8")
        except Exception as e:
            return f"ERROR reading {file_path}: {e}"

        if old_code not in original:
            # 진단 정보 제공
            lines_old = old_code.strip().splitlines()
            first = lines_old[0] if lines_old else "(empty)"
            last = lines_old[-1] if lines_old else "(empty)"
            return (
                f"ERROR: patch_project_file — old_code를 {file_path}에서 찾을 수 없음.\n"
                f"첫 줄: {first!r}\n"
                f"마지막 줄: {last!r}\n"
                f"파일을 read_project_file로 다시 읽고 old_code를 정확히 복사하라."
            )

        count = original.count(old_code)
        if count > 1:
            return (
                f"ERROR: patch_project_file — old_code가 {count}곳에서 발견됨. "
                "더 넓은 범위의 코드를 old_code에 포함해 유일하게 특정하라."
            )

        patched = original.replace(old_code, new_code, 1)
        try:
            path.write_text(patched, encoding="utf-8")
            old_lines = old_code.count("\n") + 1
            new_lines = new_code.count("\n") + 1
            return (
                f"OK: patched {file_path} "
                f"({old_lines}줄 → {new_lines}줄, 총 {len(patched)} chars)"
            )
        except Exception as e:
            return f"ERROR writing {file_path}: {e}"
