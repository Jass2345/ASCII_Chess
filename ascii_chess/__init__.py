from __future__ import annotations

from typing import Any

__all__ = [
    "StockfishAI",
    "EngineConfig",
    "ChessGUI",
]


def __getattr__(name: str) -> Any:
    if name == "StockfishAI":
        from .ai import StockfishAI as _StockfishAI

        return _StockfishAI
    if name == "EngineConfig":
        from .ai import EngineConfig as _EngineConfig

        return _EngineConfig
    if name == "ChessGUI":
        from .gui import ChessGUI as _ChessGUI

        return _ChessGUI
    raise AttributeError(name)
