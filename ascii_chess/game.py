from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

try:
    import chess
except ImportError:  # pragma: no cover - dependency to be installed by user
    chess = None  # type: ignore

from .ai import EngineConfig, StockfishAI
from .renderer import AsciiRenderer
from .taunts import TauntManager


DEFAULT_PROMPT = "Enter move in SAN (e.g. Nf3, O-O, cxd4, resign, help)."


@dataclass
class GameState:
    board: "chess.Board" = field(default_factory=lambda: chess.Board() if chess else None)
    move_history: List[str] = field(default_factory=list)


class GameController:
    def __init__(
        self,
        renderer: Optional[AsciiRenderer] = None,
        ai: Optional[StockfishAI] = None,
        taunts: Optional[TauntManager] = None,
        engine_config: Optional[EngineConfig] = None,
    ) -> None:
        if chess is None:
            raise RuntimeError("python-chess is required to run the game.")
        self.renderer = renderer or AsciiRenderer()
        self.ai = ai or StockfishAI(config=engine_config)
        self.taunts = taunts or TauntManager()
        self.state = GameState()
        self.last_message = DEFAULT_PROMPT
        self._running = True
        self._resigned = False

    def run(self) -> None:
        try:
            while self._running:
                rating = self._prompt_rating()
                self.ai.set_rating(rating)
                aborted = self._start_game_loop()
                if not self._running:
                    break
                if not aborted:
                    self._render()
                    self._announce_result(self.state.board)
                if not self._prompt_play_again():
                    self._running = False
                else:
                    self._reset_state()
        finally:
            self.ai.close()

    def _prompt_rating(self) -> int:
        self.renderer.render_title_screen()
        while True:
            try:
                rating_str = input("Set AI Elo (800-2850, default 1500): ").strip()
                if not rating_str:
                    return 1500
                rating = int(rating_str)
                if 800 <= rating <= 2850:
                    return rating
                print("Please enter a rating between 800 and 2850.")
            except ValueError:
                print("Rating must be a number.")

    def _start_game_loop(self) -> bool:
        board = self.state.board
        assert board is not None
        self._resigned = False
        self.last_message = DEFAULT_PROMPT

        while not board.is_game_over(claim_draw=True):
            move = self._prompt_move(board)
            if move is None:
                if self._resigned:
                    self.last_message = "You resigned."
                elif not self._running:
                    self.last_message = "Exiting game..."
                else:
                    self.last_message = "Game aborted."
                self._render()
                return True

            player_san = board.san(move)
            board.push(move)
            self.state.move_history.append(player_san)
            self.last_message = "AI is thinking..."
            self._render()

            if board.is_game_over(claim_draw=True):
                break

            ai_move = self.ai.choose_move(board)
            ai_san = board.san(ai_move)
            board.push(ai_move)
            self.state.move_history.append(ai_san)
            evaluation = self._evaluate(board)
            self.taunts.choose(evaluation)
            self.last_message = DEFAULT_PROMPT

        return False

    def _prompt_move(self, board: "chess.Board") -> Optional["chess.Move"]:
        error_message = ""
        while True:
            prompt = error_message or DEFAULT_PROMPT
            self.last_message = prompt
            self._render()
            user_input = input("Your move (or command): ").strip()
            if not user_input:
                error_message = "Please enter a move."
                continue
            lowered = user_input.lower()
            if lowered in {"quit", "exit"}:
                self._running = False
                return None
            if lowered == "resign":
                self._resigned = True
                return None
            if lowered == "help":
                print(
                    "\nCommands:\n"
                    "  help    - show this message\n"
                    "  resign  - concede the game\n"
                    "  quit    - exit the program\n"
                    "Enter chess moves in Standard Algebraic Notation (SAN).\n"
                )
                error_message = ""
                continue
            try:
                move = board.parse_san(user_input)
                return move
            except ValueError:
                error_message = f"Illegal move: {user_input}."

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

    def _announce_result(self, board: "chess.Board") -> None:
        outcome = board.outcome(claim_draw=True)
        if outcome is None:
            if self._resigned:
                winner = "Black" if board.turn == chess.WHITE else "White"
                print(f"\nYou resigned. {winner} wins by resignation.")
            else:
                print("\nGame ended prematurely.")
            return
        if outcome.winner is None:
            message = "Game drawn."
        elif outcome.winner == chess.WHITE:
            message = "White wins!"
        else:
            message = "Black wins!"
        print("\n" + message)
        if outcome.termination:
            print(f"Reason: {outcome.termination.name.replace('_', ' ').title()}")
        print(f"Result: {outcome.result()}")

    def _prompt_play_again(self) -> bool:
        while True:
            choice = input("Play again? (y/n): ").strip().lower()
            if choice in {"y", "yes"}:
                return True
            if choice in {"n", "no"}:
                return False
            print("Please answer with y or n.")

    def _reset_state(self) -> None:
        self.state.board = chess.Board()
        self.state.move_history.clear()
        self.taunts.choose(0)
        self.last_message = DEFAULT_PROMPT
        self._running = True
        self._resigned = False

    def _render(self) -> None:
        board = self.state.board
        assert board is not None
        self.renderer.render_board(
            board,
            self.state.move_history,
            self.ai.rating,
            self.taunts.last,
            self.last_message,
        )
