import random

from PIL import Image, ImageDraw, ImageFilter

from media_bot.services.stage_art import backdrop, glow_line, sparkle
from media_bot.services.stage_text import letter_rows
from media_bot.services.typography import load_font

PALETTES = {
    "gold_lounge": ((42, 30, 20), (239, 194, 108)),
    "diamond_night": ((16, 26, 51), (191, 220, 255)),
    "red_carpet": ((61, 13, 26), (250, 193, 139)),
}


def metallic_letter(char: str, height: int, color: tuple[int, int, int]) -> Image.Image:
    font = load_font(height)
    box = font.getbbox(char)
    mask = Image.new("L", (round(box[2] - box[0]) + 22, round(box[3] - box[1]) + 22))
    ImageDraw.Draw(mask).text((10 - box[0], 5 - box[1]), char, font=font, fill=255, stroke_width=2)
    letter = Image.new("RGBA", mask.size)
    # Extruded edge and contact shadow behind the bright face.
    shadow = Image.new("RGBA", mask.size, (*tuple(c // 4 for c in color), 255))
    shifted = Image.new("L", mask.size)
    shifted.paste(mask, (5, 6))
    letter.paste(shadow, (0, 0), shifted)
    face = Image.new("RGBA", mask.size)
    draw = ImageDraw.Draw(face)
    for y in range(mask.height):
        ratio = y / mask.height
        shine = 1.25 if 0.24 < ratio < 0.4 else (0.65 + 0.45 * (1 - ratio))
        draw.line((0, y, mask.width, y), fill=tuple(min(255, int(c * shine)) for c in color))
    letter.paste(face, (0, 0), mask)
    return letter


def render(
    text: str, preset: str, characters: list[Image.Image], grips: list[tuple[float, float]]
) -> Image.Image:
    rows = letter_rows(text)
    background, gold = PALETTES[preset]
    image = backdrop((1600, 1000), background)
    glow_line(image, (30, 30, 1570, 970), gold)
    draw = ImageDraw.Draw(image)
    # Decorative particles are reproducible, not security material.
    rng = random.Random(17)  # nosec B311
    for _ in range(110):
        particle_x, y = rng.randrange(55, 1545), rng.randrange(70, 930)
        radius = rng.choice((1, 1, 2))
        draw.ellipse((particle_x, y, particle_x + radius, y + radius), fill=(*gold, 85))
    index = 0
    row_height = 840 if len(rows) == 1 else 430
    for row_index, row in enumerate(rows):
        units = sum(0.32 if char == " " else 1 for char in row)
        cell_width = min(370, 1420 / max(units, 1))
        x = (1600 - units * cell_width) / 2
        top = (1000 - row_height * len(rows)) // 2 + row_index * row_height
        for char in row:
            if char == " ":
                x += cell_width * 0.32
                continue
            source = characters[index % len(characters)]
            # Preserve the photographic aspect ratio; letter rests just above cupped hands.
            scale = min((cell_width - 10) / source.width, (row_height - 12) / source.height)
            person = source.resize(
                (round(source.width * scale), round(source.height * scale)),
                Image.Resampling.LANCZOS,
            )
            px = round(x + (cell_width - person.width) / 2)
            py = top + row_height - person.height
            image.alpha_composite(person, (px, py))
            grip_x, grip_y = grips[index % len(characters)]
            baseline = py + round(person.height * grip_y)
            glyph = metallic_letter(char, round(person.height * 0.20), gold)
            if glyph.width > cell_width * 0.68:
                factor = cell_width * 0.68 / glyph.width
                glyph = glyph.resize((round(glyph.width * factor), round(glyph.height * factor)))
            gx, gy = (
                round(px + person.width * grip_x - glyph.width / 2),
                baseline - glyph.height + 16,
            )
            shadow = Image.new("RGBA", image.size)
            shadow.paste((0, 0, 0, 130), (gx + 4, gy + 5), glyph.getchannel("A"))
            image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5)))
            image.alpha_composite(glyph, (gx, gy))
            sparkle(ImageDraw.Draw(image), gx + glyph.width // 3, gy + 12, 6)
            index += 1
            x += cell_width
    return image
