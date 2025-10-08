# ASCII Chess

터미널 또는 GUI 환경에서 Stockfish 엔진과 대국할 수 있는 ASCII 기반 체스 프로그램입니다. 플레이어는 SAN 형태로 수를 입력하며, Enemy(Stockfish)와 번갈아 대국합니다.

## 주요 특징
- 인트로 화면에서 Enemy Elo를 입력 후 게임 시작
- GUI(기본)와 CLI(`--cli`) 모드 지원
- `ff`(기권), `quit`(즉시 종료), `/win`, `/lose`, `/draw`(테스트용) 명령 지원
- Enemy가 둔 마지막 기물을 깜빡임 효과로 강조

## 준비 사항
- Python 3.10 이상
- `python-chess` 라이브러리
- Stockfish 실행 파일 (PATH 등록 또는 `--engine-path` 지정)

```bash
pip install python-chess
```

Stockfish는 [공식 다운로드 페이지](https://stockfishchess.org/download/)에서 받아 사용 환경에 맞게 배치하세요. `engines/` 폴더에 각 플랫폼용 실행 파일을 넣으면 자동으로 탐지합니다.

## 실행 방법

```bash
python main.py [옵션]
```

### 자주 쓰는 옵션
- `--engine-path /path/to/stockfish` : Stockfish 실행 파일 경로
- `--think-time 1.0` : Enemy 한 수당 사고 시간(초)
- `--ascii-only` : 유니코드 대신 ASCII 기물 사용
- `--cli` : CLI 모드 실행 (미지정 시 GUI)
- `--min-rating`, `--max-rating` : 입력 가능한 Elo 범위 조정
- `--no-auto-install` : `python-chess` 자동 설치 시도 비활성화

## 조작 방법
- 일반 수는 SAN 형식으로 입력 (예: `Nf3`, `O-O`)
- `ff` : 플레이어 기권
- `quit` : 즉시 게임 종료
- `/win`, `/lose`, `/draw` : 개발자용 강제 결과 명령

## 코드 구조
- `main.py` : CLI/GUI 진입점
- `ascii_chess/game.py` : CLI 게임 루프 및 입력 처리
- `ascii_chess/gui.py` : Tkinter 기반 GUI
- `ascii_chess/renderer.py` : CLI 텍스트 렌더러
- `ascii_chess/ai.py` : Stockfish 제어 래퍼
- `ascii_chess/deps.py` : 의존성 설치/탐색 유틸리티

