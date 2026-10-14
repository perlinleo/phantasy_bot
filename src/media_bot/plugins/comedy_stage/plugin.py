from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from media_bot.plugin_sdk.contracts import ImageResult, JobContext, PluginSpec
from media_bot.plugins.comedy_stage.renderer import Stage
from media_bot.services.character_assets import load_characters
from media_bot.services.ffmpeg import encode_rgb_frames, validate_animation
from media_bot.services.stage_text import fit_stage_text


class Input(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    text: str = Field(min_length=1, max_length=100)

    @field_validator("text")
    @classmethod
    def readable(cls, value: str) -> str:
        fit_stage_text(value)
        return value


class Options(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    preset: Literal["classic_red", "neon_roast"] = "classic_red"
    duration_seconds: Literal[6, 8] = 6


async def run(input_data: Input, options: Options, context: JobContext) -> ImageResult:
    context.report("rendering", 0)
    stage = Stage(
        input_data.text, options.preset, load_characters("comedy_stage", context.assets_root)
    )
    context.workspace.mkdir(parents=True, exist_ok=True)
    output = context.workspace / "comedy-stage.mp4"
    encode_rgb_frames(stage.frames(options.duration_seconds, context), output, 1280, 720, 24)
    context.report("validating", None)
    validate_animation(output, 1280, 720, options.duration_seconds + 1, expected_fps=24)
    if output.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("Ролик превышает лимит 20 MiB.")
    context.report("ready", 1)
    return ImageResult(kind="animation", path=output.name, media_type="video/mp4")


SPEC = PluginSpec(
    id="comedy_stage",
    version="1",
    title="Камеди: Воля и Харламов",
    description="Пародийная сцена с Волей и Харламовым и вашей надписью. MP4 без звука, 6–8 с.",
    input_model=Input,
    options_model=Options,
    run=run,
    category="video",
    tags=("камеди", "comedy", "воля", "харламов", "шоу", "юмор"),
)
