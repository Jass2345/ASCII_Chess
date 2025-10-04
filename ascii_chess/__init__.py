"""ASCII Chess package scaffolding for CLI gameplay against Stockfish."""

from __future__ import annotations

from typing import Any

__all__ = [
    "GameController",
    "AsciiRenderer",
    "StockfishAI",
]


def __getattr__(name: str) -> Any:
    if name == "GameController":
        from .game import GameController as _GameController

        return _GameController
    if name == "AsciiRenderer":
        from .renderer import AsciiRenderer as _AsciiRenderer

        return _AsciiRenderer
    if name == "StockfishAI":
        from .ai import StockfishAI as _StockfishAI

        return _StockfishAI
    raise AttributeError(name)
