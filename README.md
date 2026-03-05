# 水滸傳: 천명의 맹세

crewAI 기반의 수호지 전략 게임 — 고구를 타도하고 송나라를 구하라!

## 게임 개요

108 호한 중 하나를 선택해 고구(高俅)를 추적하고 타도하는 턴 기반 전략 게임입니다.  
금나라의 침공으로 송이 멸망하기 전에 고구를 잡아야 합니다. 타임어택과 탐색 요소를 결합했습니다.

**핵심 규칙**
- 최대 30턴 이내에 고구를 잡으면 승리
- 턴마다 왕조 안정도가 감소하며, 안정도가 0이 되거나 제한 턴을 넘기면 패배
- 마을을 돌며 단서(clue)를 쌓고, 단서 3 이상인 마을에서 고구와 조우 시 전투 가능

## 기술 스택

| 라이브러리 | 역할 |
|-----------|------|
| [crewAI](https://crewai.com) | AI NPC / 고구 행동 에이전트 |
| [Rich](https://rich.readthedocs.io) | 터미널 UI |
| [Pydantic v2](https://docs.pydantic.dev) | 게임 상태 직렬화 |
| PyYAML | 영웅·마을·이벤트 데이터 설정 |

## 프로젝트 구조

```
water-margin-story/
├── agents/          # crewAI 에이전트 (고구, NPC 영웅, 군사 오용)
├── tasks/           # crewAI 태스크 (이동·전투·정보수집)
├── models/          # Pydantic 데이터 모델 (Hero, Town, GameState…)
├── game/            # 게임 엔진, 턴 매니저, 이벤트 시스템
├── config/          # YAML 설정 (heroes.yaml, towns.yaml, events.yaml)
├── tools/           # crewAI 도구 (이동, 전투, 조사)
├── ui/              # Rich 기반 터미널 UI
└── main.py          # 진입점
```

## 빠른 시작

### 1. 환경 설정

```bash
cd ~/git/water-margin-story
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. API 키 설정

```bash
cp .env.example .env
# .env 파일에 OPENAI_API_KEY 입력
```

> crewAI 에이전트는 LLM을 사용합니다. OpenAI 외에도 Anthropic, Groq 등을 지원합니다.

### 3. 실행

```bash
python main.py
```

## 게임 플레이

1. 영웅 선택 화면에서 108 호한 중 한 명을 선택
2. 각 턴에 **이동 / 정보 수집 / 휴식 / 턴 종료** 중 행동 선택 (기본 3 AP)
3. 단서를 쌓아 고구의 위치를 파악한 뒤 최후 대결
4. 왕조 안정도 바를 주시하며 남은 턴을 계획적으로 사용

## 멀티플레이어 확장 계획

- `GameState` 가 완전 직렬화(Pydantic)되어 있어 네트워크 동기화 준비 완료
- `player_ids` 리스트로 복수 플레이어 등록 가능
- `is_player_controlled` / `player_id` 필드로 플레이어·AI 분리

## 개발 현황

- [x] 게임 엔진 기본 프레임
- [x] 영웅·마을·이벤트 YAML 설정
- [x] Rich 터미널 UI
- [x] crewAI 에이전트·태스크·도구 뼈대
- [ ] crewAI LLM 에이전트 실제 연동 (AI 턴에 에이전트 호출)
- [ ] 세이브·로드 기능
- [ ] 멀티플레이어 소켓 레이어
