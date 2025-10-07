from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import List, Optional

try:
    import chess
except ImportError:  # pragma: no cover - handled by dependency check in main
    chess = None  # type: ignore

from .ai import EngineConfig, StockfishAI
from .renderer import ASCII_PIECES, LIGHT_SQUARE, DARK_SQUARE, UNICODE_PIECES
from .taunts import TauntManager


BOARD_FONT = ("Menlo", 18)
MOVE_FONT = ("Menlo", 14)
STATUS_FONT = ("Menlo", 12)
PROMPT_FONT = ("Menlo", 12)


class ChessGUI:
    def __init__(self, root: tk.Tk, engine_config: EngineConfig, use_unicode: bool = True) -> None:
        if chess is None:
            raise RuntimeError("python-chess is required to run the GUI.")

        self.root = root
        self.root.title("ASCII Chess vs Stockfish")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.engine_config = engine_config
        self.ai = StockfishAI(config=self.engine_config)
        self.taunts = TauntManager()
        self.use_unicode = use_unicode

        self.board = chess.Board()
        self.move_history: List[str] = []
        self._awaiting_ai = False
        self._resigned = False

        self._build_widgets()
        self._prompt_rating()
        self._render()

    def _build_widgets(self) -> None:
        main_frame = tk.Frame(self.root, padx=12, pady=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Board display
        self.board_text = tk.Text(
            main_frame,
            width=30,
            height=20,
            font=BOARD_FONT,
            bg="#111",
            fg="#eee",
            state=tk.DISABLED,
        )
        self.board_text.grid(row=0, column=0, rowspan=2, sticky="nsew")

        # Moves display
        moves_frame = tk.Frame(main_frame)
        moves_frame.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        moves_label = tk.Label(moves_frame, text="Moves", font=STATUS_FONT)
        moves_label.pack(anchor="w")

        self.moves_text = tk.Text(
            moves_frame,
            width=24,
            height=18,
            font=MOVE_FONT,
            state=tk.DISABLED,
        )
        self.moves_text.pack(fill=tk.BOTH, expand=True)

        # Status + input
        input_frame = tk.Frame(main_frame)
        input_frame.grid(row=1, column=1, sticky="nsew", padx=(12, 0), pady=(12, 0))

        self.status_label = tk.Label(input_frame, text="Welcome to ASCII Chess!", font=STATUS_FONT)
        self.status_label.pack(anchor="w")

        self.taunt_label = tk.Label(input_frame, text="", font=STATUS_FONT, fg="#888")
        self.taunt_label.pack(anchor="w", pady=(4, 8))

        entry_row = tk.Frame(input_frame)
        entry_row.pack(fill=tk.X)

        self.move_entry = tk.Entry(entry_row, font=PROMPT_FONT)
        self.move_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.move_entry.bind("<Return>", self._on_submit)

        submit_button = tk.Button(entry_row, text="Submit", command=self._on_submit)
        submit_button.pack(side=tk.LEFT, padx=(6, 0))

        help_label = tk.Label(
            input_frame,
            text="Commands: resign, help, quit",
            font=STATUS_FONT,
            fg="#777",
        )
        help_label.pack(anchor="w", pady=(8, 0))

        # Configure grid weights
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(0, weight=4)
        main_frame.rowconfigure(1, weight=1)

    def _prompt_rating(self) -> None:
        rating = simpledialog.askinteger(
            "Set AI Elo",
            "Enter AI Elo (1350-2850, default 1500):",
            parent=self.root,
            minvalue=self.engine_config.min_rating,
            maxvalue=self.engine_config.max_rating,
        )
        if rating is None:
            rating = 1500
        else:
            rating = max(self.engine_config.min_rating, min(rating, self.engine_config.max_rating))
        self.ai.set_rating(rating)
        self.status_label.config(text=f"Playing vs Stockfish ({rating} Elo). Your move!")

    def _on_submit(self, event: Optional[tk.Event] = None) -> None:
        if self._awaiting_ai:
            return
        text = self.move_entry.get().strip()
        if not text:
            return
        self.move_entry.delete(0, tk.END)
        self._handle_player_input(text)

    def _handle_player_input(self, user_input: str) -> None:
        lowered = user_input.lower()
        if lowered == "help":
            messagebox.showinfo(
                "Help",
                "Enter chess moves in SAN (e.g. Nf3, O-O, cxd4).\n"
                "Commands:\n  resign - concede the game\n  quit   - exit the application",
                parent=self.root,
            )
            return
        if lowered == "quit":
            self.root.quit()
            return
        if lowered == "resign":
            self._resigned = True
            self.status_label.config(text="You resigned.")
            self._finish_game("You resigned. Stockfish wins.")
            return

        try:
            move = self.board.parse_san(user_input)
            san = self.board.san(move)
        except ValueError:
            self.status_label.config(text=f"Illegal move: {user_input}")
            return

        self.board.push(move)
        self.move_history.append(san)
        self.status_label.config(text="Stockfish is thinking...")
        self._render()

        if self.board.is_game_over(claim_draw=True):
            self._announce_result()
            return

        self._awaiting_ai = True
        self.root.after(100, self._play_ai_move)

    def _play_ai_move(self) -> None:
        try:
            ai_move = self.ai.choose_move(self.board)
        except Exception as exc:  # pragma: no cover - engine errors are unexpected
            messagebox.showerror("Engine error", str(exc), parent=self.root)
            self._awaiting_ai = False
            return

        san = self.board.san(ai_move)
        self.board.push(ai_move)
        self.move_history.append(san)
        evaluation = self._evaluate(self.board)
        self.taunt_label.config(text=self.taunts.choose(evaluation))
        self.status_label.config(text="Your move.")
        self._awaiting_ai = False
        self._render()

        if self.board.is_game_over(claim_draw=True):
            self._announce_result()

    def _announce_result(self) -> None:
        outcome = self.board.outcome(claim_draw=True)
        if outcome is None:
            result_text = "Game ended prematurely."
        elif outcome.winner is None:
            result_text = "Draw!"
        elif outcome.winner == chess.WHITE:
            result_text = "White wins!"
        else:
            result_text = "Black wins!"

        if self._resigned and outcome is None:
            result_text = "You resigned. Stockfish wins."

        messagebox.showinfo("Game over", result_text, parent=self.root)
        self._ask_play_again()

    def _ask_play_again(self) -> None:
        again = messagebox.askyesno("Play again?", "Would you like to start a new game?", parent=self.root)
        if again:
            self._reset_game()
        else:
            self.root.quit()

    def _reset_game(self) -> None:
        self.board = chess.Board()
        self.move_history.clear()
        self.taunt_label.config(text=self.taunts.choose(0))
        self.status_label.config(text="New game! Your move.")
        self._resigned = False
        self._render()

    def _render(self) -> None:
        board_text = self._board_to_text(self.board)
        moves_text = self._moves_to_text(self.move_history)

        self.board_text.config(state=tk.NORMAL)
        self.board_text.delete("1.0", tk.END)
        self.board_text.insert(tk.END, board_text)
        self.board_text.config(state=tk.DISABLED)

        self.moves_text.config(state=tk.NORMAL)
        self.moves_text.delete("1.0", tk.END)
        self.moves_text.insert(tk.END, moves_text)
        self.moves_text.config(state=tk.DISABLED)

    def _board_to_text(self, board: "chess.Board") -> str:
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
                    row.append(self._piece_symbol(piece.symbol()))
            row.append(str(rank + 1))
            lines.append(" ".join(row))
        lines.append(files)
        return "\n".join(lines)

    def _piece_symbol(self, symbol: str) -> str:
        if self.use_unicode:
            return UNICODE_PIECES.get(symbol, symbol)
        return ASCII_PIECES.get(symbol, symbol)

    def _moves_to_text(self, moves: List[str]) -> str:
        if not moves:
            return "<no moves yet>"
        lines = []
        for idx in range(0, len(moves), 2):
            white = moves[idx]
            black = moves[idx + 1] if idx + 1 < len(moves) else ""
            lines.append(f"{idx // 2 + 1:>2}. {white:<8} {black:<8}")
        return "\n".join(lines)

    def _evaluate(self, board: "chess.Board") -> float:
        values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0,
        }
        total = 0.0
        for piece_type, value in values.items():
            total += len(board.pieces(piece_type, chess.WHITE)) * value
            total -= len(board.pieces(piece_type, chess.BLACK)) * value
        return total

    def _on_close(self) -> None:
        self.ai.close()
        self.root.destroy()
