# ASCII Chess

Tkinter 기반으로 Stockfish 엔진과 대국하는 GUI 전용 ASCII 체스 애플리케이션입니다. 인트로 화면에서 게임 시작과 테마 설정을 선택하고, 게임 도중에는 SAN 표기법으로 수를 입력해 플레이합니다.

## 주요 기능
- **Menlo 고정 폭 폰트 강제 사용**: `ascii_chess/fonts/menlo-regular.ttf` 경로에 폰트를 배치하면 프로그램 시작 시 자동 로드됩니다.
- **인트로 선택 메뉴**: `↑ / ↓` 키로 `Game Start` 또는 `Theme Settings`를 고르고 `Enter`로 확정합니다.
- **테마 커스터마이즈**: 보드/기물 색상을 목록에서 선택하면 좌측 보드에 즉시 미리보기와 함께 적용됩니다.
- **힌트 하이라이트**: `hint` 명령을 입력하면 추천 수의 출발/도착 칸이 붉은색으로 점멸합니다.
- **Undo/Redo/Hint 문자 명령**: GUI 버튼과 단축키 없이 입력창에 `undo`, `redo`, `hint`를 직접 입력해 사용합니다.
- **시간 모드 선택**: 10분(1), 3분(2), 무제한(3) 세 가지 모드 중 하나를 선택해 플레이합니다.

## 준비 사항
- Python 3.10 이상
- `pip install python-chess`
- Stockfish 실행 파일 (PATH 등록 또는 실행 경로 지정)
- Menlo-Regular.ttf 폰트 파일을 `ascii_chess/fonts/menlo-regular.ttf`로 복사

## 실행 방법

```bash
python main.py [옵션]
```

### 지원 옵션
- `--engine-path /path/to/stockfish` : Stockfish 실행 파일 경로 지정
- `--think-time 1.0` : AI 한 수당 기본 사고 시간(초)
- `--ascii-only` : 유니코드 대신 ASCII 기물 렌더링
- `--min-rating`, `--max-rating` : 허용 Elo 범위 재설정
- `--no-auto-install` : `python-chess` 자동 설치 시도 비활성화

## 조작 안내
- 인트로: `↑ / ↓`로 옵션 이동, `Enter`로 선택
- 테마 메뉴: `↑ / ↓`로 항목 이동, `Enter`로 적용, `Esc`로 이전 단계로 복귀
- 게임 시작: `Game Start` → Enemy Elo 입력 → 시간 모드 번호(1/2/3) 선택
- 게임 중 수 입력: SAN 표기(`Nf3`, `O-O`, `cxd4` 등)
- 특수 명령: `ff`(기권), `quit`(즉시 종료), `undo`(직전 양측 수 되돌리기), `redo`(되돌린 수 재적용), `hint`(추천 수 표시)

## 코드 구조
- `main.py` : GUI 실행 진입점
- `ascii_chess/gui.py` : Tkinter GUI와 테마/게임 로직
- `ascii_chess/ai.py` : Stockfish 제어 래퍼 및 힌트 제공
- `ascii_chess/deps.py` : 의존성 확인 및 Stockfish 탐색 유틸리티
- `ascii_chess/fonts/` : Menlo 폰트 보관 경로
