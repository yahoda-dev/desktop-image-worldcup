from __future__ import annotations

import argparse


def smoke_test() -> int:
    import tkinter

    from PIL import __version__ as pillow_version
    from PIL import Image
    from PIL import features

    from image_worldcup.resources import resource_path

    if not features.check("webp"):
        raise RuntimeError("Pillow WebP 지원을 사용할 수 없습니다.")
    icon_path = resource_path("assets", "icons", "app-icon.png")
    font_path = resource_path("assets", "fonts", "NotoSansKR[wght].ttf")
    if not font_path.is_file():
        raise RuntimeError("번들 폰트를 찾을 수 없습니다.")
    with Image.open(icon_path) as icon:
        icon.verify()
    print(
        f"Python GUI 준비 완료: Tk {tkinter.TkVersion}, "
        f"Pillow {pillow_version}, WebP 지원, 앱 리소스 준비 완료"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="로컬 이미지 이상형 월드컵")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="GUI를 열지 않고 런타임 의존성을 검사합니다.",
    )
    args = parser.parse_args()

    if args.smoke_test:
        return smoke_test()

    from image_worldcup.resources import configure_app_identity
    from image_worldcup.ui import run_app

    configure_app_identity()
    run_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
