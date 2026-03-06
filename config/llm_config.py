"""Centralized LLM configuration.

에이전트별 LLM 역할 분담:
  매니저 (계획·위임·검수)  → Groq Llama 3.3 70B Versatile  (가장 똑똑한 추론)
  개발자 (도구 사용·코딩)  → Groq Llama 4 Scout 17Bx16E    (tool calling 고성능)
  리뷰어 (검수·품질보증)   → Gemini 2.0 Flash               (컨텍스트 이해 강점)
  인게임 NPC AI           → Groq Llama 3.1 8B Instant       (실시간 턴 결정)
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


def get_manager_llm(temperature: float = 0.3) -> LLM:
    """Groq Llama 3.3 70B Versatile — 매니저 전용. 도구 없음, 계획·위임·최종검수."""
    return LLM(
        model="groq/llama-3.3-70b-versatile",
        api_key=_GROQ_KEY,
        temperature=temperature,
    )


def get_groq_tool_llm(temperature: float = 0.2, max_tokens: int = 8192) -> LLM:
    """Groq Llama 4 Scout 17Bx16E — 128k context, tool calling 고성능."""
    return LLM(
        model="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        api_key=_GROQ_KEY,
        temperature=temperature,
        max_tokens=max_tokens,
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
    """코드 생성 — Gemini 2.5 Flash. 65K output 토큰, tool calling 지원."""
    return get_gemini_flash_llm(temperature=0.1)


def get_review_llm() -> LLM:
    """코드 검수 — Gemini Flash. 컨텍스트 이해·문서 분석 강점. FileReadTool 사용."""
    return get_gemini_flash_llm(temperature=0.1)


def get_game_llm() -> LLM:
    """인게임 NPC AI 턴 결정 — 도구 없음, 8B 고속."""
    return get_groq_llm(temperature=0.7, max_tokens=1000)


# 하위 호환
def get_dev_llm() -> LLM:
    return get_groq_llm()


def llm_available() -> bool:
    return bool(_GROQ_KEY or _GEMINI_KEY)
