from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from media_bot.plugin_sdk.contracts import ImageResult, JobContext, PluginSpec
from media_bot.plugins.glamour_letters.renderer import render
from media_bot.services.character_assets import asset_spec, load_characters
from media_bot.services.stage_text import letter_rows


class Input(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    text: str = Field(min_length=1, max_length=24)

    @field_validator("text")
    @classmethod
    def readable(cls, value: str) -> str:
        letter_rows(value)
        return value


class Options(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    preset: Literal["gold_lounge", "diamond_night", "red_carpet"] = "gold_lounge"


async def run(input_data: Input, options: Options, context: JobContext) -> ImageResult:
    context.report("rendering", 0)
    characters = load_characters("glamour_letters", context.assets_root)
    image = render(input_data.text, options.preset, characters, asset_spec("glamour_letters").grips)
    context.workspace.mkdir(parents=True, exist_ok=True)
    output = context.workspace / "glamour-letters.png"
    image.convert("RGB").save(output, format="PNG", optimize=True)
    if output.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Постер превышает лимит 10 MiB.")
    context.report("rendering", 1)
    return ImageResult(path=output.name)


SPEC = PluginSpec(
    id="glamour_letters",
    version="1",
    title="Крутые тёлки",
    description="Роскошные модели держат ваши буквы. PNG-постер, до 12 знаков, три стиля.",
    input_model=Input,
    options_model=Options,
    run=run,
    category="images",
    tags=("модели", "гламур", "буквы", "тёлки", "телки", "золото"),
)
