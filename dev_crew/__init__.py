"""
게임 개발 크루 (Game Development Crew)
────────────────────────────────────────
crewAI + Gemini 2.5 Pro 에이전트들이 협업하여 Water Margin Story 게임을 개발한다.

에이전트 구성:
  - 게임 디자이너 : 기능 기획 및 밸런스 설계
  - 게임 개발자  : Python 코드 작성
  - 스토리텔러   : 수호지 세계관 기반 한국어 서사 작성
  - 코드 리뷰어  : 코드 품질 검토 및 개선 제안
"""
from dev_crew.crew import GameDevCrew

__all__ = ["GameDevCrew"]
