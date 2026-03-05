"""Centralized LLM configuration.

에이전트별 LLM 역할 분담:
  모든 에이전트 (FileReadTool 등 도구 사용) → Groq Llama 4 Scout 17Bx16E  (128k, 고성능 tool calling)
  인게임 NPC AI    → Groq Llama 3.1 8B Instant  (실시간 턴 결정, 도구 없음)
"""
from __future__ import annotations

import os
from crewai import LLM

_GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
_GROQ_KEY = os.getenv("GROQ_API_KEY", "")


def get_groq_llm(temperature: float = 0.3, max_tokens: int = 8000) -> LLM:
    """Groq Llama 3.1 8B Instant — 도구 없는 에이전트용. 128k context, 고속."""
    return LLM(
        model="groq/llama-3.1-8b-instant",
        api_key=_GROQ_KEY,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_groq_tool_llm(temperature: float = 0.2, max_tokens: int = 8192) -> LLM:
    """Groq Llama 4 Scout 17Bx16E — 128k context, tool calling 고성능. max_tokens 상한 8192."""
    return LLM(
        model="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        api_key=_GROQ_KEY,
        temperature=temperature,
        max_tokens=min(max_tokens, 8192),
    )


def get_gemini_flash_llm(temperature: float = 0.3) -> LLM:
    """Gemini 2.5 Flash — fallback 또는 보조."""
    return LLM(
        model="gemini/gemini-2.5-flash",
        api_key=_GEMINI_KEY,
        temperature=temperature,
    )


# 역할별 함수
def get_design_llm() -> LLM:
    """기획/아키텍처 — FileReadTool 사용, Llama 4 Scout tool calling."""
    return get_groq_tool_llm(temperature=0.5, max_tokens=8192)


def get_code_llm() -> LLM:
    """코드 생성 — FileWriterTool·python_runner 사용, Llama 4 Scout tool calling. (max 8192)"""
    return get_groq_tool_llm(temperature=0.1, max_tokens=8192)


def get_review_llm() -> LLM:
    """코드 검수 — FileReadTool·python_runner 사용, Llama 4 Scout tool calling. (max 8192)"""
    return get_groq_tool_llm(temperature=0.1, max_tokens=8192)


def get_game_llm() -> LLM:
    """인게임 NPC AI 턴 결정 — 도구 없음, 8B 고속."""
    return get_groq_llm(temperature=0.7, max_tokens=1000)


# 하위 호환
def get_dev_llm() -> LLM:
    return get_groq_llm()


def llm_available() -> bool:
    return bool(_GROQ_KEY or _GEMINI_KEY)
