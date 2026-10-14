import math

from PIL import Image, ImageDraw
from pydantic import BaseModel, Field

from media_bot.plugin_sdk.contracts import ImageResult, JobContext, PluginSpec
from media_bot.services.typography import load_font


class TextToEmojiInput(BaseModel):
    text: str = Field(min_length=1, max_length=80)


class TextToEmojiOptions(BaseModel):
    foreground: str = "#ffffff"
    background: str = "#2a72e5"


async def run(
    input_data: TextToEmojiInput, options: TextToEmojiOptions, context: JobContext
) -> ImageResult:
    tile_size, padding = 100, 20
    font = load_font(72)
    probe = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), input_data.text, font=font)
    width = max(tile_size, bbox[2] - bbox[0] + padding * 2)
    columns = math.ceil(width / tile_size)
    canvas = Image.new("RGBA", (columns * tile_size, tile_size), options.background)
    draw = ImageDraw.Draw(canvas)
    text_width = draw.textlength(input_data.text, font=font)
    draw.text(
        ((canvas.width - text_width) / 2, (tile_size - 72) / 2 - bbox[1]),
        input_data.text,
        font=font,
        fill=options.foreground,
    )
    context.workspace.mkdir(parents=True, exist_ok=True)
    for column in range(columns):
        canvas.crop((column * tile_size, 0, (column + 1) * tile_size, tile_size)).save(
            context.workspace / f"tile-{column:03d}.png", format="PNG"
        )
    preview = context.workspace / "emoji-preview.png"
    canvas.save(preview, format="PNG")
    return ImageResult(path=preview.name)


SPEC = PluginSpec(
    id="text_to_emoji",
    version="1",
    title="Текст в emoji",
    description="Текстовая полоса из квадратных emoji-плиток",
    input_model=TextToEmojiInput,
    options_model=TextToEmojiOptions,
    run=run,
    category="emoji",
    tags=("текст", "emoji", "эмодзи", "плитки"),
)
