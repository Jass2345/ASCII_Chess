Place platform-specific Stockfish binaries (or their extracted folders) in this
directory so the launcher can auto-detect them.

Options:
- macOS: copy the extracted folder here and rename it to `stockfish-macos` or
  drop the binary itself with that name. Remember to grant execute permission
  via `chmod +x engines/stockfish-macos*`.
- Windows: copy the extracted folder and rename it to `stockfish-windows` (or
  the binary to `stockfish-windows.exe`). Any `.exe` containing "stockfish" in
  its name inside the folder will be detected.

The repo ignores files under `engines/stockfish*`, so each developer can place
their own binaries locally without affecting version control.
