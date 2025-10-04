from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Optional

try:
    import chess
    import chess.engine
except ImportError:  # pragma: no cover - optional dependency for scaffolding
    chess = None  # type: ignore


DEFAULT_MIN_RATING = 800
DEFAULT_MAX_RATING = 2850
DEFAULT_TIME = 0.5


@dataclass
class EngineConfig:
    executable_path: Optional[str] = None
    min_rating: int = DEFAULT_MIN_RATING
    max_rating: int = DEFAULT_MAX_RATING
    default_think_time: float = DEFAULT_TIME


class StockfishAI:
    """Thin wrapper around the Stockfish engine controlled through python-chess."""

    def __init__(self, config: EngineConfig | None = None) -> None:
        if chess is None:
            raise RuntimeError("python-chess is required for Stockfish integration.")

        self.config = config or EngineConfig()
        self._engine = self._launch_engine(self.config.executable_path)
        self._rating = max(self.config.min_rating, min(1500, self.config.max_rating))
        self.set_rating(self._rating)

    def _launch_engine(self, executable_path: Optional[str]):
        candidate = executable_path or shutil.which("stockfish")
        if not candidate:
            raise FileNotFoundError(
                "Unable to locate Stockfish executable. Provide EngineConfig.executable_path or add it to PATH."
            )
        return chess.engine.SimpleEngine.popen_uci(candidate)

    @property
    def rating(self) -> int:
        return self._rating

    def set_rating(self, rating: int) -> None:
        rating = max(self.config.min_rating, min(rating, self.config.max_rating))
        self._rating = rating
        try:
            self._engine.configure({
                "UCI_LimitStrength": True,
                "UCI_Elo": rating,
            })
        except chess.engine.EngineError as exc:  # pragma: no cover - depends on binary build
            raise RuntimeError(f"Failed to configure Stockfish: {exc}") from exc

    def choose_move(self, board: "chess.Board", think_time: Optional[float] = None) -> "chess.Move":
        if chess is None:
            raise RuntimeError("python-chess is required for Stockfish integration.")
        limit = chess.engine.Limit(time=think_time or self.config.default_think_time)
        result = self._engine.play(board, limit=limit)
        return result.move

    def close(self) -> None:
        try:
            self._engine.quit()
        except Exception:  # pragma: no cover - cleanup best effort
            pass

    def __enter__(self) -> "StockfishAI":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
