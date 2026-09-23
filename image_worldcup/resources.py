from __future__ import annotations

import ctypes
from pathlib import Path
import sys
import tkinter as tk
from tkinter import font as tkfont


APP_FONT_FAMILY = "Noto Sans KR"


def resource_path(*parts: str) -> Path:
    """Return a path that works both from source and a PyInstaller bundle."""

    bundle_root = getattr(sys, "_MEIPASS", None)
    base = Path(bundle_root) if bundle_root else Path(__file__).resolve().parent.parent
    return base.joinpath(*parts)


def configure_app_identity() -> None:
    """Give Windows a stable taskbar identity for the bundled application."""

    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(  # type: ignore[attr-defined]
                "yahoda.desktop-image-worldcup"
            )
        except (AttributeError, OSError):
            pass


def _register_windows_font(path: Path) -> bool:
    try:
        return bool(
            ctypes.windll.gdi32.AddFontResourceExW(str(path), 0x10, None)  # type: ignore[attr-defined]
        )
    except (AttributeError, OSError):
        return False


def _register_macos_font(path: Path) -> bool:
    try:
        core_foundation = ctypes.CDLL(
            "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
        )
        core_text = ctypes.CDLL(
            "/System/Library/Frameworks/CoreText.framework/CoreText"
        )
        core_foundation.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
        core_foundation.CFURLCreateFromFileSystemRepresentation.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_long,
            ctypes.c_bool,
        ]
        core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
        core_text.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool
        core_text.CTFontManagerRegisterFontsForURL.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]

        encoded = str(path).encode("utf-8")
        url = core_foundation.CFURLCreateFromFileSystemRepresentation(
            None, encoded, len(encoded), False
        )
        if not url:
            return False
        try:
            return bool(core_text.CTFontManagerRegisterFontsForURL(url, 1, None))
        finally:
            core_foundation.CFRelease(url)
    except (AttributeError, OSError):
        return False


def configure_fonts(root: tk.Tk) -> str:
    """Register the bundled OFL font and apply it to Tk's named fonts."""

    font_path = resource_path("assets", "fonts", "NotoSansKR[wght].ttf")
    registered = False
    if font_path.is_file():
        if sys.platform == "win32":
            registered = _register_windows_font(font_path)
        elif sys.platform == "darwin":
            registered = _register_macos_font(font_path)

    families = set(tkfont.families(root))
    family = APP_FONT_FAMILY if registered or APP_FONT_FAMILY in families else "TkDefaultFont"
    for name in (
        "TkDefaultFont",
        "TkTextFont",
        "TkFixedFont",
        "TkMenuFont",
        "TkHeadingFont",
        "TkCaptionFont",
        "TkSmallCaptionFont",
        "TkIconFont",
        "TkTooltipFont",
    ):
        try:
            tkfont.nametofont(name, root=root).configure(family=family)
        except tk.TclError:
            continue
    return family


def set_window_icon(root: tk.Tk) -> None:
    icon_path = resource_path("assets", "icons", "app-icon.png")
    if not icon_path.is_file():
        return
    try:
        icon = tk.PhotoImage(master=root, file=icon_path)
        root.iconphoto(True, icon)
        root._app_icon = icon  # type: ignore[attr-defined]
    except tk.TclError:
        pass
