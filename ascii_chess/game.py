from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

try:
    import chess
except ImportError:  # pragma: no cover - dependency to be installed by user
    chess = None  # type: ignore

from .ai import EngineConfig, StockfishAI
from .renderer import AsciiRenderer


DEFAULT_PROMPT = "Enter move in SAN (e.g. Nf3, O-O, cxd4, ff, help)."


@dataclass
class GameState:
    board: "chess.Board" = field(default_factory=lambda: chess.Board() if chess else None)
    move_history: List[str] = field(default_factory=list)
    undo_stack: List[str] = field(default_factory=list)  # FEN 히스토리
    redo_stack: List[str] = field(default_factory=list)  # REDO용 FEN 스택


class GameController:
    def __init__(
        self,
        renderer: Optional[AsciiRenderer] = None,
        ai: Optional[StockfishAI] = None,
        engine_config: Optional[EngineConfig] = None,
    ) -> None:
        if chess is None:
            raise RuntimeError("python-chess is required to run the game.")
        # 엔진과 렌더러를 준비하고 게임 상태를 초기화한다
        self.renderer = renderer or AsciiRenderer()
        self.ai = ai or StockfishAI(config=engine_config)
        self.state = GameState()
        self.last_message = DEFAULT_PROMPT
        self.enemy_status = ""
        self._running = True
        self._resigned = False
        self._forfeited = False
        self._quit_requested = False
        self._forced_outcome: Optional[str] = None
        # UNDO/REDO 초기 상태 저장
        self.state.undo_stack.append(self.state.board.fen())

    def run(self) -> None:
        # 레이팅 설정부터 재시작 여부 확인까지 전체 게임 흐름을 제어한다
        try:
            while self._running:
                rating = self._prompt_rating()
                self.ai.set_rating(rating)
                aborted = self._start_game_loop()
                if not self._running:
                    break
                if not aborted:
                    self._render()
                    if self._forced_outcome:
                        self._announce_forced_outcome(self._forced_outcome)
                        self._forced_outcome = None
                    else:
                        self._announce_result(self.state.board)
                if not self._prompt_play_again():
                    self._running = False
                else:
                    self._reset_state()
        finally:
            self.ai.close()

    def _prompt_rating(self) -> int:
        # 플레이어에게 Enemy의 레이팅을 입력받는다
        self.renderer.render_title_screen()
        min_rating = self.ai.config.min_rating
        max_rating = self.ai.config.max_rating
        default_rating = self.ai.rating
        while True:
            try:
                rating_str = input(
                    f"Set Enemy Elo ({min_rating}-{max_rating}, default {default_rating}): "
                ).strip()
                if not rating_str:
                    return default_rating
                rating = int(rating_str)
                if min_rating <= rating <= max_rating:
                    return rating
                print(f"Please enter a rating between {min_rating} and {max_rating}.")
            except ValueError:
                print("Rating must be a number.")

    def _start_game_loop(self) -> bool:
        # 플레이어와 Enemy의 번갈아 둔 수를 처리한다
        board = self.state.board
        assert board is not None
        self._resigned = False
        self._forfeited = False
        self._quit_requested = False
        self.last_message = DEFAULT_PROMPT

        while not board.is_game_over(claim_draw=True):
            move = self._prompt_move(board)
            if move is None:
                if self._forced_outcome:
                    forced_messages = {
                        "win": "Player wins!",
                        "lose": "Enemy wins!",
                        "draw": "Draw.",
                    }
                    self.last_message = forced_messages[self._forced_outcome]
                    self.enemy_status = ""
                    return False
                if self._quit_requested:
                    return True
                if self._resigned:
                    self.last_message = "Player forfeited."
                elif not self._running:
                    self.last_message = "Exiting game..."
                else:
                    self.last_message = "Game aborted."
                self.enemy_status = ""
                self._render()
                return True

            # 플레이어 수를 두기 전 상태 저장
            self.state.undo_stack.append(board.fen())
            self.state.redo_stack.clear()  # 새 수를 두면 REDO 스택 초기화
            
            player_san = board.san(move)
            board.push(move)
            self.state.move_history.append(player_san)
            self.last_message = "Enemy is thinking..."
            self.enemy_status = "Calculating..."
            self._render()

            if board.is_game_over(claim_draw=True):
                self.enemy_status = ""
                break

            # AI 수를 두기 전 상태 저장
            self.state.undo_stack.append(board.fen())
            
            ai_move = self.ai.choose_move(board)
            ai_san = board.san(ai_move)
            board.push(ai_move)
            self.state.move_history.append(ai_san)
            self.enemy_status = ""
            self.last_message = DEFAULT_PROMPT

        return False

    def _prompt_move(self, board: "chess.Board") -> Optional["chess.Move"]:
        # 사용자의 입력을 검사해 명령 또는 합법적인 수를 반환한다
        error_message = ""
        while True:
            prompt = error_message or DEFAULT_PROMPT
            self.last_message = prompt
            self._render()
            user_input = input("Player move (or command): ").strip()
            if not user_input:
                error_message = "Please enter a move."
                continue
            lowered = user_input.lower()
            if lowered in {"/win", "/lose", "/draw"}:
                mapping = {"/win": "win", "/lose": "lose", "/draw": "draw"}
                self._forced_outcome = mapping[lowered]
                return None
            if lowered in {"quit", "exit"}:
                self._running = False
                self._quit_requested = True
                return None
            if lowered == "ff":
                self._resigned = True
                self._forfeited = True
                return None
            if lowered == "help":
                print(
                    "\nCommands:\n"
                    "  help    - show this message\n"
                    "  ff      - forfeit the game\n"
                    "  quit    - exit the program immediately\n"
                    "  undo    - undo last move (yours and enemy's)\n"
                    "  redo    - redo previously undone move\n"
                    "Enter chess moves in Standard Algebraic Notation (SAN).\n"
                )
                error_message = ""
                continue
            if lowered == "undo":
                if self._try_undo():
                    error_message = ""
                else:
                    error_message = "Nothing to undo."
                continue
            if lowered == "redo":
                if self._try_redo():
                    error_message = ""
                else:
                    error_message = "Nothing to redo."
                continue
            try:
                move = board.parse_san(user_input)
                return move
            except ValueError:
                error_message = f"Illegal move: {user_input}."

    def _announce_result(self, board: "chess.Board") -> None:
        # 정상 종료된 게임의 결과를 출력한다
        outcome = board.outcome(claim_draw=True)
        if outcome is None:
            if self._resigned:
                print("\nPlayer forfeited. Enemy wins.")
            else:
                print("\nGame ended prematurely.")
            return
        if outcome.winner is None:
            message = "Draw."
        elif outcome.winner == chess.WHITE:
            message = "Player wins!"
        else:
            message = "Enemy wins!"
        print("\n" + message)
        if outcome.termination:
            print(f"Reason: {outcome.termination.name.replace('_', ' ').title()}")
        print(f"Result: {outcome.result()}")

    def _announce_forced_outcome(self, outcome: str) -> None:
        # 개발자 테스트용 강제 결과 메시지를 출력한다
        messages = {
            "win": "Player wins!",
            "lose": "Enemy wins!",
            "draw": "Draw.",
        }
        print("\n" + messages[outcome])

    def _prompt_play_again(self) -> bool:
        # 재시작 여부를 입력받는다
        while True:
            choice = input("Play again? (y/n): ").strip().lower()
            if choice in {"y", "yes"}:
                return True
            if choice in {"n", "no"}:
                return False
            print("Please answer with y or n.")

    def _reset_state(self) -> None:
        # 새 게임을 위한 상태를 초기화한다
        self.state.board = chess.Board()
        self.state.move_history.clear()
        self.state.undo_stack.clear()
        self.state.redo_stack.clear()
        self.state.undo_stack.append(self.state.board.fen())  # 초기 상태 저장
        self.last_message = DEFAULT_PROMPT
        self.enemy_status = ""
        self._running = True
        self._resigned = False
        self._forfeited = False
        self._quit_requested = False

    def _try_undo(self) -> bool:
        # 마지막 플레이어 수와 AI 수를 되돌린다 (2수)
        if len(self.state.undo_stack) < 3:  # 초기 상태 + 플레이어 수 + AI 수
            return False
        
        # 현재 상태를 REDO 스택에 저장 (AI 수)
        if self.state.move_history:
            self.state.redo_stack.append(self.state.move_history[-1])
        
        # AI 수 되돌리기
        self.state.board.pop()
        self.state.undo_stack.pop()
        if self.state.move_history:
            self.state.move_history.pop()
        
        # 플레이어 수도 REDO 스택에 저장
        if self.state.move_history:
            self.state.redo_stack.append(self.state.move_history[-1])
        
        # 플레이어 수 되돌리기
        self.state.board.pop()
        self.state.undo_stack.pop()
        if self.state.move_history:
            self.state.move_history.pop()
        
        self.last_message = "Undone. " + DEFAULT_PROMPT
        return True
    
    def _try_redo(self) -> bool:
        # REDO 스택에서 상태를 복원한다 (2수)
        if len(self.state.redo_stack) < 2:  # 플레이어 수 + AI 수
            return False
        
        # 플레이어 수 REDO
        player_move_san = self.state.redo_stack.pop()
        try:
            player_move = self.state.board.parse_san(player_move_san)
            self.state.undo_stack.append(self.state.board.fen())
            self.state.board.push(player_move)
            self.state.move_history.append(player_move_san)
        except ValueError:
            self.state.redo_stack.append(player_move_san)  # 복원 실패시 되돌림
            return False
        
        # AI 수 REDO
        ai_move_san = self.state.redo_stack.pop()
        try:
            ai_move = self.state.board.parse_san(ai_move_san)
            self.state.undo_stack.append(self.state.board.fen())
            self.state.board.push(ai_move)
            self.state.move_history.append(ai_move_san)
        except ValueError:
            # AI 수 복원 실패시 플레이어 수도 되돌림
            self.state.board.pop()
            self.state.undo_stack.pop()
            self.state.move_history.pop()
            self.state.redo_stack.append(player_move_san)
            self.state.redo_stack.append(ai_move_san)
            return False
        
        self.last_message = "Redone. " + DEFAULT_PROMPT
        return True

    def _render(self) -> None:
        # CLI 렌더러에 현재 상태를 전달한다
        board = self.state.board
        assert board is not None
        self.renderer.render_board(
            board,
            self.state.move_history,
            self.ai.rating,
            self.enemy_status,
            self.last_message,
        )
