# ASCII Chess CLI

HNU CE vibe coding project - CLI ASCII Chess / 윤여명, 정재석, 지민우

ASCII 기반 터미널 체스 게임으로, 사용자가 입력한 레이팅으로 설정된 Stockfish AI와 SAN(Smith Algebraic Notation) 형식으로 대국할 수 있도록 설계된 파이썬 프로젝트입니다.

## 특징
- 프로그램 시작 시 아스키 아트 소개 화면과 Enemy 레이팅 입력
- 체스판(왼쪽 3/4) + 기보 기록(오른쪽) + 입력 영역(하단) 구성
- `♔♕♖♗♘♙♚♛♜♝♞♟` 유니코드 기물을 기본 사용 (옵션으로 ASCII 대체)
- 정규 체스 규칙 지원(`python-chess`) 및 Stockfish 엔진 연동
- Player vs Enemy 고정 호칭, `ff`(기권)/`quit`(즉시 종료) 커맨드 지원

## 준비물
- Python 3.10 이상 권장
- [python-chess](https://pypi.org/project/chess/) 라이브러리
- Stockfish 엔진 바이너리 (PATH 등록, 실행 경로 지정 또는 `engines/` 폴더에 배치)

```bash
pip install python-chess
```

Stockfish 바이너리는 [공식 배포 페이지](https://stockfishchess.org/download/)에서 시스템에 맞게 다운로드한 뒤, 실행 권한을 부여하고 PATH에 추가하거나 실행 경로를 기억해 두세요.

macOS와 Windows만 사용한다면 다음과 같이 “무설치” 구성이 가능합니다.

1. `engines/` 폴더에 각 플랫폼용 Stockfish 압축을 풀고 나온 폴더 전체를 옮긴 뒤 이름을 `stockfish-macos`, `stockfish-windows`처럼 구분합니다. (단일 실행 파일만 있다면 파일 이름을 그대로 사용해도 됩니다.)
2. macOS 바이너리에는 `chmod +x`로 실행 권한을 부여합니다.
3. 이 폴더는 `.gitignore`에 포함돼 있으므로 각 개발자가 자신의 바이너리만 넣어두면 됩니다.
4. 런타임에 플랫폼을 확인해 해당 폴더 안에서 `stockfish` 실행 파일을 찾아 자동으로 사용합니다. 찾지 못한 경우에만 `--engine-path` 또는 PATH 검색 결과를 사용합니다.

## 실행 방법

```bash
python main.py [옵션]
```

사용 가능한 주요 옵션:
- `--engine-path /path/to/stockfish` : Stockfish 실행 파일 경로
- `--think-time 1.0` : AI 한 수당 사고 시간(초)
- `--ascii-only` : 유니코드 대신 ASCII 기물 사용 (GUI/CLI 공통)
- `--cli` : 기존 CLI 모드로 실행 (기본값은 GUI)
- `--min-rating`, `--max-rating` : 입력 가능한 레이팅 범위 조정
- `--no-auto-install` : `python-chess` 자동 설치 시도를 건너뜀

프로그램 실행 후:
1. 의존성 점검 단계에서 `python-chess` 미설치 시 자동 설치를 시도하고, Stockfish 경로가 없으면 안내 메시지를 표시합니다. `engines/` 폴더에 플랫폼별 바이너리를 넣어두면 자동으로 감지합니다.
2. GUI 모드에서는 실행 직후 Enemy 레이팅을 입력하고, 좌측 보드와 우측 기보·입력창에서 게임을 진행합니다.
3. CLI 모드(`python main.py --cli`)에서는 SAN 형식으로 수를 입력하며 `ff`, `quit` 등의 명령을 바로 사용할 수 있습니다.
4. 게임 종료 시 결과가 표시되면 재도전 여부를 선택하거나 종료합니다.

## 개발 메모
- `ascii_chess/renderer.py` : CLI 출력 레이아웃 & 보드 렌더링 로직
- `ascii_chess/gui.py` : Tkinter 기반 GUI 화면 구성 및 이벤트 루프
- `ascii_chess/game.py` : CLI 게임 루프, 입력 처리, 결과 안내
- `ascii_chess/ai.py` : Stockfish 래퍼 및 레이팅 설정
- `ascii_chess/deps.py` : 의존성 자동 확인 및 `python-chess` 설치 시도
- `engines/` : Windows/macOS용 Stockfish 바이너리를 두면 자동 감지됨

향후 확장 아이디어:
- AI와의 분석 모드, PGN 저장 기능, 퍼포먼스 로그 등
- 시간 제한 모드 혹은 하이라이트 애니메이션 추가
