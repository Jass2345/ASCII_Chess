# Stockfish Placement

1. Download the Stockfish engine that matches your operating system.
2. Extract the archive and place the contents inside `engines/stockfish/` (create the folder if it does not exist).
3. Ensure the engine binary filename contains the word `stockfish` so the launcher can detect it.
4. On macOS/Linux, make the binary executable: `chmod +x engines/stockfish/<binary-name>`.

The application scans the `engines/stockfish/` directory (recursively) for the first matching executable each time it launches. This repository keeps the folder empty by default so you must supply your own engine locally.
