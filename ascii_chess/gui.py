from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import List, Optional

try:
    import chess
except ImportError:  # pragma: no cover - handled by dependency check in main
    chess = None  # type: ignore

from .ai import EngineConfig, StockfishAI
from .renderer import ASCII_PIECES, LIGHT_SQUARE, DARK_SQUARE, UNICODE_PIECES


# 고정폭 폰트 사용으로 체크판 자간 정렬
BOARD_FONT = ("Courier New", 28)
MOVE_FONT = ("Courier New", 12)
STATUS_FONT = ("Arial", 11)
PROMPT_FONT = ("Courier New", 11)

ENEMY_BASE_COLOR = "#888"
ENEMY_HIGHLIGHT_COLOR = "#ffcc33"
ENEMY_BLINK_INTERVAL_MS = 350
ENEMY_BLINK_TOGGLES = 6  # 점멸 횟수 (약 세 번)


class ChessGUI:
    def __init__(self, root: tk.Tk, engine_config: EngineConfig, use_unicode: bool = True) -> None:
        if chess is None:
            raise RuntimeError("python-chess is required to run the GUI.")

        self.root = root
        self.root.title("ASCII Chess")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.engine_config = engine_config
        self.ai = StockfishAI(config=self.engine_config)
        self.use_unicode = use_unicode
        self.board = chess.Board()
        self.move_history: List[str] = []
        self.undo_stack: List[str] = [self.board.fen()]  # FEN 히스토리
        self.redo_stack: List[str] = []  # REDO용 FEN 스택
        self._awaiting_ai = False
        self._resigned = False
        self._forfeited = False
        self._enemy_highlight_square: Optional[int] = None
        self._enemy_blink_visible = True
        self._enemy_blink_job: Optional[str] = None
        self._enemy_blink_remaining = 0
        self._is_rendering = False
        self._ai_job: Optional[str] = None
        self._focus_binding: Optional[str] = None
        self._closing = False
        self._build_widgets()
        self._configure_geometry()
        self._bring_to_front()
        self._setup_keybindings()
        self._show_intro_screen()

    def _build_widgets(self) -> None:
        # 보드 영역과 기보·입력 영역을 초기화한다
        main_frame = tk.Frame(self.root, padx=12, pady=12)
        main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame = main_frame

        # 보드 텍스트 위젯 - 스크롤바 추가
        board_container = tk.Frame(main_frame)
        board_container.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 12))
        
        board_scroll_y = tk.Scrollbar(board_container, orient=tk.VERTICAL)
        board_scroll_x = tk.Scrollbar(board_container, orient=tk.HORIZONTAL)
        
        self.board_text = tk.Text(
            board_container,
            width=20,
            height=12,
            font=BOARD_FONT,
            bg="#111",
            fg="#eee",
            state=tk.DISABLED,
            bd=0,
            highlightthickness=0,
            wrap=tk.NONE,
            yscrollcommand=board_scroll_y.set,
            xscrollcommand=board_scroll_x.set,
        )
        board_scroll_y.config(command=self.board_text.yview)
        board_scroll_x.config(command=self.board_text.xview)
        
        self.board_text.grid(row=0, column=0, sticky="nsew")
        board_scroll_y.grid(row=0, column=1, sticky="ns")
        board_scroll_x.grid(row=1, column=0, sticky="ew")
        
        board_container.rowconfigure(0, weight=1)
        board_container.columnconfigure(0, weight=1)

        moves_frame = tk.Frame(main_frame)
        moves_frame.grid(row=0, column=1, sticky="nsew")
        self.moves_frame = moves_frame

        moves_label = tk.Label(moves_frame, text="Moves", font=STATUS_FONT)
        moves_label.pack(anchor="w")

        moves_scroll = tk.Scrollbar(moves_frame, orient=tk.VERTICAL)
        self.moves_text = tk.Text(
            moves_frame,
            width=18,
            height=18,
            font=MOVE_FONT,
            state=tk.DISABLED,
            wrap=tk.NONE,
            yscrollcommand=moves_scroll.set,
        )
        moves_scroll.config(command=self.moves_text.yview)
        self.moves_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        moves_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        input_frame = tk.Frame(main_frame)
        input_frame.grid(row=1, column=1, sticky="sew", pady=(12, 0))

        self.status_label = tk.Label(input_frame, text="Welcome, Player!", font=STATUS_FONT)
        self.status_label.pack(anchor="w")

        self.enemy_label = tk.Label(input_frame, text="Enemy: Ready", font=STATUS_FONT, fg=ENEMY_BASE_COLOR)
        self.enemy_label.pack(anchor="w", pady=(4, 8))
        self.input_frame = input_frame

        entry_row = tk.Frame(input_frame)
        entry_row.pack(fill=tk.X)

        self.move_entry = tk.Entry(entry_row, font=PROMPT_FONT)
        self.move_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.move_entry.bind("<Return>", self._on_submit)

        self.submit_button = tk.Button(entry_row, text="Submit", command=self._on_submit)
        self.submit_button.pack(side=tk.LEFT, padx=(6, 0))

        # UNDO/REDO 버튼 추가
        button_row = tk.Frame(input_frame)
        button_row.pack(fill=tk.X, pady=(8, 0))
        
        self.undo_button = tk.Button(button_row, text="Undo (Ctrl+Z)", command=self._on_undo)
        self.undo_button.pack(side=tk.LEFT, padx=(0, 6))
        
        self.redo_button = tk.Button(button_row, text="Redo (Ctrl+Y)", command=self._on_redo)
        self.redo_button.pack(side=tk.LEFT, padx=(0, 6))
        
        self.hint_button = tk.Button(button_row, text="💡 Hint", command=self._on_hint)
        self.hint_button.pack(side=tk.LEFT)

        help_label = tk.Label(
            input_frame,
            text="Commands: ff, help, quit, undo, redo, hint",
            font=STATUS_FONT,
            fg="#777",
        )
        help_label.pack(anchor="w", pady=(8, 0))

        # Grid 가중치 설정 - 창 크기 변경 시 자동 확장
        main_frame.columnconfigure(0, weight=1)  # 보드 영역 확장
        main_frame.columnconfigure(1, weight=1)  # 기보/입력 영역 확장
        main_frame.rowconfigure(0, weight=1)     # 상단 영역 확장
        main_frame.rowconfigure(1, weight=0)     # 입력 영역은 고정

    def _show_intro_screen(self) -> None:
        # 인트로 화면을 표시하고 엔터 입력을 기다린다
        self.main_frame.pack_forget()

        self.intro_frame = tk.Frame(self.root, bg="#111", padx=40, pady=40)
        self.intro_frame.pack(fill=tk.BOTH, expand=True)

        pawn_art = (
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
        )

        art_label = tk.Label(
            self.intro_frame,
            text=pawn_art,
            font=("Courier", 18),
            bg="#111",
            fg="#eee",
            justify=tk.CENTER,
        )
        art_label.pack(pady=(0, 16))

        title_label = tk.Label(
            self.intro_frame,
            text="< ASCII Chess >",
            font=("Menlo", 26, "bold"),
            bg="#111",
            fg="#eee",
        )
        title_label.pack(pady=(0, 12))

        self.blink_label = tk.Label(
            self.intro_frame,
            text="< Press Enter to start >",
            font=("Menlo", 16),
            bg="#111",
            fg="#eee",
        )
        self.blink_label.pack(pady=(0, 8))
        self._blink_state = True
        self._blink()

        self.root.bind("<Return>", self._start_game_from_intro)
    
    def _setup_keybindings(self) -> None:
        # UNDO/REDO 단축키 설정
        self.root.bind("<Control-z>", lambda e: self._on_undo())
        self.root.bind("<Control-y>", lambda e: self._on_redo())

    def _blink(self) -> None:
        if not hasattr(self, "blink_label"):
            return
        self._blink_state = not self._blink_state
        color = "#eee" if self._blink_state else "#555"
        self.blink_label.config(fg=color)
        self.root.after(500, self._blink)

    def _start_game_from_intro(self, event: tk.Event | None = None) -> None:
        # 인트로 종료 후 기본 판과 입력 상태를 세팅한다
        if not hasattr(self, "intro_frame"):
            return
        self.root.unbind("<Return>")
        self.intro_frame.destroy()
        del self.intro_frame
        del self.blink_label
        self._stop_enemy_blink()
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.status_label.config(text="Enter Enemy Elo (1350-2850, default 1500):")
        self.move_entry.delete(0, tk.END)
        self.move_entry.insert(0, "1500")
        self.move_entry.selection_range(0, tk.END)
        self.move_entry.focus_set()
        self.move_entry.bind("<Return>", self._on_submit_with_rating)
        self.submit_button.configure(command=self._on_submit_with_rating)
        board_text = self._board_to_text(self.board)
        self.board_text.config(state=tk.NORMAL)
        self.board_text.delete("1.0", tk.END)
        self.board_text.insert(tk.END, board_text)
        self.board_text.config(state=tk.DISABLED)

    def _on_submit_with_rating(self, event: tk.Event | None = None) -> None:
        text = self.move_entry.get().strip()
        if not text:
            self.status_label.config(text="Please enter a rating between 1350 and 2850.")
            return
        try:
            rating = int(text)
        except ValueError:
            self.status_label.config(text="Rating must be a number (1350-2850).")
            self.move_entry.selection_range(0, tk.END)
            return
        rating = max(self.engine_config.min_rating, min(rating, self.engine_config.max_rating))
        self.move_entry.delete(0, tk.END)
        self.ai.set_rating(rating)
        self.status_label.config(text=f"Enemy rating: {rating} Elo. Player to move.")
        self._stop_enemy_blink()
        self.enemy_label.config(text="Enemy: Ready", fg=ENEMY_BASE_COLOR)
        self._resigned = False
        self._forfeited = False
        self._awaiting_ai = False
        self.move_entry.bind("<Return>", self._on_submit)
        self.submit_button.configure(command=self._on_submit)
        self._render()

    def _on_submit(self, event: Optional[tk.Event] = None) -> None:
        # 현재 입력 값에 따라 명령 또는 수를 처리한다
        text = self.move_entry.get().strip()
        if not text:
            return
        lowered = text.lower()
        if self._awaiting_ai and lowered not in {"quit", "ff", "/win", "/lose", "/draw", "help"}:
            self.status_label.config(text="Enemy is thinking... please wait.")
            return
        self.move_entry.delete(0, tk.END)
        self._handle_player_input(text)

    def _handle_player_input(self, user_input: str) -> None:
        # 특수 명령과 SAN 입력을 판별하여 처리한다
        lowered = user_input.lower()
        if lowered in {"/win", "/lose", "/draw"}:
            outcome = lowered[1:]
            self._handle_forced_outcome(outcome)
            return
        if lowered == "help":
            messagebox.showinfo(
                "Help",
                "Enter chess moves in SAN (e.g. Nf3, O-O, cxd4).\n"
                "Commands:\n  ff     - forfeit the game\n  quit   - exit the application\n"
                "  undo   - undo last move (Ctrl+Z)\n  redo   - redo move (Ctrl+Y)",
                parent=self.root,
            )
            return
        if lowered == "undo":
            self._on_undo()
            return
        if lowered == "redo":
            self._on_redo()
            return
        if lowered == "quit":
            self._stop_enemy_blink()
            if self._ai_job is not None:
                try:
                    self.root.after_cancel(self._ai_job)
                except tk.TclError:
                    pass
                self._ai_job = None
            self._awaiting_ai = False
            self._exit_game()
            return
        if lowered == "ff":
            self._stop_enemy_blink()
            self._resigned = True
            self._forfeited = True
            self._awaiting_ai = False
            self.status_label.config(text="Player forfeited. Enemy wins.")
            self.enemy_label.config(text="Enemy: Victory", fg=ENEMY_BASE_COLOR)
            messagebox.showinfo("Game over", "Player forfeited. Enemy wins.", parent=self.root)
            self._ask_play_again()
            return

        try:
            move = self.board.parse_san(user_input)
            san = self.board.san(move)
        except ValueError:
            self.status_label.config(text=f"Illegal move: {user_input}")
            return

        # 플레이어 수를 두기 전 상태 저장
        self.undo_stack.append(self.board.fen())
        self.redo_stack.clear()  # 새 수를 두면 REDO 스택 초기화
        
        self.board.push(move)
        self.move_history.append(san)
        self.status_label.config(text="Enemy is thinking...")
        self.enemy_label.config(text="Enemy: Calculating...", fg=ENEMY_BASE_COLOR)
        self._render()

        if self.board.is_game_over(claim_draw=True):
            self._announce_result()
            return

        self._awaiting_ai = True
        self._ai_job = self.root.after(100, self._play_ai_move)

    def _play_ai_move(self) -> None:
        # Enemy가 수를 계산해 둔 뒤 화면과 상태를 갱신한다
        try:
            ai_move = self.ai.choose_move(self.board)
        except Exception as exc:  # pragma: no cover - engine errors are unexpected
            messagebox.showerror("Engine error", str(exc), parent=self.root)
            self._awaiting_ai = False
            self._ai_job = None
            return

        self._ai_job = None
        
        # AI 수를 두기 전 상태 저장
        self.undo_stack.append(self.board.fen())
        
        san = self.board.san(ai_move)
        self.board.push(ai_move)
        self.move_history.append(san)
        self.enemy_label.config(text=f"Enemy: {san}", fg=ENEMY_BASE_COLOR)
        self.status_label.config(text="Player to move.")
        self._awaiting_ai = False
        self._start_enemy_blink(ai_move.to_square)

        if self.board.is_game_over(claim_draw=True):
            self._announce_result()

    def _handle_forced_outcome(self, outcome: str) -> None:
        # 개발자 테스트 명령으로 강제 종료 시 메시지를 출력한다
        self._stop_enemy_blink()
        mapping = {
            "win": ("Player wins!", "Enemy: Defeated"),
            "lose": ("Enemy wins!", "Enemy: Victory"),
            "draw": ("Draw.", "Enemy: Draw"),
        }
        message, enemy_text = mapping.get(outcome, ("Draw.", "Enemy: Draw"))
        self._awaiting_ai = False
        self._resigned = False
        self._forfeited = False
        self.status_label.config(text=message)
        self.enemy_label.config(text=enemy_text, fg=ENEMY_BASE_COLOR)
        messagebox.showinfo("Game over", message, parent=self.root)
        self._ask_play_again()

    def _announce_result(self) -> None:
        # 실제 대국 결과를 팝업으로 알리고 재도전을 묻는다
        outcome = self.board.outcome(claim_draw=True)
        if outcome is None:
            result_text = "Game ended prematurely."
        elif outcome.winner is None:
            result_text = "Draw!"
        elif outcome.winner == chess.WHITE:
            result_text = "Player wins!"
        else:
            result_text = "Enemy wins!"

        messagebox.showinfo("Game over", result_text, parent=self.root)
        if outcome and outcome.winner is not None:
            if outcome.winner == chess.WHITE:
                self.enemy_label.config(text="Enemy: Defeated")
            else:
                self.enemy_label.config(text="Enemy: Victory")
        elif outcome and outcome.winner is None:
            self.enemy_label.config(text="Enemy: Draw")
        else:
            self.enemy_label.config(text="Enemy: Idle")
        self._ask_play_again()

    def _ask_play_again(self) -> None:
        again = messagebox.askyesno("Play again?", "Would you like to start a new game?", parent=self.root)
        if again:
            self._reset_game()
        else:
            self._exit_game()

    def _reset_game(self) -> None:
        # 새 대국을 시작하기 위한 상태 초기화
        self.board = chess.Board()
        self.move_history.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.undo_stack.append(self.board.fen())  # 초기 상태 저장
        self._stop_enemy_blink()
        self.enemy_label.config(text="Enemy: Ready", fg=ENEMY_BASE_COLOR)
        self.status_label.config(text="New game! Player to move.")
        self._resigned = False
        self._forfeited = False
        self._awaiting_ai = False
        self._closing = False
        if self._ai_job is not None:
            try:
                self.root.after_cancel(self._ai_job)
            except tk.TclError:
                pass
            self._ai_job = None
        self._render()

    def _render(self) -> None:
        # 보드와 기보 텍스트를 최신 상태로 갱신한다
        if self._is_rendering:
            return
        self._is_rendering = True
        try:
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
        finally:
            self._is_rendering = False

    def _board_to_text(self, board: "chess.Board") -> str:
        # 보드 상태를 텍스트 행렬로 변환한다 (고정폭 폰트에 맞춘 간격)
        # 파일 레이블: 각 문자 사이에 2칸 공백으로 체스판 칸과 정렬
        files = "   a  b  c  d  e  f  g  h"
        lines = [files]
        for rank in range(7, -1, -1):
            row_parts = [str(rank + 1) + " "]
            for file in range(8):
                square = chess.square(file, rank)
                piece = board.piece_at(square)
                bg_char = LIGHT_SQUARE if (rank + file) % 2 else DARK_SQUARE
                
                if piece is None:
                    # 빈 칸: 배경 문자를 중앙에 배치 (양쪽 공백)
                    cell = " " + bg_char + " "
                else:
                    symbol = self._piece_symbol(piece.symbol())
                    if self._enemy_highlight_square == square and not self._enemy_blink_visible:
                        cell = " " + bg_char + " "
                    else:
                        # 기물: 중앙에 배치 (양쪽 공백)
                        cell = " " + symbol + " "
                
                row_parts.append(cell)
            
            row_parts.append(str(rank + 1))
            line = "".join(row_parts)
            lines.append(line)
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

    def _on_close(self) -> None:
        self._stop_enemy_blink()
        self.ai.close()
        self.root.destroy()

    def _start_enemy_blink(self, square: int) -> None:
        self._stop_enemy_blink()
        self._enemy_highlight_square = square
        self._enemy_blink_visible = False
        self._enemy_blink_remaining = ENEMY_BLINK_TOGGLES
        self.enemy_label.config(fg=ENEMY_HIGHLIGHT_COLOR)
        self._render()
        if self._enemy_blink_remaining > 0:
            self._enemy_blink_job = self.root.after(ENEMY_BLINK_INTERVAL_MS, self._enemy_blink_step)

    def _enemy_blink_step(self) -> None:
        if self._enemy_blink_remaining <= 0:
            self._stop_enemy_blink()
            return
        self._enemy_blink_visible = not self._enemy_blink_visible
        self._enemy_blink_remaining -= 1
        self.enemy_label.config(
            fg=ENEMY_HIGHLIGHT_COLOR if self._enemy_blink_visible else ENEMY_BASE_COLOR
        )
        self._render()
        if self._enemy_blink_remaining > 0:
            self._enemy_blink_job = self.root.after(
                ENEMY_BLINK_INTERVAL_MS, self._enemy_blink_step
            )
        else:
            self._enemy_blink_job = self.root.after(
                ENEMY_BLINK_INTERVAL_MS, self._stop_enemy_blink
            )

    def _stop_enemy_blink(self) -> None:
        if self._enemy_blink_job is not None:
            try:
                self.root.after_cancel(self._enemy_blink_job)
            except tk.TclError:
                pass
            self._enemy_blink_job = None
        highlight_was_set = self._enemy_highlight_square is not None
        self._enemy_highlight_square = None
        self._enemy_blink_visible = True
        self._enemy_blink_remaining = 0
        if self.enemy_label.cget("fg") != ENEMY_BASE_COLOR:
            self.enemy_label.config(fg=ENEMY_BASE_COLOR)
        if highlight_was_set and not self._is_rendering:
            self._render()

    def _exit_game(self) -> None:
        # 창을 안전하게 종료하며 모든 예약 작업을 정리한다
        if self._closing:
            return
        self._closing = True
        self._stop_enemy_blink()
        if self._ai_job is not None:
            try:
                self.root.after_cancel(self._ai_job)
            except tk.TclError:
                pass
            self._ai_job = None
        self._awaiting_ai = False
        try:
            self.ai.close()
        except Exception:
            pass
        try:
            self.root.quit()
        except tk.TclError:
            pass
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def _configure_geometry(self) -> None:
        # 유동적인 창 크기 설정 - 사용자가 조절 가능
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        board_width = 32 * 18
        board_height = 12 * 36
        moves_width = 150
        padding = 24
        default_w = board_width + moves_width + padding
        default_h = board_height + padding
        
        # 화면 크기의 80%를 최대로 설정
        max_w = int(screen_width * 0.8)
        max_h = int(screen_height * 0.8)
        
        # 화면에 맞춰 크기 조정
        window_w = min(default_w, max_w)
        window_h = min(default_h, max_h)
        
        # 최소 크기 설정 (UI가 깨지지 않도록)
        min_w = 700
        min_h = 500
        
        # 창을 화면 중앙에 배치
        x = (screen_width - window_w) // 2
        y = (screen_height - window_h) // 2
        
        self.root.geometry(f"{window_w}x{window_h}+{x}+{y}")
        self.root.minsize(min_w, min_h)
        self.root.resizable(True, True)  # 크기 조절 가능하게 변경

    def _bring_to_front(self) -> None:
        try:
            self.root.lift()
            self.root.attributes("-topmost", True)
            self._focus_binding = self.root.bind("<FocusIn>", self._release_topmost, add="+")
        except tk.TclError:
            self._focus_binding = None

    def _release_topmost(self, _event: tk.Event | None = None) -> None:
        try:
            self.root.attributes("-topmost", False)
        except tk.TclError:
            pass
        finally:
            if getattr(self, "_focus_binding", None) is not None:
                try:
                    self.root.unbind("<FocusIn>", self._focus_binding)
                except tk.TclError:
                    pass
                self._focus_binding = None
    
    def _on_undo(self) -> None:
        # 마지막 플레이어 수와 AI 수를 되돌린다 (2수)
        if self._awaiting_ai:
            self.status_label.config(text="Cannot undo while Enemy is thinking.")
            return
        
        if len(self.undo_stack) < 3:  # 초기 상태 + 플레이어 수 + AI 수
            self.status_label.config(text="Nothing to undo.")
            return
        
        # 현재 상태를 REDO 스택에 저장 (AI 수)
        if self.move_history:
            self.redo_stack.append(self.move_history[-1])
        
        # AI 수 되돌리기
        self.board.pop()
        self.undo_stack.pop()
        if self.move_history:
            self.move_history.pop()
        
        # 플레이어 수도 REDO 스택에 저장
        if self.move_history:
            self.redo_stack.append(self.move_history[-1])
        
        # 플레이어 수 되돌리기
        self.board.pop()
        self.undo_stack.pop()
        if self.move_history:
            self.move_history.pop()
        
        self._stop_enemy_blink()
        self.status_label.config(text="Undone. Player to move.")
        self.enemy_label.config(text="Enemy: Ready", fg=ENEMY_BASE_COLOR)
        self._render()
    
    def _on_redo(self) -> None:
        # REDO 스택에서 상태를 복원한다 (2수)
        if self._awaiting_ai:
            self.status_label.config(text="Cannot redo while Enemy is thinking.")
            return
        
        if len(self.redo_stack) < 2:  # 플레이어 수 + AI 수
            self.status_label.config(text="Nothing to redo.")
            return
        
        # 플레이어 수 REDO
        player_move_san = self.redo_stack.pop()
        try:
            player_move = self.board.parse_san(player_move_san)
            self.undo_stack.append(self.board.fen())
            self.board.push(player_move)
            self.move_history.append(player_move_san)
        except ValueError:
            self.redo_stack.append(player_move_san)
            self.status_label.config(text="Redo failed.")
            return
        
        # AI 수 REDO
        ai_move_san = self.redo_stack.pop()
        try:
            ai_move = self.board.parse_san(ai_move_san)
            self.undo_stack.append(self.board.fen())
            self.board.push(ai_move)
            self.move_history.append(ai_move_san)
        except ValueError:
            # AI 수 복원 실패시 플레이어 수도 되돌림
            self.board.pop()
            self.undo_stack.pop()
            self.move_history.pop()
            self.redo_stack.append(player_move_san)
            self.redo_stack.append(ai_move_san)
            self.status_label.config(text="Redo failed.")
            return
        
        self._stop_enemy_blink()
        self.status_label.config(text="Redone. Player to move.")
        self.enemy_label.config(text="Enemy: Ready", fg=ENEMY_BASE_COLOR)
        self._render()
    
    def _on_hint(self) -> None:
        # Stockfish 최고 수준으로 최선의 수를 추천한다
        if self._awaiting_ai:
            self.status_label.config(text="Cannot get hint while Enemy is thinking.")
            return
        
        if self.board.is_game_over(claim_draw=True):
            self.status_label.config(text="Game is over. No hints available.")
            return
        
        # 플레이어 차례가 아니면 힌트 불가
        if self.board.turn != chess.WHITE:
            self.status_label.config(text="Hint only available on player's turn.")
            return
        
        try:
            self.status_label.config(text="Analyzing best move...")
            self.hint_button.config(state=tk.DISABLED)
            self.root.update_idletasks()
            
            hint_move, hint_san = self.ai.get_hint(self.board)
            from_square = chess.square_name(hint_move.from_square)
            to_square = chess.square_name(hint_move.to_square)
            
            hint_message = f"💡 Hint: {hint_san} (from {from_square} to {to_square})"
            self.status_label.config(text=hint_message)
            messagebox.showinfo("Hint", hint_message, parent=self.root)
        except Exception as exc:
            error_msg = f"Failed to get hint: {exc}"
            self.status_label.config(text=error_msg)
            messagebox.showerror("Hint Error", error_msg, parent=self.root)
        finally:
            self.hint_button.config(state=tk.NORMAL)
