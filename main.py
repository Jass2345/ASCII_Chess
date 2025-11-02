from __future__ import annotations

import argparse
import sys

from ascii_chess.deps import collect_dependency_status


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ASCII Chess GUI vs Stockfish")
    parser.add_argument("--engine-path", default=None, help="Path to Stockfish executable.")
    parser.add_argument("--min-rating", type=int, default=1350, help="Minimum Stockfish Elo.")
    parser.add_argument("--max-rating", type=int, default=2850, help="Maximum Stockfish Elo.")
    parser.add_argument("--think-time", type=float, default=0.5, help="Default think time per AI move.")
    parser.add_argument("--ascii-only", action="store_true", help="Use ASCII pieces instead of Unicode.")
    parser.add_argument("--no-auto-install", action="store_true", help="Skip python-chess auto-installation.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    deps = collect_dependency_status(
        engine_path=args.engine_path,
        auto_install=not args.no_auto_install,
    )

    if not deps.python_chess_ok:
        print(
            "python-chess could not be imported. Install it manually with `pip install python-chess` and re-run.",
            file=sys.stderr,
        )
        return 1

    if deps.stockfish_path is None:
        hint = (
            "Stockfish executable not found. Download it from https://stockfishchess.org/download/ "
            "and provide the path with --engine-path /path/to/stockfish."
        )
        print(hint, file=sys.stderr)
        return 1

    try:
        import tkinter as tk
    except Exception as exc:
        print(f"Failed to load Tkinter: {exc}", file=sys.stderr)
        return 1

    from ascii_chess.ai import EngineConfig
    from ascii_chess.gui import ChessGUI

    engine_config = EngineConfig(
        executable_path=deps.stockfish_path,
        min_rating=args.min_rating,
        max_rating=args.max_rating,
        default_think_time=args.think_time,
    )

    root = tk.Tk()
    ChessGUI(root, engine_config=engine_config, use_unicode=not args.ascii_only)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
