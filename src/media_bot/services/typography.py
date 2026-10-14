from pathlib import Path

from PIL import ImageFont


def load_font(size: int) -> ImageFont.FreeTypeFont:
    """Load a Cyrillic-capable font installed in the image."""
    candidates = (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    )
    for font_path in candidates:
        if font_path.exists():
            return ImageFont.truetype(font_path, size=size)
    raise RuntimeError("DejaVu Sans is unavailable; install fonts-dejavu-core")
