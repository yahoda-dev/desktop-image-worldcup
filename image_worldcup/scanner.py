from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import warnings

from PIL import Image, ImageOps


SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})


def canonical_path_key(path: Path) -> str:
    """Return a Windows-compatible, case-insensitive identity for a path."""

    resolved = path.expanduser().resolve(strict=False)
    return str(resolved).replace("\\", "/").casefold()


@dataclass(frozen=True, slots=True)
class ImageEntry:
    path: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", self.path.expanduser().resolve(strict=False))

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def key(self) -> str:
        return canonical_path_key(self.path)


@dataclass(frozen=True, slots=True)
class ScanResult:
    images: tuple[ImageEntry, ...]
    invalid_count: int

    @property
    def valid_count(self) -> int:
        return len(self.images)


def _validate_image(path: Path) -> bool:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                image.seek(0)
                image.load()
        return True
    except Exception:
        return False


def scan_images(folder: Path | str) -> ScanResult:
    root = Path(folder).expanduser().resolve(strict=False)
    if not root.is_dir():
        raise ValueError(f"폴더를 찾을 수 없습니다: {root}")

    images: list[ImageEntry] = []
    seen_paths: set[str] = set()
    invalid_count = 0

    for current_root, _, file_names in os.walk(root, followlinks=False):
        current_folder = Path(current_root)
        for file_name in file_names:
            path = current_folder / file_name
            if path.suffix.casefold() not in SUPPORTED_EXTENSIONS:
                continue

            key = canonical_path_key(path)
            if key in seen_paths:
                invalid_count += 1
                continue
            seen_paths.add(key)

            if _validate_image(path):
                images.append(ImageEntry(path))
            else:
                invalid_count += 1

    images.sort(key=lambda entry: entry.key)
    return ScanResult(tuple(images), invalid_count)


def load_image_for_display(path: Path) -> Image.Image:
    """Load the first frame, apply EXIF orientation, and detach it from the file."""

    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as source:
            source.seek(0)
            oriented = ImageOps.exif_transpose(source)
            return oriented.convert("RGBA")
