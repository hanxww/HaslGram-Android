#!/usr/bin/env python3
"""Generate HaslGram-branded Android icon resources from branding/haslgram-icon.webp.

Source artwork derives from the previously approved HaslGram channel/app avatar.
Do not replace GPL attribution or upstream source notices.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image, ImageDraw

DENSITIES = {
    "mdpi": 48,
    "hdpi": 72,
    "xhdpi": 96,
    "xxhdpi": 144,
    "xxxhdpi": 192,
}


def write_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    args = p.parse_args()

    branding_dir = Path(__file__).resolve().parent.parent / "branding"
    source = branding_dir / "haslgram-icon.webp"
    if not source.is_file():
        raise FileNotFoundError(f"Missing checked-in branding asset: {source}")

    icon = Image.open(source).convert("RGBA")
    if icon.width != icon.height or icon.width < 192:
        raise ValueError("HaslGram brand icon must be square and >=192px")
    resources = args.source / "TMessagesProj/src/main/res"
    written = 0
    for density, size in DENSITIES.items():
        folder = resources / f"mipmap-{density}"
        if not folder.is_dir():
            raise FileNotFoundError(folder)
        scaled = icon.resize((size, size), Image.Resampling.LANCZOS)

        # Android must not contain both PNG and WebP with the same resource ID.
        for filename in ("ic_launcher.webp", "ic_launcher_round.webp", "ic_launcher_foreground.webp"):
            (folder / filename).unlink(missing_ok=True)
        write_png(scaled, folder / "ic_launcher.png")
        write_png(scaled, folder / "ic_launcher_foreground.png")
        circular_mask = Image.new("L", (size, size))
        ImageDraw.Draw(circular_mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        circular = scaled.copy()
        circular.putalpha(circular_mask)
        write_png(circular, folder / "ic_launcher_round.png")
        written += 3

        # The upstream alternative launcher icons must not let users switch
        # back to Telegram/OwpenGram artwork from the appearance settings.
        for old_icon in folder.glob("icon_*.png"):
            if "foreground" in old_icon.name or "launcher" in old_icon.name:
                write_png(scaled, old_icon)
                written += 1

    # Used by the server selector, Android 12 splash, and introductory screen.
    nodpi = resources / "drawable-nodpi"
    write_png(icon.resize((512, 512), Image.Resampling.LANCZOS), nodpi / "server_owpengram.png")
    written += 1

    color_xml = resources / "values" / "ic_launcher_background.xml"
    colors = color_xml.read_text(encoding="utf-8")
    if "#E9E9EE" not in colors:
        raise ValueError("Unknown upstream launcher background; refusing blind edit")
    color_xml.write_text(colors.replace("#E9E9EE", "#0750C7"), encoding="utf-8")

    print(f"HaslGram branding generated: {written} PNG icon resources and splash logo")


if __name__ == "__main__":
    main()
