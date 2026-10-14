import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from media_bot.services.typography import load_font


def render_tiles(text: str, workspace: Path, style: str) -> Path:
    """Render a transparent emoji strip and split it into 100px PNG tiles."""
    tile_size, padding = 100, 20
    font = load_font(76)
    probe = Image.new("RGBA", (1, 1))
    bbox = ImageDraw.Draw(probe).textbbox((0, 0), text, font=font, stroke_width=2)
    width = max(tile_size, bbox[2] - bbox[0] + padding * 2)
    columns = math.ceil(width / tile_size)
    canvas = Image.new("RGBA", (columns * tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    x = (canvas.width - draw.textlength(text, font=font)) / 2
    y = (tile_size - 76) / 2 - bbox[1]

    if style == "blood":
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).text((x + 3, y + 5), text, font=font, fill="#260006", stroke_width=5)
        canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(3)))
        draw.text((x, y), text, font=font, fill="#7b0010", stroke_width=3, stroke_fill="#250006")
        draw.text(
            (x, y - 2), text, font=font, fill="#e10b21", stroke_width=1, stroke_fill="#ff6c6c"
        )
        # Deterministic visual effect; this is not security material.
        rng = random.Random(text)  # nosec B311
        for position in range(8):
            drop_x = rng.randrange(max(1, canvas.width))
            drop_y = rng.randrange(72, 94)
            radius = 1 + position % 3
            draw.ellipse(
                (drop_x - radius, drop_y - radius, drop_x + radius, drop_y + radius * 2),
                fill="#b40016",
            )
    elif style == "ghost":
        glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).text((x, y), text, font=font, fill="#bdfcff", stroke_width=4)
        canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6)))
        draw.text((x, y), text, font=font, fill="#eaffff", stroke_width=2, stroke_fill="#5ccbd1")
        for ghost_x in range(10, canvas.width, 24):
            draw.arc((ghost_x, 78, ghost_x + 18, 98), 180, 360, fill="#bdfcff", width=2)
    else:
        draw.text(
            (x + 3, y + 4), text, font=font, fill="#050505", stroke_width=5, stroke_fill="#000000"
        )
        draw.text((x, y), text, font=font, fill="#22252a", stroke_width=3, stroke_fill="#050505")
        draw.line((0, 20, canvas.width, 80), fill="#747b84", width=1)
        draw.text(
            (x, y - 2), text, font=font, fill="#a6adb4", stroke_width=1, stroke_fill="#343a40"
        )

    workspace.mkdir(parents=True, exist_ok=True)
    for column in range(columns):
        canvas.crop((column * tile_size, 0, (column + 1) * tile_size, tile_size)).save(
            workspace / f"tile-{column:03d}.png", format="PNG"
        )
    preview = workspace / "emoji-preview.png"
    canvas.save(preview, format="PNG")
    return preview
