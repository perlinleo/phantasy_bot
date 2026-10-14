from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

from media_bot.plugin_sdk.contracts import ImageResult, JobContext, PluginSpec
from media_bot.services.typography import load_font


class TextCardInput(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class TextCardOptions(BaseModel):
    background: str = "#15182b"
    foreground: str = "#f8f4e8"


def _wrap(
    text: str, draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, width: int
) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for word in paragraph.split(" "):
            proposed = word if not current else f"{current} {word}"
            if draw.textlength(proposed, font=font) <= width:
                current = proposed
            else:
                if current:
                    lines.append(current)
                current = word
        lines.append(current)
    return lines


async def run(
    input_data: TextCardInput, options: TextCardOptions, context: JobContext
) -> ImageResult:
    context.report("rendering", 0.0)
    width, height, padding = 1080, 1350, 96
    image = Image.new("RGB", (width, height), options.background)
    draw = ImageDraw.Draw(image)
    font = load_font(64)
    lines = _wrap(input_data.text, draw, font, width - padding * 2)
    line_height = 86
    total_height = len(lines) * line_height
    y = max(padding, (height - total_height) // 2)
    for line in lines:
        draw.text((padding, y), line, font=font, fill=options.foreground)
        y += line_height
    output = context.workspace / "text-card.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)
    context.report("rendering", 1.0)
    return ImageResult(path=output.name)


SPEC = PluginSpec(
    id="text_card",
    version="1",
    title="Текстовая карточка",
    description="Текст на лаконичной карточке",
    input_model=TextCardInput,
    options_model=TextCardOptions,
    run=run,
    category="images",
    tags=("текст", "картинка", "открытка"),
)
