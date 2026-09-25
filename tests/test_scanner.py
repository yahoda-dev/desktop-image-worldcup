from pathlib import Path

from PIL import Image

from image_worldcup.scanner import (
    ImageEntry,
    canonical_path_key,
    load_animation_for_display,
    normalize_extensions,
    scan_images,
)


def create_image(path: Path, image_format: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (24, 16), color=(30, 120, 210)).save(path, format=image_format)


def test_scan_images_recursively_filters_and_validates(tmp_path: Path) -> None:
    create_image(tmp_path / "first.JPEG", "JPEG")
    create_image(tmp_path / "nested" / "second.PNG", "PNG")
    create_image(tmp_path / "nested" / "third.webp", "WEBP")
    create_image(tmp_path / "ignored.gif", "GIF")
    (tmp_path / "broken.jpg").write_bytes(b"not an image")

    result = scan_images(tmp_path, {"jpg", "jpeg", "png", "webp"})

    assert result.valid_count == 3
    assert result.invalid_count == 1
    assert {entry.name for entry in result.images} == {
        "first.JPEG",
        "second.PNG",
        "third.webp",
    }


def test_scan_uses_selected_extensions(tmp_path: Path) -> None:
    create_image(tmp_path / "photo.jpg", "JPEG")
    create_image(tmp_path / "animation.gif", "GIF")
    (tmp_path / "movie.mp4").write_bytes(
        b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    )
    (tmp_path / "sound.wav").write_bytes(
        b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
    )

    result = scan_images(tmp_path, {".gif", ".mp4", ".wav"})

    assert {entry.name for entry in result.images} == {
        "animation.gif",
        "movie.mp4",
        "sound.wav",
    }
    assert result.invalid_count == 0


def test_scan_rejects_invalid_selected_media(tmp_path: Path) -> None:
    (tmp_path / "broken.mp4").write_bytes(b"not an mp4")
    (tmp_path / "broken.wav").write_bytes(b"not a wav")

    result = scan_images(tmp_path, {"mp4", "wav"})

    assert result.valid_count == 0
    assert result.invalid_count == 2


def test_normalize_extensions_rejects_unknown_format() -> None:
    try:
        normalize_extensions({"bmp"})
    except ValueError as error:
        assert ".bmp" in str(error)
    else:
        raise AssertionError("지원하지 않는 확장자는 거부되어야 합니다.")


def test_load_animation_returns_frames_and_durations(tmp_path: Path) -> None:
    path = tmp_path / "animated.gif"
    first = Image.new("RGB", (8, 8), "red")
    second = Image.new("RGB", (8, 8), "blue")
    first.save(path, save_all=True, append_images=[second], duration=[40, 80], loop=0)

    frames, durations = load_animation_for_display(path)

    assert len(frames) == 2
    assert durations == (40, 80)


def test_canonical_path_key_normalizes_equivalent_paths(tmp_path: Path) -> None:
    image_path = tmp_path / "folder" / "photo.png"
    image_path.parent.mkdir()

    direct = ImageEntry(image_path)
    equivalent = ImageEntry(tmp_path / "folder" / ".." / "folder" / "photo.png")

    assert direct.key == equivalent.key
    assert canonical_path_key(image_path) == direct.key


def test_scan_rejects_missing_folder(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    try:
        scan_images(missing)
    except ValueError as error:
        assert str(missing) in str(error)
    else:
        raise AssertionError("존재하지 않는 폴더는 거부되어야 합니다.")


def test_scan_excludes_decompression_bomb(tmp_path: Path, monkeypatch) -> None:
    oversized = tmp_path / "oversized.png"
    create_image(oversized, "PNG")
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 10)

    result = scan_images(tmp_path)

    assert result.valid_count == 0
    assert result.invalid_count == 1
