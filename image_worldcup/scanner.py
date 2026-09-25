from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable
import warnings

from PIL import Image, ImageOps, ImageSequence


SUPPORTED_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".wav"}
)
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif"})
ANIMATED_IMAGE_EXTENSIONS = frozenset({".gif", ".webp"})
EXTERNAL_MEDIA_EXTENSIONS = frozenset({".mp4", ".wav"})


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

    @property
    def extension(self) -> str:
        return self.path.suffix.casefold()

    @property
    def is_playable(self) -> bool:
        return self.extension in ANIMATED_IMAGE_EXTENSIONS | EXTERNAL_MEDIA_EXTENSIONS

    @property
    def opens_in_external_player(self) -> bool:
        return self.extension in EXTERNAL_MEDIA_EXTENSIONS


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


def _validate_mp4(path: Path) -> bool:
    try:
        with path.open("rb") as source:
            header = source.read(12)
        return len(header) == 12 and header[4:8] == b"ftyp"
    except OSError:
        return False


def _validate_wav(path: Path) -> bool:
    try:
        with path.open("rb") as source:
            header = source.read(12)
        return (
            len(header) == 12
            and header[:4] in {b"RIFF", b"RIFX"}
            and header[8:12] == b"WAVE"
        )
    except OSError:
        return False


def _validate_media(path: Path) -> bool:
    extension = path.suffix.casefold()
    if extension in IMAGE_EXTENSIONS:
        return _validate_image(path)
    if extension == ".mp4":
        return _validate_mp4(path)
    if extension == ".wav":
        return _validate_wav(path)
    return False


def normalize_extensions(extensions: Iterable[str] | None) -> frozenset[str]:
    if extensions is None:
        return SUPPORTED_EXTENSIONS
    normalized = frozenset(
        extension.casefold()
        if extension.startswith(".")
        else f".{extension.casefold()}"
        for extension in extensions
    )
    unknown = normalized - SUPPORTED_EXTENSIONS
    if unknown:
        raise ValueError(f"지원하지 않는 확장자입니다: {', '.join(sorted(unknown))}")
    return normalized


def scan_images(
    folder: Path | str,
    extensions: Iterable[str] | None = None,
) -> ScanResult:
    root = Path(folder).expanduser().resolve(strict=False)
    if not root.is_dir():
        raise ValueError(f"폴더를 찾을 수 없습니다: {root}")
    selected_extensions = normalize_extensions(extensions)

    images: list[ImageEntry] = []
    seen_paths: set[str] = set()
    invalid_count = 0

    for current_root, _, file_names in os.walk(root, followlinks=False):
        current_folder = Path(current_root)
        for file_name in file_names:
            path = current_folder / file_name
            if path.suffix.casefold() not in selected_extensions:
                continue

            key = canonical_path_key(path)
            if key in seen_paths:
                invalid_count += 1
                continue
            seen_paths.add(key)

            if _validate_media(path):
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


def load_animation_for_display(
    path: Path,
) -> tuple[tuple[Image.Image, ...], tuple[int, ...]]:
    """Load detached animation frames and their display durations."""

    frames: list[Image.Image] = []
    durations: list[int] = []
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as source:
            for frame in ImageSequence.Iterator(source):
                oriented = ImageOps.exif_transpose(frame)
                frames.append(oriented.convert("RGBA"))
                duration = int(frame.info.get("duration", source.info.get("duration", 100)))
                durations.append(max(20, min(duration, 10_000)))

    if not frames:
        raise ValueError(f"표시할 프레임이 없습니다: {path}")
    return tuple(frames), tuple(durations)
