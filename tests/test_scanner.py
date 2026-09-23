from pathlib import Path

from PIL import Image

from image_worldcup.scanner import ImageEntry, canonical_path_key, scan_images


def create_image(path: Path, image_format: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (24, 16), color=(30, 120, 210)).save(path, format=image_format)


def test_scan_images_recursively_filters_and_validates(tmp_path: Path) -> None:
    create_image(tmp_path / "first.JPEG", "JPEG")
    create_image(tmp_path / "nested" / "second.PNG", "PNG")
    create_image(tmp_path / "nested" / "third.webp", "WEBP")
    create_image(tmp_path / "ignored.gif", "GIF")
    (tmp_path / "broken.jpg").write_bytes(b"not an image")

    result = scan_images(tmp_path)

    assert result.valid_count == 3
    assert result.invalid_count == 1
    assert {entry.name for entry in result.images} == {
        "first.JPEG",
        "second.PNG",
        "third.webp",
    }


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
