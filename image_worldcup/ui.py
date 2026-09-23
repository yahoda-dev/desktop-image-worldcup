from __future__ import annotations

from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from PIL import Image, ImageTk

from image_worldcup.scanner import (
    ImageEntry,
    ScanResult,
    load_image_for_display,
    scan_images,
)
from image_worldcup.resources import configure_fonts, set_window_icon
from image_worldcup.tournament import Tournament, allowed_round_sizes


class WorldCupApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self._font_family = configure_fonts(root)
        set_window_icon(root)
        self.root.title("로컬 이미지 이상형 월드컵")
        self.root.geometry("1400x800")
        self.root.minsize(1050, 650)

        self._selected_folder: Path | None = None
        self._scan_result: ScanResult | None = None
        self._scan_token = 0
        self._scan_queue: queue.Queue[tuple[int, ScanResult | None, Exception | None]] = (
            queue.Queue()
        )
        self._image_token = 0
        self._image_queue: queue.Queue[
            tuple[int, tuple[Image.Image, ...] | None, Exception | None]
        ] = queue.Queue()
        self._tournament: Tournament | None = None
        self._current_images: tuple[Image.Image, ...] = ()
        self._photo_images: list[ImageTk.PhotoImage | None] = [None, None]
        self._canvases: list[tk.Canvas] = []
        self._resize_job: str | None = None
        self._selection_locked = False
        self._choice_buttons: list[ttk.Button] = []
        self._loading_bar: ttk.Progressbar | None = None

        self._show_start_screen()
        self.root.after(100, self._poll_scan_queue)

    def _clear_root(self) -> None:
        self._image_token += 1
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
            self._resize_job = None
        for child in self.root.winfo_children():
            child.destroy()
        self._canvases = []
        self._current_images = ()
        self._photo_images = [None, None]
        self._choice_buttons = []
        self._loading_bar = None

    def _show_start_screen(self) -> None:
        self._clear_root()
        self._tournament = None
        self._selection_locked = False

        container = ttk.Frame(self.root, padding=32)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="로컬 이미지 이상형 월드컵",
            font=(self._font_family, 24, "bold"),
        ).pack(pady=(30, 12))
        ttk.Label(
            container,
            text="JPG, PNG, WebP 이미지가 있는 폴더를 선택하세요.",
        ).pack(pady=(0, 28))

        folder_row = ttk.Frame(container)
        folder_row.pack(fill="x", pady=8)
        self._folder_var = tk.StringVar(
            value=str(self._selected_folder) if self._selected_folder else ""
        )
        ttk.Entry(folder_row, textvariable=self._folder_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ttk.Button(folder_row, text="폴더 선택", command=self._choose_folder).pack(
            side="right"
        )

        self._status_var = tk.StringVar(value="폴더를 선택해 주세요.")
        ttk.Label(container, textvariable=self._status_var).pack(pady=(16, 20))
        self._scan_progress = ttk.Progressbar(container, mode="indeterminate", length=320)

        round_row = ttk.Frame(container)
        self._round_row = round_row
        round_row.pack(pady=8)
        ttk.Label(round_row, text="시작 라운드").pack(side="left", padx=(0, 10))
        self._round_var = tk.StringVar()
        self._round_combo = ttk.Combobox(
            round_row,
            textvariable=self._round_var,
            state="disabled",
            width=12,
        )
        self._round_combo.pack(side="left")

        self._start_button = ttk.Button(
            container,
            text="월드컵 시작",
            command=self._start_tournament,
            state="disabled",
        )
        self._start_button.pack(pady=28, ipadx=28, ipady=10)

        if self._scan_result is not None:
            self._apply_scan_result(self._scan_result)

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(title="이미지 폴더 선택")
        if not selected:
            return
        self._selected_folder = Path(selected).resolve(strict=False)
        self._folder_var.set(str(self._selected_folder))
        self._begin_scan(self._selected_folder)

    def _begin_scan(self, folder: Path) -> None:
        self._scan_token += 1
        token = self._scan_token
        self._scan_result = None
        self._status_var.set("이미지 파일을 검사하고 있습니다...")
        self._scan_progress.pack(pady=(0, 16), before=self._round_row)
        self._scan_progress.start(12)
        self._round_var.set("")
        self._round_combo.configure(values=(), state="disabled")
        self._start_button.configure(state="disabled")

        def worker() -> None:
            try:
                result = scan_images(folder)
                self._scan_queue.put((token, result, None))
            except Exception as error:
                self._scan_queue.put((token, None, error))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_scan_queue(self) -> None:
        try:
            while True:
                token, result, error = self._scan_queue.get_nowait()
                if token != self._scan_token:
                    continue
                if error is not None:
                    self._stop_scan_progress()
                    self._status_var.set("폴더를 검사하지 못했습니다.")
                    messagebox.showerror("폴더 검사 실패", str(error))
                elif result is not None:
                    self._scan_result = result
                    self._apply_scan_result(result)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_scan_queue)

        try:
            while True:
                token, images, error = self._image_queue.get_nowait()
                if token != self._image_token:
                    continue
                if error is not None:
                    self._abort_for_missing_image(error)
                elif images is not None:
                    self._finish_image_load(images)
        except queue.Empty:
            pass

    def _stop_scan_progress(self) -> None:
        if hasattr(self, "_scan_progress"):
            self._scan_progress.stop()
            self._scan_progress.pack_forget()

    def _apply_scan_result(self, result: ScanResult) -> None:
        self._stop_scan_progress()
        self._status_var.set(
            f"사용 가능한 이미지 {result.valid_count}장 · 제외된 파일 {result.invalid_count}장"
        )
        sizes = allowed_round_sizes(result.valid_count)
        if not sizes:
            self._round_var.set("")
            self._round_combo.configure(values=(), state="disabled")
            self._start_button.configure(state="disabled")
            messagebox.showwarning(
                "이미지 부족",
                "월드컵을 시작하려면 유효한 이미지가 2장 이상 필요합니다.",
            )
            return

        values = tuple(f"{size}강" for size in sizes)
        self._round_combo.configure(values=values, state="readonly")
        self._round_var.set(values[-1])
        self._start_button.configure(state="normal")

    def _start_tournament(self) -> None:
        if self._scan_result is None:
            return
        try:
            size = int(self._round_var.get().removesuffix("강"))
            self._tournament = Tournament(self._scan_result.images, size)
        except (ValueError, RuntimeError) as error:
            messagebox.showerror("시작할 수 없음", str(error))
            return
        self._show_match_screen()

    def _show_match_screen(self) -> None:
        tournament = self._tournament
        if tournament is None or tournament.current_match is None:
            return

        self._clear_root()
        self._selection_locked = True

        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=0, minsize=370)
        outer.rowconfigure(0, weight=1)

        game_area = ttk.Frame(outer)
        game_area.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        ttk.Label(
            game_area,
            text=(
                f"{tournament.round_label}  "
                f"{tournament.match_number}/{tournament.round_match_count} 경기"
            ),
            font=(self._font_family, 18, "bold"),
        ).pack(pady=(0, 16))

        loading_row = ttk.Frame(game_area)
        loading_row.pack(fill="x", pady=(0, 10))
        ttk.Label(loading_row, text="이미지를 불러오는 중입니다...").pack(side="left")
        self._loading_bar = ttk.Progressbar(loading_row, mode="indeterminate")
        self._loading_bar.pack(side="left", fill="x", expand=True, padx=(12, 0))
        self._loading_bar.start(10)

        match_frame = ttk.Frame(game_area)
        match_frame.pack(fill="both", expand=True)
        match_frame.columnconfigure(0, weight=1, uniform="match")
        match_frame.columnconfigure(1, weight=1, uniform="match")
        match_frame.rowconfigure(0, weight=1)

        match = tournament.current_match
        for index, entry in enumerate(match.participants):
            card = ttk.Frame(match_frame, padding=8, relief="ridge")
            card.grid(row=0, column=index, sticky="nsew", padx=8)
            card.rowconfigure(0, weight=1)
            card.columnconfigure(0, weight=1)

            canvas = tk.Canvas(
                card,
                background="#202124",
                highlightthickness=0,
                cursor="hand2",
            )
            canvas.grid(row=0, column=0, sticky="nsew")
            canvas.bind("<Button-1>", self._selection_handler(entry))
            canvas.bind("<Configure>", self._schedule_image_render)
            canvas.create_text(
                20,
                20,
                text="불러오는 중...",
                fill="#ffffff",
                anchor="nw",
                font=(self._font_family, 12),
            )
            self._canvases.append(canvas)

            button = ttk.Button(
                card,
                text=entry.name,
                command=lambda selected=entry: self._select_winner(selected),
                state="disabled",
            )
            button.grid(row=1, column=0, sticky="ew", pady=(8, 0), ipady=6)
            self._choice_buttons.append(button)

        self._create_history_panel(outer).grid(row=0, column=1, sticky="nsew")
        self._begin_image_load(tournament.current_match.participants)

    def _begin_image_load(self, entries: tuple[ImageEntry, ...]) -> None:
        self._image_token += 1
        token = self._image_token

        def worker() -> None:
            try:
                images = tuple(load_image_for_display(entry.path) for entry in entries)
                self._image_queue.put((token, images, None))
            except Exception as error:
                self._image_queue.put((token, None, error))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_image_load(self, images: tuple[Image.Image, ...]) -> None:
        self._current_images = images
        if self._loading_bar is not None:
            loading_row = self._loading_bar.master
            self._loading_bar.stop()
            loading_row.destroy()
            self._loading_bar = None
        for button in self._choice_buttons:
            button.configure(state="normal")
        self._selection_locked = False
        self.root.after_idle(self._render_images)

    def _create_history_panel(self, parent: ttk.Frame) -> ttk.Frame:
        panel = ttk.LabelFrame(parent, text="대진 히스토리", padding=10)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        tournament = self._tournament
        completed = len(tournament.history) if tournament is not None else 0
        ttk.Label(panel, text=f"완료된 경기 {completed}개").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        tree = ttk.Treeview(
            panel,
            columns=("matchup", "winner"),
            show="tree headings",
            selectmode="none",
        )
        tree.heading("#0", text="경기")
        tree.heading("matchup", text="대진")
        tree.heading("winner", text="선택")
        tree.column("#0", width=58, minwidth=52, stretch=False)
        tree.column("matchup", width=175, minwidth=120, stretch=True)
        tree.column("winner", width=105, minwidth=80, stretch=True)

        scroll = ttk.Scrollbar(panel, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.grid(row=1, column=0, sticky="nsew")
        scroll.grid(row=1, column=1, sticky="ns")

        if tournament is None:
            return panel

        groups: dict[str, str] = {}

        def round_group(label: str) -> str:
            if label not in groups:
                groups[label] = tree.insert("", "end", text=label, open=True)
            return groups[label]

        for result in tournament.history:
            matchup = f"{result.match.left.name}  vs  {result.match.right.name}"
            tree.insert(
                round_group(result.round_label),
                "end",
                text=f"{result.match_number}경기",
                values=(matchup, f"✓ {result.winner.name}"),
            )

        current = tournament.current_match
        if current is not None:
            tree.insert(
                round_group(tournament.round_label),
                "end",
                text=f"{tournament.match_number}경기",
                values=(f"{current.left.name}  vs  {current.right.name}", "선택 대기"),
                tags=("current",),
            )
            tree.tag_configure("current", background="#e8f4f2")
        return panel

    def _selection_handler(self, entry: ImageEntry) -> Callable[[tk.Event], None]:
        return lambda _event: self._select_winner(entry)

    def _schedule_image_render(self, _event: tk.Event | None = None) -> None:
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(120, self._render_images)

    def _render_images(self) -> None:
        self._resize_job = None
        if len(self._canvases) != len(self._current_images):
            return
        for index, (canvas, source) in enumerate(
            zip(self._canvases, self._current_images, strict=True)
        ):
            width = max(100, canvas.winfo_width() - 20)
            height = max(100, canvas.winfo_height() - 20)
            preview = source.copy()
            preview.thumbnail((width, height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(preview)
            self._photo_images[index] = photo
            canvas.delete("all")
            canvas.create_image(
                canvas.winfo_width() // 2,
                canvas.winfo_height() // 2,
                image=photo,
                anchor="center",
            )

    def _select_winner(self, winner: ImageEntry) -> None:
        if self._selection_locked or self._tournament is None:
            return
        self._selection_locked = True
        try:
            self._tournament.select(winner)
        except (ValueError, RuntimeError) as error:
            self._selection_locked = False
            messagebox.showerror("선택 오류", str(error))
            return

        if self._tournament.is_finished:
            self._show_champion_screen()
        else:
            self._show_match_screen()

    def _abort_for_missing_image(self, error: Exception) -> None:
        messagebox.showerror(
            "이미지를 읽을 수 없음",
            "대회 진행 중 이미지가 삭제되었거나 읽을 수 없게 되었습니다.\n"
            "폴더를 다시 검사합니다.\n\n"
            f"{error}",
        )
        folder = self._selected_folder
        self._scan_result = None
        self._show_start_screen()
        if folder is not None:
            self._begin_scan(folder)

    def _show_champion_screen(self) -> None:
        if self._tournament is None or self._tournament.champion is None:
            return
        champion = self._tournament.champion

        self._clear_root()
        self._photo_images = [None, None]

        outer = ttk.Frame(self.root, padding=24)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=0, minsize=370)
        outer.rowconfigure(0, weight=1)

        winner_area = ttk.Frame(outer)
        winner_area.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        ttk.Label(
            winner_area,
            text="우승",
            font=(self._font_family, 26, "bold"),
        ).pack(pady=(0, 12))
        ttk.Label(
            winner_area,
            text=champion.name,
            font=(self._font_family, 16, "bold"),
        ).pack(pady=(0, 10))

        loading_row = ttk.Frame(winner_area)
        loading_row.pack(fill="x", pady=(0, 10))
        ttk.Label(loading_row, text="우승 이미지를 불러오는 중입니다...").pack(
            side="left"
        )
        self._loading_bar = ttk.Progressbar(loading_row, mode="indeterminate")
        self._loading_bar.pack(side="left", fill="x", expand=True, padx=(12, 0))
        self._loading_bar.start(10)

        canvas = tk.Canvas(
            winner_area,
            background="#202124",
            highlightthickness=0,
            height=420,
        )
        canvas.pack(fill="both", expand=True)
        canvas.bind("<Configure>", self._schedule_image_render)
        self._canvases = [canvas]

        path_var = tk.StringVar(value=str(champion.path))
        ttk.Entry(winner_area, textvariable=path_var, state="readonly").pack(
            fill="x", pady=(12, 12)
        )

        buttons = ttk.Frame(winner_area)
        buttons.pack()
        ttk.Button(
            buttons,
            text="같은 폴더에서 다시 시작",
            command=self._restart_same_folder,
        ).pack(side="left", padx=6, ipadx=8, ipady=5)
        ttk.Button(
            buttons,
            text="새 폴더 선택",
            command=self._choose_new_folder,
        ).pack(side="left", padx=6, ipadx=8, ipady=5)
        self._create_history_panel(outer).grid(row=0, column=1, sticky="nsew")
        self._begin_image_load((champion,))

    def _restart_same_folder(self) -> None:
        folder = self._selected_folder
        self._scan_result = None
        self._show_start_screen()
        if folder is not None:
            self._begin_scan(folder)

    def _choose_new_folder(self) -> None:
        self._selected_folder = None
        self._scan_result = None
        self._show_start_screen()
        self.root.after_idle(self._choose_folder)


def run_app() -> None:
    root = tk.Tk()
    WorldCupApp(root)
    root.mainloop()
