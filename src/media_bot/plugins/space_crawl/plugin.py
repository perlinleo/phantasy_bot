import random
from collections.abc import Iterator

from PIL import Image, ImageDraw
from pydantic import BaseModel, Field

from media_bot.plugin_sdk.contracts import ImageResult, JobContext, PluginSpec
from media_bot.services.ffmpeg import encode_rgb_frames, validate_animation
from media_bot.services.typography import load_font


class SpaceCrawlInput(BaseModel):
    text: str = Field(min_length=1, max_length=1500)


class SpaceCrawlOptions(BaseModel):
    duration_seconds: int = Field(default=8, ge=3, le=45)
    fps: int = Field(default=24, ge=12, le=24)


async def run(
    input_data: SpaceCrawlInput, options: SpaceCrawlOptions, context: JobContext
) -> ImageResult:
    width, height = 1280, 720
    # Deterministic star field; this is not security material.
    rng = random.Random(1)  # nosec B311
    stars = [(rng.randrange(width), rng.randrange(height), rng.randrange(1, 3)) for _ in range(300)]
    lines = input_data.text.splitlines() or [input_data.text]

    def frames() -> Iterator[bytes]:
        for frame_number in range(options.duration_seconds * options.fps):
            image = Image.new("RGB", (width, height), "#02030a")
            draw = ImageDraw.Draw(image)
            for x, y, radius in stars:
                draw.ellipse((x, y, x + radius, y + radius), fill="#c7d5ff")
            offset = (
                height
                + 80
                - frame_number
                * (height + len(lines) * 64 + 200)
                / (options.duration_seconds * options.fps)
            )
            for index, line in enumerate(lines):
                scale = max(0.35, min(1.0, 1.0 - (offset + index * 64) / (height * 1.5)))
                line_font = load_font(max(16, int(42 * scale)))
                text_width = draw.textlength(line, font=line_font)
                draw.text(
                    ((width - text_width) / 2, offset + index * 64),
                    line,
                    font=line_font,
                    fill="#ffe81f",
                )
            yield image.tobytes()

    output = context.workspace / "space-crawl.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    encode_rgb_frames(frames(), output, width, height, options.fps)
    validate_animation(output, width, height, options.duration_seconds + 1)
    return ImageResult(kind="animation", path=output.name, media_type="video/mp4")


SPEC = PluginSpec(
    id="space_crawl",
    version="1",
    title="Космический crawl",
    description="Жёлтый текст среди звёзд",
    input_model=SpaceCrawlInput,
    options_model=SpaceCrawlOptions,
    run=run,
    category="video",
    tags=("текст", "видео", "титры", "космос"),
)
