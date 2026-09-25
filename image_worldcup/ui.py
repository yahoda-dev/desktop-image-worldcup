from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from PIL import Image, ImageTk

from image_worldcup.scanner import (
    ANIMATED_IMAGE_EXTENSIONS,
    EXTERNAL_MEDIA_EXTENSIONS,
    ImageEntry,
    ScanResult,
    load_animation_for_display,
    load_image_for_display,
    scan_images,
)
from image_worldcup.resources import configure_fonts, set_window_icon
from image_worldcup.tournament import Tournament, allowed_round_sizes


@dataclass(frozen=True, slots=True)
class MediaPreview:
    frames: tuple[Image.Image, ...] = ()
    durations: tuple[int, ...] = ()

    @property
    def is_animated(self) -> bool:
        return len(self.frames) > 1


class WorldCupApp:
    EXTENSION_OPTIONS = ("jpg", "jpeg", "png", "webp", "gif", "mp4", "wav")

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
            tuple[int, tuple[MediaPreview, ...] | None, Exception | None]
        ] = queue.Queue()
        self._tournament: Tournament | None = None
        self._current_entries: tuple[ImageEntry, ...] = ()
        self._current_media: tuple[MediaPreview, ...] = ()
        self._photo_images: list[ImageTk.PhotoImage | None] = [None, None]
        self._canvases: list[tk.Canvas] = []
        self._animation_jobs: list[str | None] = []
        self._animation_playing: list[bool] = []
        self._animation_frame_indices: list[int] = []
        self._resize_job: str | None = None
        self._selection_locked = False
        self._choice_buttons: list[ttk.Button] = []
        self._loading_bar: ttk.Progressbar | None = None
        self._extension_values = {
            extension: True for extension in self.EXTENSION_OPTIONS
        }
        self._extension_vars: dict[str, tk.BooleanVar] = {}

        self._show_start_screen()
        self.root.after(100, self._poll_scan_queue)

    def _clear_root(self) -> None:
        self._image_token += 1
        for job in self._animation_jobs:
            if job is not None:
                self.root.after_cancel(job)
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
            self._resize_job = None
        for child in self.root.winfo_children():
            child.destroy()
        self._canvases = []
        self._current_entries = ()
        self._current_media = ()
        self._photo_images = [None, None]
        self._animation_jobs = []
        self._animation_playing = []
        self._animation_frame_indices = []
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
            text="사용할 파일 형식을 고른 뒤 미디어가 있는 폴더를 선택하세요.",
        ).pack(pady=(0, 28))

        extension_group = ttk.LabelFrame(container, text="사용할 확장자", padding=12)
        extension_group.pack(fill="x", pady=(0, 14))
        self._extension_vars = {}
        for column, extension in enumerate(self.EXTENSION_OPTIONS):
            variable = tk.BooleanVar(value=self._extension_values[extension])
            self._extension_vars[extension] = variable
            ttk.Checkbutton(
                extension_group,
                text=extension.upper(),
                variable=variable,
                command=self._extensions_changed,
            ).grid(row=0, column=column, padx=8, sticky="w")
            extension_group.columnconfigure(column, weight=1)
        ttk.Label(
            extension_group,
            text="GIF·애니메이션 WebP는 화면에서, MP4·WAV는 기본 플레이어에서 재생됩니다.",
        ).grid(row=1, column=0, columnspan=len(self.EXTENSION_OPTIONS), pady=(10, 0))

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
        if not self._selected_extensions():
            messagebox.showwarning("확장자 선택 필요", "확장자를 하나 이상 선택해 주세요.")
            return
        selected = filedialog.askdirectory(title="미디어 폴더 선택")
        if not selected:
            return
        self._selected_folder = Path(selected).resolve(strict=False)
        self._folder_var.set(str(self._selected_folder))
        self._begin_scan(self._selected_folder)

    def _selected_extensions(self) -> frozenset[str]:
        return frozenset(
            f".{extension}"
            for extension, variable in self._extension_vars.items()
            if variable.get()
        )

    def _extensions_changed(self) -> None:
        self._extension_values = {
            extension: variable.get()
            for extension, variable in self._extension_vars.items()
        }
        extensions = self._selected_extensions()
        if not extensions:
            self._scan_token += 1
            self._scan_result = None
            self._stop_scan_progress()
            self._status_var.set("확장자를 하나 이상 선택해 주세요.")
            self._round_var.set("")
            self._round_combo.configure(values=(), state="disabled")
            self._start_button.configure(state="disabled")
            return
        if self._selected_folder is not None:
            self._begin_scan(self._selected_folder)

    def _begin_scan(self, folder: Path) -> None:
        self._scan_token += 1
        token = self._scan_token
        self._scan_result = None
        self._status_var.set("미디어 파일을 검사하고 있습니다...")
        self._scan_progress.pack(pady=(0, 16), before=self._round_row)
        self._scan_progress.start(12)
        self._round_var.set("")
        self._round_combo.configure(values=(), state="disabled")
        self._start_button.configure(state="disabled")
        extensions = self._selected_extensions()

        def worker() -> None:
            try:
                result = scan_images(folder, extensions)
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
            f"사용 가능한 미디어 {result.valid_count}개 · 제외된 파일 {result.invalid_count}개"
        )
        sizes = allowed_round_sizes(result.valid_count)
        if not sizes:
            self._round_var.set("")
            self._round_combo.configure(values=(), state="disabled")
            self._start_button.configure(state="disabled")
            messagebox.showwarning(
                "미디어 부족",
                "월드컵을 시작하려면 유효한 미디어가 2개 이상 필요합니다.",
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
        ttk.Label(
            game_area,
            text="재생 형식은 화면을 클릭해 재생/일시정지하고, 아래 파일명 버튼으로 선택하세요.",
        ).pack(pady=(0, 10))

        loading_row = ttk.Frame(game_area)
        loading_row.pack(fill="x", pady=(0, 10))
        ttk.Label(loading_row, text="미디어를 불러오는 중입니다...").pack(side="left")
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
            if entry.is_playable:
                canvas.bind("<Button-1>", self._playback_handler(index, entry))
            else:
                canvas.bind("<Button-1>", self._selection_handler(entry))
            canvas.bind("<Configure>", self._schedule_image_render)
            loading_text = (
                "재생 준비 중..." if entry.is_playable else "불러오는 중..."
            )
            canvas.create_text(
                20, 20, text=loading_text, fill="#ffffff", anchor="nw",
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
        self._current_entries = entries

        def worker() -> None:
            try:
                previews: list[MediaPreview] = []
                for entry in entries:
                    if entry.extension in EXTERNAL_MEDIA_EXTENSIONS:
                        previews.append(MediaPreview())
                    elif entry.extension in ANIMATED_IMAGE_EXTENSIONS:
                        frames, durations = load_animation_for_display(entry.path)
                        previews.append(MediaPreview(frames, durations))
                    else:
                        previews.append(
                            MediaPreview((load_image_for_display(entry.path),), (100,))
                        )
                self._image_queue.put((token, tuple(previews), None))
            except Exception as error:
                self._image_queue.put((token, None, error))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_image_load(self, previews: tuple[MediaPreview, ...]) -> None:
        self._current_media = previews
        self._animation_jobs = [None] * len(previews)
        self._animation_playing = [False] * len(previews)
        self._animation_frame_indices = [0] * len(previews)
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

    def _playback_handler(
        self, index: int, entry: ImageEntry
    ) -> Callable[[tk.Event], None]:
        return lambda _event: self._toggle_playback(index, entry)

    def _toggle_playback(self, index: int, entry: ImageEntry) -> None:
        if entry.opens_in_external_player:
            self._open_in_default_player(entry.path)
            return
        if index >= len(self._current_media):
            return
        preview = self._current_media[index]
        if not preview.is_animated:
            self._select_winner(entry)
            return
        self._animation_playing[index] = not self._animation_playing[index]
        if self._animation_playing[index]:
            self._schedule_next_frame(index)
        else:
            job = self._animation_jobs[index]
            if job is not None:
                self.root.after_cancel(job)
                self._animation_jobs[index] = None
        self._render_media(index)

    def _open_in_default_player(self, path: Path) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except (OSError, subprocess.SubprocessError) as error:
            messagebox.showerror("재생 실패", f"기본 플레이어를 열 수 없습니다.\n\n{error}")

    def _schedule_next_frame(self, index: int) -> None:
        if index >= len(self._current_media) or not self._animation_playing[index]:
            return
        preview = self._current_media[index]
        frame_index = self._animation_frame_indices[index]
        duration = preview.durations[frame_index]
        self._animation_jobs[index] = self.root.after(
            duration, lambda: self._advance_animation(index)
        )

    def _advance_animation(self, index: int) -> None:
        if index >= len(self._current_media) or not self._animation_playing[index]:
            return
        preview = self._current_media[index]
        self._animation_frame_indices[index] = (
            self._animation_frame_indices[index] + 1
        ) % len(preview.frames)
        self._animation_jobs[index] = None
        self._render_media(index)
        self._schedule_next_frame(index)

    def _schedule_image_render(self, _event: tk.Event | None = None) -> None:
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(120, self._render_images)

    def _render_images(self) -> None:
        self._resize_job = None
        if len(self._canvases) != len(self._current_media):
            return
        for index in range(len(self._current_media)):
            self._render_media(index)

    def _render_media(self, index: int) -> None:
        if index >= len(self._canvases) or index >= len(self._current_media):
            return
        canvas = self._canvases[index]
        preview = self._current_media[index]
        entry = self._current_entries[index]
        canvas.delete("all")

        if not preview.frames:
            media_name = "동영상" if entry.extension == ".mp4" else "오디오"
            canvas.create_text(
                canvas.winfo_width() // 2,
                canvas.winfo_height() // 2,
                text=f"▶ {media_name}\n\n클릭하면 기본 플레이어에서 재생됩니다.",
                fill="#ffffff",
                justify="center",
                font=(self._font_family, 16, "bold"),
                anchor="center",
            )
            return

        frame_index = self._animation_frame_indices[index]
        source = preview.frames[frame_index]
        width = max(100, canvas.winfo_width() - 20)
        height = max(100, canvas.winfo_height() - 20)
        rendered = source.copy()
        rendered.thumbnail((width, height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(rendered)
        self._photo_images[index] = photo
        canvas.create_image(
            canvas.winfo_width() // 2,
            canvas.winfo_height() // 2,
            image=photo,
            anchor="center",
        )
        if preview.is_animated:
            state = "Ⅱ 일시정지" if self._animation_playing[index] else "▶ 재생"
            canvas.create_text(
                16,
                16,
                text=state,
                fill="#ffffff",
                anchor="nw",
                font=(self._font_family, 11, "bold"),
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
            "미디어를 읽을 수 없음",
            "대회 진행 중 미디어가 삭제되었거나 읽을 수 없게 되었습니다.\n"
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
        ttk.Label(loading_row, text="우승 미디어를 불러오는 중입니다...").pack(
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
            cursor="hand2" if champion.is_playable else "",
        )
        canvas.pack(fill="both", expand=True)
        canvas.bind("<Configure>", self._schedule_image_render)
        if champion.is_playable:
            canvas.bind("<Button-1>", self._playback_handler(0, champion))
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
