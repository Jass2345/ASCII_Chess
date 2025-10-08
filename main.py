from __future__ import annotations

import argparse
import sys

from ascii_chess.deps import collect_dependency_status


def parse_args(argv: list[str]) -> argparse.Namespace:
    # 명령줄 인자 정의 및 파싱
    parser = argparse.ArgumentParser(description="ASCII CLI Chess vs Stockfish")
    parser.add_argument(
        "--engine-path",
        help="Path to Stockfish executable (defaults to checking PATH).",
        default=None,
    )
    parser.add_argument(
        "--min-rating",
        type=int,
        default=1350,
        help="Minimum Elo allowed for the AI (default: 1350, Stockfish limit).",
    )
    parser.add_argument(
        "--max-rating",
        type=int,
        default=2850,
        help="Maximum Elo allowed for the AI (default: 2850).",
    )
    parser.add_argument(
        "--think-time",
        type=float,
        default=0.5,
        help="Default thinking time per AI move in seconds (default: 0.5).",
    )
    parser.add_argument(
        "--ascii-only",
        action="store_true",
        help="Force ASCII board rendering instead of Unicode chess glyphs.",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run the classic CLI experience instead of the GUI.",
    )
    parser.add_argument(
        "--no-auto-install",
        action="store_true",
        help="Skip automatic installation attempt for python-chess.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    # 실행 환경 점검 후 CLI 또는 GUI 진입점을 수행
    args = parse_args(argv or sys.argv[1:])

    deps = collect_dependency_status(
        engine_path=args.engine_path,
        auto_install=not args.no_auto_install,
    )

    if not deps.python_chess_ok:
        print(
            "python-chess could not be imported. "
            "Install it manually with `pip install python-chess` and re-run.",
            file=sys.stderr,
        )
        return 1

    if deps.stockfish_path is None:
        hint = (
            "Stockfish executable not found. Download it from "
            "https://stockfishchess.org/download/ and provide the path with "
            "--engine-path /path/to/stockfish."
        )
        print(hint, file=sys.stderr)
        return 1

    from ascii_chess.ai import EngineConfig
    from ascii_chess.game import GameController
    from ascii_chess.renderer import AsciiRenderer

    engine_config = EngineConfig(
        executable_path=deps.stockfish_path,
        min_rating=args.min_rating,
        max_rating=args.max_rating,
        default_think_time=args.think_time,
    )

    if args.cli:
        renderer = AsciiRenderer(use_unicode=not args.ascii_only)
        try:
            controller = GameController(renderer=renderer, engine_config=engine_config)
        except RuntimeError as exc:
            print(f"Failed to initialise game: {exc}", file=sys.stderr)
            return 1
        controller.run()
        return 0

    try:
        import tkinter as tk
    except Exception as exc:  # pragma: no cover - Tk may be missing
        print(f"Failed to load Tkinter: {exc}", file=sys.stderr)
        return 1

    from ascii_chess.gui import ChessGUI

    root = tk.Tk()
    ChessGUI(root, engine_config=engine_config, use_unicode=not args.ascii_only)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
