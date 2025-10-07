from __future__ import annotations

import shutil
from typing import Iterable, List

try:
    import chess
except ImportError:  # pragma: no cover - library not installed yet
    chess = None  # type: ignore


UNICODE_PIECES = {
    "P": "♙",
    "N": "♘",
    "B": "♗",
    "R": "♖",
    "Q": "♕",
    "K": "♔",
    "p": "♟",
    "n": "♞",
    "b": "♝",
    "r": "♜",
    "q": "♛",
    "k": "♚",
}

ASCII_PIECES = {
    "P": "P",
    "N": "N",
    "B": "B",
    "R": "R",
    "Q": "Q",
    "K": "K",
    "p": "p",
    "n": "n",
    "b": "b",
    "r": "r",
    "q": "q",
    "k": "k",
}

LIGHT_SQUARE = "·"
DARK_SQUARE = ":"

class AsciiRenderer:
    """Responsible for rendering the CLI experience."""

    def __init__(self, use_unicode: bool = True) -> None:
        self.use_unicode = use_unicode and self._supports_unicode()

    def _supports_unicode(self) -> bool:
        # If running in a terminal that cannot print chess glyphs reliably, fall back.
        try:
            "♔".encode("utf-8")
        except UnicodeEncodeError:
            return False
        return True

    def clear(self) -> None:
        # ANSI clear screen
        print("\033[2J\033[H", end="")

    def render_title_screen(self) -> None:
        self.clear()
        term = shutil.get_terminal_size((80, 24))
        pawn_art_raw = (
            """⠀⠀⠀⡀⠀⠄⠀⠀⢀⠀⠀⡀⠀⠠⠀⠀⠀⡀⠀⠄⠀⠀⠄⠀⠀⢀⠀⠠⠀⠀
            ⠁⠀⠄⠀⠀⠄⠈⠀⡀⠀⠄⠀⠠⠀⠀⠁⡀⠀⠀⠄⠈⠀⡀⠈⢀⠀⠀⠠⠀⠁
            ⠐⠀⠀⠐⠀⠀⠐⠀⠀⠄⠀⢐⡰⡜⡝⡵⣲⢔⠀⠀⠐⠀⠀⠄⠀⠀⠂⠀⠐⠀
            ⠄⠀⠁⡀⠈⠀⠠⠈⠀⠀⠐⣸⢜⢜⢜⢎⡗⡯⣇⠁⢀⠀⠁⡀⠐⠀⡀⠁⠀⠄
            ⠀⠀⠂⠀⠀⠂⠀⠄⠀⠁⢀⢺⡪⡮⣪⣳⢽⣝⡇⠄⠀⠠⠀⠀⠠⠀⠀⠠⠀⠠
            ⠀⠂⠀⠈⢀⠀⠁⢀⠀⠁⠀⠀⡽⡽⣳⡽⣗⣏⠀⠀⠐⠀⠀⠂⠀⠀⠂⢀⠀⠂
            ⠄⠀⠁⠠⠀⠀⠄⠀⠀⠄⠁⠙⠊⡯⣾⣺⡵⠋⠃⠁⢀⠈⠀⠠⠈⠀⡀⠀⠀⠄
            ⠀⠐⠀⢀⠀⠂⠀⠐⠀⠀⠄⠀⠀⣟⢼⣞⣿⠀⠀⠂⠀⠀⠄⠀⠐⠀⠀⠐⠀⠀
            ⠁⠀⠄⠀⢀⠀⠈⢀⠀⠁⠀⠈⢐⡽⣜⣞⣿⡀⠠⠀⠈⢀⠀⠈⢀⠀⠁⢀⠈⠀
            ⠐⠀⠀⠐⠀⠀⠐⠀⠀⠄⠈⢀⢮⢯⢞⡾⡽⣧⡀⠀⠂⠀⠀⠐⠀⠀⠄⠀⠀⠂
            ⡀⠀⠁⡀⠀⠁⡀⠐⠀⢀⠐⣨⢿⢽⡽⣾⣻⢷⡅⢀⠠⠀⠁⡀⠈⠀⡀⠈⢀⠀
            ⠀⠀⠂⠀⠀⠂⠀⠠⠀⣖⡯⣺⢝⣗⢯⢗⡽⣳⢯⣗⡷⠀⠀⠀⠠⠀⠀⠠⠀⠀
            ⠈⠀⡀⠈⠀⡀⠂⠀⠀⠺⠽⠽⣝⣞⡽⡽⣝⢷⠯⠷⠛⠀⠈⠀⡀⠀⠂⠀⠐⠀
            ⠄⠀⠀⠄⠀⠀⠄⠈⠀⡀⠀⠄⠀⠀⢀⠀⠀⢀⠀⠠⠀⠈⠀⡀⠀⠠⠀⠁⠀⠄
            ⢀⠀⠁⠀⠐⠀⠀⠐⠀⠀⠠⠀⠐⠀⠀⠀⠂⠀⠀⠄⠀⠂⠁⠀⠐⠀⠀⠐⠀⠀"""
        ).strip("\n")
        pawn_art = pawn_art_raw.splitlines()
        centered = [line.center(term.columns) for line in pawn_art]
        print("\n".join(centered))
        print("\n" + "< ASCII Chess >".center(term.columns))
        print("".center(term.columns, "="))

    def render_board(
        self,
        board: "chess.Board",
        move_history: Iterable[str],
        enemy_rating: int,
        enemy_status: str,
        prompt_text: str,
        input_buffer: str = "",
    ) -> None:
        self.clear()
        term = shutil.get_terminal_size((100, 30))
        colsplit = int(term.columns * 0.75)
        rowsplit = int(term.lines * 0.8)

        board_str = self._board_to_text(board)
        moves_str = self._moves_to_text(move_history)
        board_lines = board_str.splitlines()
        moves_lines = moves_str.splitlines()

        padded_board_lines = [line.ljust(colsplit) for line in board_lines]
        padded_moves_lines = [line for line in moves_lines]

        max_lines = max(len(padded_board_lines), len(padded_moves_lines))
        padded_board_lines.extend(["".ljust(colsplit)] * (max_lines - len(padded_board_lines)))
        padded_moves_lines.extend([""] * (max_lines - len(padded_moves_lines)))

        top_lines: List[str] = []
        for left, right in zip(padded_board_lines, padded_moves_lines):
            top_lines.append(f"{left} {right}")

        info_lines = [
            f"Enemy rating (Elo): {enemy_rating}",
            prompt_text,
            f"Input: {input_buffer}",
            "",
        ]
        if enemy_status:
            info_lines.append(f"Enemy: {enemy_status}")
        top_height = len(top_lines)
        total_lines = top_height + len(info_lines)

        if rowsplit > 0 and total_lines > rowsplit:
            top_lines = top_lines[:rowsplit]

        print("\n".join(top_lines))
        print("\n".join(info_lines))

    def _board_to_text(self, board: "chess.Board") -> str:
        if chess is None:
            raise RuntimeError("python-chess is required for board rendering.")

        files = "  a b c d e f g h"
        lines = [files]
        for rank in range(7, -1, -1):
            row = [str(rank + 1)]
            for file in range(8):
                square = chess.square(file, rank)
                piece = board.piece_at(square)
                if piece is None:
                    row.append(LIGHT_SQUARE if (rank + file) % 2 else DARK_SQUARE)
                else:
                    symbol = piece.symbol()
                    row.append(self._piece_symbol(symbol))
            row.append(str(rank + 1))
            lines.append(" ".join(row))
        lines.append(files)
        return "\n".join(lines)

    def _piece_symbol(self, symbol: str) -> str:
        mapping = UNICODE_PIECES if self.use_unicode else ASCII_PIECES
        return mapping.get(symbol, symbol)

    def _moves_to_text(self, moves: Iterable[str]) -> str:
        lines = ["Moves (White/Black):"]
        move_pairs = []
        moves_list = list(moves)
        for idx in range(0, len(moves_list), 2):
            white = moves_list[idx]
            black = moves_list[idx + 1] if idx + 1 < len(moves_list) else ""
            move_pairs.append(f"{idx // 2 + 1:>2}. {white:<7} {black:<7}")
        lines.extend(move_pairs if move_pairs else ["<no moves yet>"])
        return "\n".join(lines)
