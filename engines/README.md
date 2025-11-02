# Stockfish Placement

1. Download the Stockfish engine that matches your operating system.
2. Extract the archive and place the contents inside `engines/stockfish/` (create the folder if it does not exist).
3. Ensure the engine binary filename contains the word `stockfish` so the launcher can detect it.  
   다른 폴더/실행 파일이라도 이름에 `stockfish`가 포함돼 있으면 자동 탐색 대상입니다.
4. On macOS/Linux, make the binary executable: `chmod +x engines/stockfish/<binary-name>`.

The application scans `engines/stockfish/` first and then checks other `engines/` items whose names contain `stockfish`. This repository keeps the folder empty by default so you must supply your own engine locally.
