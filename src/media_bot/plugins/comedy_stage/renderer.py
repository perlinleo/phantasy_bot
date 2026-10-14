import math
from collections.abc import Iterator

from PIL import Image, ImageDraw, ImageFilter

from media_bot.plugin_sdk.contracts import JobContext
from media_bot.services.stage_art import backdrop, glow_line
from media_bot.services.stage_text import fit_stage_text
from media_bot.services.typography import load_font


def ease(value: float) -> float:
    value = max(0, min(1, value))
    return value * value * (3 - 2 * value)


class Stage:
    def __init__(self, text: str, preset: str, characters: list[Image.Image]) -> None:
        neon = preset == "neon_roast"
        self.accent = (112, 176, 255) if neon else (255, 182, 97)
        self.background = backdrop((1280, 720), (30, 13, 62) if neon else (85, 12, 28))
        glow_line(self.background, (22, 22, 1258, 697), self.accent)
        draw = ImageDraw.Draw(self.background)
        draw.text((640, 55), "COMEDY NIGHT", font=load_font(26), fill=self.accent, anchor="mm")
        draw.text((640, 672), "ВОЛЯ  ×  ХАРЛАМОВ", font=load_font(19), fill="#baa997", anchor="mm")
        # Table and stage floor behind the cast.
        draw.ellipse((541, 562, 739, 584), fill="#21151d", outline=self.accent, width=2)
        draw.rectangle((632, 583, 648, 640), fill="#30232a")
        draw.ellipse((587, 633, 693, 646), fill="#30232a")
        self.board = Image.new("RGBA", (740, 290), (0, 0, 0, 0))
        board_draw = ImageDraw.Draw(self.board)
        board_draw.rounded_rectangle(
            (0, 0, 739, 289), radius=22, fill="#100e18", outline=self.accent, width=3
        )
        lines, font = fit_stage_text(text)
        spacing = font.size + 16
        y = (290 - len(lines) * spacing) / 2 + spacing / 2
        for line in lines:
            board_draw.text((370, y), line, font=font, fill="#fff7e7", anchor="mm")
            y += spacing
        self.cast: list[Image.Image] = []
        for source in characters:
            factor = min(330 / source.width, 530 / source.height)
            person = source.resize(
                (round(source.width * factor), round(source.height * factor)),
                Image.Resampling.LANCZOS,
            )
            cell = Image.new("RGBA", (340, 540))
            cell.alpha_composite(person, ((340 - person.width) // 2, 540 - person.height))
            self.cast.append(cell)

    def frame(self, seconds: float, duration: int) -> Image.Image:
        image = self.background.copy()
        light = Image.new("RGBA", image.size)
        light_draw = ImageDraw.Draw(light)
        for origin, phase in ((115, 0.0), (1165, 2.0)):
            target = origin + math.sin(seconds * 0.7 + phase) * 95
            light_draw.polygon(
                [(origin - 12, 15), (origin + 12, 15), (target + 190, 650), (target - 130, 650)],
                fill=(*self.accent, 24),
            )
        image.alpha_composite(light.filter(ImageFilter.GaussianBlur(14)))
        # Board is stationary throughout the reading window.
        reveal = ease((seconds - 0.8) / 0.65)
        if reveal > 0:
            board = self.board.copy()
            board.putalpha(board.getchannel("A").point(lambda a: round(a * reveal)))
            image.alpha_composite(board, (270, 165))
        entrance = ease(seconds / 0.85)
        for i, x in ((0, -25), (2, 965)):
            reacting = 2.4 <= seconds < duration - 0.6
            blend = ease((seconds - 2.2) / 0.25) * (1 - ease((seconds - duration + 0.8) / 0.25))
            pose = Image.blend(self.cast[i], self.cast[i + 1], blend)
            bounce = round(math.sin(seconds * (3 if i == 2 else 1.7)) * (5 if reacting else 2))
            slide = round((1 - entrance) * (360 if i == 2 else -360))
            pose = pose.rotate(math.sin(seconds * 1.4 + i) * 0.6, resample=Image.Resampling.BICUBIC)
            image.alpha_composite(pose, (x + slide, 118 + bounce))
        return image.convert("RGB")

    def frames(self, duration: int, context: JobContext) -> Iterator[bytes]:
        total = duration * 24
        for index in range(total):
            yield self.frame(index / 24, duration).tobytes()
            if index % 12 == 0 or index == total - 1:
                context.report("rendering", (index + 1) / total)
        context.report("encoding", None)
