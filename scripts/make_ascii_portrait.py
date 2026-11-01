import argparse
import html
from pathlib import Path

from PIL import Image, ImageOps


RAMP = " .:-=+*#%@"
WIDTH = 100
HEIGHT = 60
FONT_SIZE = 8
LINE_HEIGHT = 8


def build_svg(source: Path) -> str:
    image = Image.open(source).convert("RGB")
    image = ImageOps.fit(image, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
    grayscale = ImageOps.autocontrast(ImageOps.grayscale(image))

    rows = []
    for row_index in range(HEIGHT):
        y = 58 + row_index * LINE_HEIGHT
        pixels = []
        for value in (grayscale.getpixel((x, row_index)) for x in range(WIDTH)):
            ramp_index = round((255 - value) * (len(RAMP) - 1) / 255)
            pixels.append(RAMP[ramp_index])
        text = html.escape("".join(pixels))
        delay = row_index * 0.045
        rows.append(
            f'<text x="10" y="{y}" opacity="1">{text}'
            f'<animate attributeName="opacity" values="0;1" '
            f'begin="{delay:.3f}s" dur="0.18s" fill="freeze" />'
            "</text>"
        )

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="500" height="600" '
        'viewBox="0 0 500 600" role="img" aria-labelledby="title description">'
        "<title id=\"title\">Ajay Varsan ASCII portrait</title>"
        "<desc id=\"description\">A monochrome ASCII portrait that reveals row by row.</desc>"
        '<rect width="500" height="600" rx="12" fill="#0A192F" />'
        '<g fill="#D1D5DB" font-family="Consolas, Courier New, monospace" '
        'font-size="8" xml:space="preserve">'
        + "".join(rows)
        + "</g></svg>"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Turn a portrait photo into an animated ASCII SVG."
    )
    parser.add_argument("photo", type=Path, help="Path to a JPG, PNG, or other Pillow-readable photo")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("assets/ajay-ascii.svg"),
        help="Output SVG path (default: assets/ajay-ascii.svg)",
    )
    args = parser.parse_args()

    if not args.photo.is_file():
        parser.error(f"photo not found: {args.photo}")

    svg = build_svg(args.photo)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
