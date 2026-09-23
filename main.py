from __future__ import annotations

import argparse


def smoke_test() -> int:
    import tkinter

    from PIL import __version__ as pillow_version
    from PIL import features

    if not features.check("webp"):
        raise RuntimeError("Pillow WebP 지원을 사용할 수 없습니다.")
    print(
        f"Python GUI 준비 완료: Tk {tkinter.TkVersion}, "
        f"Pillow {pillow_version}, WebP 지원"
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

    from image_worldcup.ui import run_app

    run_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
