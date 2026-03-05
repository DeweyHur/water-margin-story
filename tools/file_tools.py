"""Simple file read/write tools with minimal schema for LLM compatibility."""
from __future__ import annotations

from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class _ReadInput(BaseModel):
    file_path: str = Field(description="읽을 파일 경로 (프로젝트 루트 기준 상대 경로 또는 절대 경로)")


class _WriteInput(BaseModel):
    file_path: str = Field(description="저장할 파일 경로 (프로젝트 루트 기준 상대 경로 또는 절대 경로)")
    content: str = Field(description="파일에 저장할 전체 내용")


class SimpleFileReadTool(BaseTool):
    name: str = "read_project_file"
    description: str = "프로젝트 파일 전체 내용을 읽는다. file_path만 필요."
    args_schema: type[BaseModel] = _ReadInput

    def _run(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.is_absolute():
            # project root is two levels up from tools/
            root = Path(__file__).parent.parent
            path = root / file_path
        if not path.exists():
            return f"ERROR: File not found: {file_path}"
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            return f"ERROR reading {file_path}: {e}"


class SimpleFileWriteTool(BaseTool):
    name: str = "write_project_file"
    description: str = "프로젝트 파일에 내용을 저장한다. file_path와 content가 필요."
    args_schema: type[BaseModel] = _WriteInput

    def _run(self, file_path: str, content: str) -> str:
        path = Path(file_path)
        if not path.is_absolute():
            root = Path(__file__).parent.parent
            path = root / file_path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return f"OK: saved {file_path} ({len(content)} chars)"
        except Exception as e:
            return f"ERROR writing {file_path}: {e}"
