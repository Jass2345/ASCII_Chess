from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox
from typing import List, Optional

try:
    import chess
except ImportError:  # pragma: no cover - handled by dependency check in main
    chess = None  # type: ignore

from .ai import EngineConfig, StockfishAI
from .renderer import ASCII_PIECES, LIGHT_SQUARE, DARK_SQUARE, UNICODE_PIECES


BOARD_FONT = ("Menlo", 32)
MOVE_FONT = ("Menlo", 14)
STATUS_FONT = ("Menlo", 12)
PROMPT_FONT = ("Menlo", 12)

ENEMY_BASE_COLOR = "#888"
ENEMY_HIGHLIGHT_COLOR = "#ffcc33"
ENEMY_BLINK_INTERVAL_MS = 350
ENEMY_BLINK_TOGGLES = 6  # 점멸 횟수 (약 세 번)

CELL_WIDTH = 3
EDGE_LABEL_WIDTH = 2


@dataclass(frozen=True)
class BoardTheme:
    name: str
    light_color: str
    dark_color: str


@dataclass(frozen=True)
class PieceColorTheme:
    name: str
    black_color: str
    white_color: str


DEFAULT_BOARD_THEMES: List[BoardTheme] = [
    BoardTheme("default", "#1e1e1e", "#111111"),
    BoardTheme("classic", "#f0d9b5", "#b58863"),
    BoardTheme("ocean", "#4f6d7a", "#1f3b4d"),
]

DEFAULT_PIECE_COLORS: List[PieceColorTheme] = [
    PieceColorTheme("default", "#eeeeee", "#eeeeee"),
    PieceColorTheme("contrast", "#333333", "#fafafa"),
    PieceColorTheme("emerald", "#0f5132", "#fef7e2"),
]

FALLBACK_BOARD_THEME = DEFAULT_BOARD_THEMES[0]
FALLBACK_PIECE_COLOR = DEFAULT_PIECE_COLORS[0]

class ChessGUI:
    def __init__(self, root: tk.Tk, engine_config: EngineConfig, use_unicode: bool = True) -> None:
        if chess is None:
            raise RuntimeError("python-chess is required to run the GUI.")

        self.root = root
        self.root.title("ASCII Chess")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.mode = "intro"
        self.engine_config = engine_config
        self.ai = StockfishAI(config=self.engine_config)
        self.use_unicode = use_unicode
        self.board = chess.Board()
        self.move_history: List[str] = []
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
        self.board_font = tkfont.Font(family=BOARD_FONT[0], size=BOARD_FONT[1])

        self.board_themes: List[BoardTheme] = list(DEFAULT_BOARD_THEMES)
        self.piece_color_themes: List[PieceColorTheme] = list(DEFAULT_PIECE_COLORS)
        self.selected_board_theme_index = 0
        self.selected_piece_color_theme_index = 0
        self.preview_board_theme: Optional[BoardTheme] = None
        self.preview_piece_color_theme: Optional[PieceColorTheme] = None
        self.theme_listbox: Optional[tk.Listbox] = None
        self.theme_info_label: Optional[tk.Label] = None
        self.theme_mode = "menu"
        self.theme_detail_category: Optional[str] = None
        self.theme_menu_index = 0
        self.theme_categories = [
            ("board", "Board Color"),
            ("piece_color", "Piece Color"),
        ]

        self._build_widgets()
        self._configure_geometry()
        self._bring_to_front()
        self._show_intro_screen()

    def _build_widgets(self) -> None:
        # 보드 영역과 기보·입력 영역을 초기화한다
        main_frame = tk.Frame(self.root, padx=12, pady=12)
        main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame = main_frame

        self.board_text = tk.Text(
            main_frame,
            width=2,
            height=2,
            font=self.board_font,
            bg="#111",
            fg="#eee",
            state=tk.DISABLED,
            bd=0,
            highlightthickness=0,
        )
        self.board_text.grid(row=0, column=0, rowspan=2, sticky="nw")

        moves_frame = tk.Frame(main_frame)
        moves_frame.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        self.moves_frame = moves_frame

        moves_label = tk.Label(moves_frame, text="Moves", font=STATUS_FONT)
        moves_label.pack(anchor="w")
        self.moves_label = moves_label

        self.moves_text = tk.Text(
            moves_frame,
            width=18,
            height=18,
            font=MOVE_FONT,
            state=tk.DISABLED,
        )
        self.moves_text.pack(fill=tk.BOTH, expand=True)

        self.theme_listbox = tk.Listbox(
            moves_frame,
            width=18,
            height=18,
            font=MOVE_FONT,
            activestyle="dotbox",
            exportselection=False,
        )
        self.theme_listbox.bind("<Return>", self._on_theme_activate)
        self.theme_listbox.bind("<Double-Button-1>", self._on_theme_activate)
        self.theme_listbox.bind("<<ListboxSelect>>", self._on_theme_selection_changed)
        self.theme_listbox.pack_forget()

        self.theme_info_label = tk.Label(
            moves_frame,
            text="",
            font=STATUS_FONT,
            fg="#999",
            justify=tk.LEFT,
            wraplength=240,
        )
        self.theme_info_label.pack_forget()

        input_frame = tk.Frame(main_frame)
        input_frame.grid(row=1, column=1, sticky="nsew", padx=(12, 0), pady=(12, 0))

        self.status_label = tk.Label(input_frame, text="Welcome, Player!", font=STATUS_FONT)
        self.status_label.pack(anchor="w")

        self.enemy_label = tk.Label(input_frame, text="Enemy: Ready", font=STATUS_FONT, fg=ENEMY_BASE_COLOR)
        self.enemy_label.pack(anchor="w", pady=(4, 8))
        self.input_frame = input_frame

        entry_row = tk.Frame(input_frame)
        entry_row.pack(fill=tk.X)
        self.entry_row = entry_row

        self.move_entry = tk.Entry(entry_row, font=PROMPT_FONT)
        self.move_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.move_entry.bind("<Return>", self._on_submit)

        self.submit_button = tk.Button(entry_row, text="Submit", command=self._on_submit)
        self.submit_button.pack(side=tk.LEFT, padx=(6, 0))

        help_label = tk.Label(
            input_frame,
            text="Commands: ff, help, quit",
            font=STATUS_FONT,
            fg="#777",
        )
        help_label.pack(anchor="w", pady=(8, 0))
        self.help_label = help_label

        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=0)
        main_frame.rowconfigure(1, weight=1)

    def _show_intro_screen(self) -> None:
        # 인트로 화면을 표시하고 엔터 입력을 기다린다
        self.mode = "intro"
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

        self.esc_hint_label = tk.Label(
            self.intro_frame,
            text="< Press Esc for theme settings >",
            font=("Menlo", 14),
            bg="#111",
            fg="#bbb",
        )
        self.esc_hint_label.pack(pady=(0, 16))

        self.root.bind("<Return>", self._start_game_from_intro)
        self.root.bind("<Escape>", self._handle_escape)

    def _blink(self) -> None:
        if not hasattr(self, "blink_label"):
            return
        self._blink_state = not self._blink_state
        color = "#eee" if self._blink_state else "#555"
        self.blink_label.config(fg=color)
        self.root.after(500, self._blink)

    def _handle_escape(self, event: tk.Event | None = None):
        if self.mode == "intro":
            self._enter_theme_settings()
            return "break"
        if self.mode == "theme_detail":
            self._exit_theme_detail()
            return "break"
        if self.mode == "theme_menu":
            self._leave_theme_settings()
            return "break"
        return None

    def _enter_theme_settings(self) -> None:
        if self.mode in {"theme_menu", "theme_detail"}:
            return
        if hasattr(self, "intro_frame"):
            self.root.unbind("<Return>")
            try:
                self.intro_frame.destroy()
            except tk.TclError:
                pass
            for attr in ("intro_frame", "blink_label", "esc_hint_label"):
                if hasattr(self, attr):
                    delattr(self, attr)
        self._stop_enemy_blink()
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.mode = "theme_menu"
        self.moves_label.config(text="Theme Settings")
        self.status_label.config(text="테마 옵션을 선택하세요.")
        self.enemy_label.config(text="Enter: 옵션 열기 / Esc: 첫 화면", fg=ENEMY_BASE_COLOR)
        self.move_entry.delete(0, tk.END)
        self.move_entry.configure(state=tk.DISABLED)
        self.submit_button.configure(state=tk.DISABLED)
        self.entry_row.pack_forget()
        self.help_label.pack_forget()
        self._show_theme_sidebar()
        self.board = chess.Board()
        self.move_history.clear()
        self.preview_board_theme = None
        self.preview_piece_color_theme = None
        self._show_theme_menu()

    def _leave_theme_settings(self) -> None:
        if self.mode not in {"theme_menu", "theme_detail"}:
            return
        self._show_moves_sidebar()
        self.entry_row.pack(fill=tk.X)
        self.help_label.pack(anchor="w", pady=(8, 0))
        self.move_entry.configure(state=tk.NORMAL)
        self.submit_button.configure(state=tk.NORMAL)
        self.moves_label.config(text="Moves")
        self.status_label.config(text="Welcome, Player!")
        self.enemy_label.config(text="Enemy: Ready", fg=ENEMY_BASE_COLOR)
        self.preview_board_theme = None
        self.preview_piece_color_theme = None
        self.mode = "intro"
        self.main_frame.pack_forget()
        self._show_intro_screen()

    def _show_theme_sidebar(self) -> None:
        if self.theme_listbox is None or self.theme_info_label is None:
            return
        self.moves_text.pack_forget()
        if not self.theme_listbox.winfo_manager():
            self.theme_listbox.pack(fill=tk.BOTH, expand=True)
        if not self.theme_info_label.winfo_manager():
            self.theme_info_label.pack(anchor="w", pady=(8, 0))

    def _show_moves_sidebar(self) -> None:
        if self.theme_listbox is None or self.theme_info_label is None:
            return
        if self.theme_listbox.winfo_manager():
            self.theme_listbox.pack_forget()
        if self.theme_info_label.winfo_manager():
            self.theme_info_label.pack_forget()
        if not self.moves_text.winfo_manager():
            self.moves_text.pack(fill=tk.BOTH, expand=True)

    def _show_theme_menu(self) -> None:
        if self.theme_listbox is None:
            return
        self._show_theme_sidebar()
        self.mode = "theme_menu"
        self.theme_mode = "menu"
        self.theme_detail_category = None
        self.preview_board_theme = None
        self.preview_piece_color_theme = None

        self.theme_listbox.delete(0, tk.END)
        for _, label in self.theme_categories:
            self.theme_listbox.insert(tk.END, label)

        if not self.theme_categories:
            return

        self.theme_menu_index = max(0, min(self.theme_menu_index, len(self.theme_categories) - 1))
        self.theme_listbox.selection_clear(0, tk.END)
        self.theme_listbox.selection_set(self.theme_menu_index)
        self.theme_listbox.activate(self.theme_menu_index)
        self.theme_listbox.focus_set()

        self.moves_label.config(text="Theme Settings")
        self.status_label.config(text="커스터마이즈할 항목을 선택하세요.")
        self.enemy_label.config(text="Enter: 옵션 열기 / Esc: 첫 화면", fg=ENEMY_BASE_COLOR)
        self.theme_info_label.config(
            text="위/아래 방향키로 이동하고 Enter로 해당 옵션을 엽니다.\n"
            "Board Color: 보드 배경 색상 조합\n"
            "Piece Color: 흑/백 기물 색상 지정"
        )
        self._render()

    def _enter_theme_detail(self, category: str) -> None:
        if self.theme_listbox is None:
            return
        self._show_theme_sidebar()
        self.mode = "theme_detail"
        self.theme_mode = "detail"
        self.theme_detail_category = category
        self.theme_listbox.delete(0, tk.END)

        category_label = next((label for key, label in self.theme_categories if key == category), "")
        if category_label:
            self.moves_label.config(text=f"Theme Settings · {category_label}")

        if category == "board":
            themes = self.board_themes
            selected_index = self.selected_board_theme_index
            for theme in themes:
                self.theme_listbox.insert(
                    tk.END, f"{theme.name} ({theme.light_color}, {theme.dark_color})"
                )
            if themes:
                self.preview_board_theme = themes[selected_index]
            self.status_label.config(text="Board Color - 적용할 색상 세트를 선택하세요.")
            self.theme_info_label.config(
                text="선택한 색상 조합이 좌측 보드에 즉시 반영됩니다.\nEnter로 적용하고 Esc로 메뉴로 돌아갑니다."
            )
        elif category == "piece_color":
            themes = self.piece_color_themes
            selected_index = self.selected_piece_color_theme_index
            for theme in themes:
                self.theme_listbox.insert(
                    tk.END, f"{theme.name} ({theme.black_color}, {theme.white_color})"
                )
            if themes:
                self.preview_piece_color_theme = themes[selected_index]
            self.status_label.config(text="Piece Color - 흑/백 기물 색상을 선택하세요.")
            self.theme_info_label.config(
                text="기물 전용 색상을 설정합니다. 좌측 보드에서 즉시 확인할 수 있습니다.\nEnter로 적용, Esc로 메뉴 복귀."
            )
        else:
            return

        total = self.theme_listbox.size()
        if total == 0:
            return
        selected_index = max(0, min(selected_index, total - 1))
        self.theme_listbox.selection_clear(0, tk.END)
        self.theme_listbox.selection_set(selected_index)
        self.theme_listbox.activate(selected_index)
        self.theme_listbox.focus_set()
        self._render()

    def _exit_theme_detail(self) -> None:
        if self.mode != "theme_detail":
            return
        if self.theme_detail_category == "board":
            self.preview_board_theme = None
        elif self.theme_detail_category == "piece_color":
            self.preview_piece_color_theme = None
        self.theme_detail_category = None
        self._show_theme_menu()

    def _on_theme_selection_changed(self, _event: tk.Event | None = None) -> None:
        if self.mode != "theme_detail" or self.theme_listbox is None:
            return
        selection = self.theme_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if self.theme_detail_category == "board":
            if 0 <= index < len(self.board_themes):
                self.preview_board_theme = self.board_themes[index]
        elif self.theme_detail_category == "piece_color":
            if 0 <= index < len(self.piece_color_themes):
                self.preview_piece_color_theme = self.piece_color_themes[index]
        self._render()

    def _on_theme_activate(self, _event: tk.Event | None = None):
        if self.theme_listbox is None:
            return "break"
        selection = self.theme_listbox.curselection()
        if not selection:
            return "break"
        index = selection[0]
        if self.mode == "theme_menu":
            self.theme_menu_index = index
            category = self.theme_categories[index][0]
            self._enter_theme_detail(category)
            return "break"
        if self.mode == "theme_detail":
            message = ""
            if self.theme_detail_category == "board" and 0 <= index < len(self.board_themes):
                self.selected_board_theme_index = index
                self.preview_board_theme = None
                message = f"보드 테마 '{self.board_themes[index].name}'을 적용했습니다."
            elif (
                self.theme_detail_category == "piece_color"
                and 0 <= index < len(self.piece_color_themes)
            ):
                self.selected_piece_color_theme_index = index
                self.preview_piece_color_theme = None
                message = f"기물 색상 '{self.piece_color_themes[index].name}'을 적용했습니다."
            if message:
                self.status_label.config(text=message)
            self._show_theme_menu()
            return "break"
        return "break"

    def _start_game_from_intro(self, event: tk.Event | None = None) -> None:
        # 인트로 종료 후 기본 판과 입력 상태를 세팅한다
        if not hasattr(self, "intro_frame"):
            return
        self.root.unbind("<Return>")
        self.intro_frame.destroy()
        del self.intro_frame
        del self.blink_label
        if hasattr(self, "esc_hint_label"):
            del self.esc_hint_label
        self._stop_enemy_blink()
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.mode = "game_setup"
        self.status_label.config(text="Enter Enemy Elo (1350-2850, default 1500):")
        self.move_entry.delete(0, tk.END)
        self.move_entry.insert(0, "1500")
        self.move_entry.selection_range(0, tk.END)
        self.move_entry.focus_set()
        self.move_entry.bind("<Return>", self._on_submit_with_rating)
        self.submit_button.configure(command=self._on_submit_with_rating)
        board_text = self._board_to_text(self.board)
        lines = board_text.splitlines() or [""]
        max_cols = max(len(line) for line in lines)
        self.board_text.config(state=tk.NORMAL)
        self.board_text.delete("1.0", tk.END)
        self.board_text.insert(tk.END, board_text)
        self.board_text.config(state=tk.DISABLED)
        self.board_text.configure(width=max_cols, height=len(lines))
        self.moves_text.configure(height=max(int(len(lines) * 1.5), 6))

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
        self.mode = "game"
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
                "Commands:\n  ff     - forfeit the game\n  quit   - exit the application",
                parent=self.root,
            )
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
        self._stop_enemy_blink()
        self.enemy_label.config(text="Enemy: Ready", fg=ENEMY_BASE_COLOR)
        self.status_label.config(text="New game! Player to move.")
        self._resigned = False
        self._forfeited = False
        self._awaiting_ai = False
        self._closing = False
        self.mode = "game"
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
            board_lines = board_text.splitlines() or [""]
            moves_text = self._moves_to_text(self.move_history)

            max_cols = max(len(line) for line in board_lines)
            self.board_text.config(state=tk.NORMAL)
            self.board_text.delete("1.0", tk.END)
            self.board_text.insert(tk.END, board_text)
            self._apply_board_theme_tags(board_lines)
            self.board_text.config(state=tk.DISABLED)
            board_line_count = len(board_lines)
            self.board_text.configure(width=max_cols, height=board_line_count)

            if self.mode not in {"theme_menu", "theme_detail"}:
                self.moves_text.config(state=tk.NORMAL)
                self.moves_text.delete("1.0", tk.END)
                self.moves_text.insert(tk.END, moves_text)
                self.moves_text.config(state=tk.DISABLED)
                self.moves_text.configure(height=max(int(board_line_count * 1.5), 6))
        finally:
            self._is_rendering = False

    def _apply_board_theme_tags(self, board_lines: List[str]) -> None:
        if chess is None:
            return
        board_theme = self._effective_board_theme()
        piece_theme = self._effective_piece_color_theme()

        self.board_text.tag_configure("square_light", background=board_theme.light_color)
        self.board_text.tag_configure("square_dark", background=board_theme.dark_color)
        self.board_text.tag_configure("piece_white", foreground=piece_theme.white_color)
        self.board_text.tag_configure("piece_black", foreground=piece_theme.black_color)

        for tag in ("square_light", "square_dark", "piece_white", "piece_black"):
            self.board_text.tag_remove(tag, "1.0", tk.END)

        if len(board_lines) < 10:
            return

        for rank_offset in range(8):
            line_number = rank_offset + 2  # 1-based line index (1=header)
            rank_idx = 7 - rank_offset
            for file_idx in range(8):
                start_col = EDGE_LABEL_WIDTH + file_idx * CELL_WIDTH
                end_col = start_col + CELL_WIDTH
                start_index = f"{line_number}.{start_col}"
                end_index = f"{line_number}.{end_col}"
                square_tag = "square_light" if (file_idx + rank_idx) % 2 else "square_dark"
                self.board_text.tag_add(square_tag, start_index, end_index)
                square = chess.square(file_idx, rank_idx)
                piece = self.board.piece_at(square)
                blink_hidden = (
                    self._enemy_highlight_square == square and not self._enemy_blink_visible
                )
                if piece and not blink_hidden:
                    piece_tag = "piece_white" if piece.color == chess.WHITE else "piece_black"
                    self.board_text.tag_add(piece_tag, start_index, end_index)

    def _effective_board_theme(self) -> BoardTheme:
        if self.preview_board_theme is not None:
            return self.preview_board_theme
        if not self.board_themes:
            return FALLBACK_BOARD_THEME
        index = self.selected_board_theme_index % len(self.board_themes)
        return self.board_themes[index]

    def _effective_piece_color_theme(self) -> PieceColorTheme:
        if self.preview_piece_color_theme is not None:
            return self.preview_piece_color_theme
        if not self.piece_color_themes:
            return FALLBACK_PIECE_COLOR
        index = self.selected_piece_color_theme_index % len(self.piece_color_themes)
        return self.piece_color_themes[index]

    def _board_to_text(self, board: "chess.Board") -> str:
        # 보드 상태를 텍스트 행렬로 변환한다
        header_cells = [chr(ord("a") + file).center(CELL_WIDTH) for file in range(8)]
        header = " " * EDGE_LABEL_WIDTH + "".join(header_cells) + " " * EDGE_LABEL_WIDTH
        lines = [header]
        for rank in range(7, -1, -1):
            square_chunks: List[str] = []
            for file in range(8):
                square = chess.square(file, rank)
                piece = board.piece_at(square)
                blink_hidden = (
                    self._enemy_highlight_square == square and not self._enemy_blink_visible
                )
                if piece is None or blink_hidden:
                    symbol = LIGHT_SQUARE if (rank + file) % 2 else DARK_SQUARE
                else:
                    symbol = self._piece_symbol(piece.symbol())
                square_chunks.append(symbol.center(CELL_WIDTH))
            row_label = str(rank + 1).center(EDGE_LABEL_WIDTH)
            line = f"{row_label}{''.join(square_chunks)}{row_label}"
            lines.append(line)
        lines.append(header)
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
        # 고정 창 크기를 계산하기 위한 기준 값
        board_width = 32 * 18
        board_height = 12 * 36
        moves_width = 150
        padding = 24
        total_w = board_width + moves_width + padding
        total_h = board_height + padding
        self.root.geometry(f"{total_w}x{total_h}")
        self.root.resizable(False, False)

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
