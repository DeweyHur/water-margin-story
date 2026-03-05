"""Centralized LLM configuration.

에이전트별 LLM 역할 분담:
  기본 (모든 에이전트) → Groq Llama 3.3 70B  (일일 14,000회, 초고속)
  Fallback / 보조   → Gemini 2.5 Flash    (일일 250~1,000회)
  인게임 NPC AI    → Groq Llama 3.3 70B  (실시간 턴 결정)
"""
from __future__ import annotations

import os
from crewai import LLM

_GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
_GROQ_KEY = os.getenv("GROQ_API_KEY", "")

# 기본 LLM: Groq Llama 3.3 70B — 초고속, 일일 14,000회
_GROQ_LLM_KWARGS = dict(
    model="groq/llama-3.3-70b-versatile",
    api_key=_GROQ_KEY,
)


def get_groq_llm(temperature: float = 0.3, max_tokens: int = 3000) -> LLM:
    """Groq Llama 3.3 70B — 모든 에이전트 기본값. max_tokens로 TPM 초과 방지."""
    return LLM(**_GROQ_LLM_KWARGS, temperature=temperature, max_tokens=max_tokens)


def get_gemini_flash_llm(temperature: float = 0.3) -> LLM:
    """Gemini 2.5 Flash — Groq 할당량 소진 시 fallback 또는 보조."""
    return LLM(
        model="gemini/gemini-2.5-flash",
        api_key=_GEMINI_KEY,
        temperature=temperature,
    )


# 여아별 역할 함수 — 현재 구성에서는 모두 Groq 사용
def get_design_llm() -> LLM:
    """기획/아키텍처 (Groq). max_tokens=2500 → 설계 문서에 충분."""
    return get_groq_llm(temperature=0.5, max_tokens=2500)


def get_code_llm() -> LLM:
    """코드 생성 (Groq). max_tokens=3500 → 파일 1개씩 완성."""
    return get_groq_llm(temperature=0.1, max_tokens=3500)


def get_review_llm() -> LLM:
    """코드 검수 (Groq). max_tokens=2000 → 리뷰 요약에 충분."""
    return get_groq_llm(temperature=0.1, max_tokens=2000)


def get_game_llm() -> LLM:
    """인게임 NPC AI 턴 결정 (Groq). max_tokens=500 → 짧은 액션 결정."""
    return get_groq_llm(temperature=0.7, max_tokens=500)


# 하위 호환
def get_dev_llm() -> LLM:
    return get_groq_llm()


def llm_available() -> bool:
    return bool(_GROQ_KEY or _GEMINI_KEY)
