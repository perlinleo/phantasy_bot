"""Small procedural lighting elements shared by both illustrated stages."""

import math

from PIL import Image, ImageDraw, ImageFilter


def backdrop(size: tuple[int, int], color: tuple[int, int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        light = 0.4 + 0.6 * math.sin(math.pi * y / height)
        draw.line((0, y, width, y), fill=tuple(int(c * light) for c in color))
    # Velvet folds; quiet enough to keep type readable.
    for x in range(0, width, 3):
        strength = (math.sin(x / 34) + 1) / 2
        shade = tuple(int(c * (0.4 + strength * 0.6)) for c in color)
        draw.line((x, 0, x, int(height * 0.82)), fill=shade, width=3)
    draw.rectangle((0, int(height * 0.82), width, height), fill=(12, 10, 17))
    return image.convert("RGBA")


def glow_line(
    image: Image.Image, box: tuple[int, int, int, int], color: tuple[int, int, int]
) -> None:
    light = Image.new("RGBA", image.size)
    draw = ImageDraw.Draw(light)
    draw.rounded_rectangle(box, radius=24, outline=(*color, 180), width=6)
    image.alpha_composite(light.filter(ImageFilter.GaussianBlur(15)))
    ImageDraw.Draw(image).rounded_rectangle(box, radius=24, outline=(*color, 220), width=2)


def sparkle(draw: ImageDraw.ImageDraw, x: int, y: int, radius: int) -> None:
    draw.line((x - radius, y, x + radius, y), fill="#fff4d7", width=2)
    draw.line((x, y - radius, x, y + radius), fill="#fff4d7", width=2)
