import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


SIZE = 420
PIXEL_SIZE = 1
FRAME_COUNT = 18
FRAME_DURATION_MS = 75
HOLD_DURATION_MS = 1500
BACKGROUND = (10, 25, 47)


def build_frames(source: Path) -> list[Image.Image]:
    with Image.open(source) as image:
        image = ImageOps.fit(
            image.convert("RGB"),
            (SIZE, SIZE),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.4),
        )
    palette_source = Image.new("RGB", (SIZE * 2, SIZE), BACKGROUND)
    palette_source.paste(image, (SIZE, 0))
    palette = palette_source.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    rng = random.Random(29)
    pixels = []
    for y in range(0, SIZE, PIXEL_SIZE):
        for x in range(0, SIZE, PIXEL_SIZE):
            pixels.append(
                (
                    x,
                    y,
                    rng.uniform(-SIZE * 0.15, SIZE * 1.15),
                    rng.uniform(-SIZE * 0.15, SIZE * 1.15),
                    image.getpixel((x, y)),
                )
            )

    frames = []
    for frame_index in range(FRAME_COUNT):
        progress = (frame_index + 1) / FRAME_COUNT
        eased_progress = 1 - (1 - progress) ** 3
        frame = Image.new("RGB", (SIZE, SIZE), BACKGROUND)
        draw = ImageDraw.Draw(frame)
        for x, y, start_x, start_y, color in pixels:
            pixel_x = round(start_x + (x - start_x) * eased_progress)
            pixel_y = round(start_y + (y - start_y) * eased_progress)
            draw.rectangle(
                (pixel_x, pixel_y, pixel_x + PIXEL_SIZE - 1, pixel_y + PIXEL_SIZE - 1),
                fill=color,
            )

        frames.append(frame.quantize(palette=palette, dither=Image.Dither.NONE))

    return frames


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a looping fine-pixel assembly GIF from a portrait photo."
    )
    parser.add_argument("photo", type=Path, help="Path to a JPG, PNG, or other Pillow-readable photo")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("assets/your-photo-animated.gif"),
        help="Output GIF path (default: assets/your-photo-animated.gif)",
    )
    args = parser.parse_args()

    if not args.photo.is_file():
        parser.error(f"photo not found: {args.photo}")

    frames = build_frames(args.photo)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        args.output,
        save_all=True,
        append_images=frames[1:],
        duration=[FRAME_DURATION_MS] * (len(frames) - 1) + [HOLD_DURATION_MS],
        loop=0,
        optimize=True,
        disposal=1,
    )
    print(
        f"Wrote {args.output} ({len(frames)} frames, "
        f"{PIXEL_SIZE}px photo pixels, looping)"
    )


if __name__ == "__main__":
    main()
