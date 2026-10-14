from pydantic import BaseModel, Field

from media_bot.plugin_sdk.contracts import ImageResult, JobContext, PluginSpec
from media_bot.plugins.emoji_styles import render_tiles


class Input(BaseModel):
    text: str = Field(min_length=1, max_length=40)


class Options(BaseModel):
    pass


async def run(input_data: Input, _: Options, context: JobContext) -> ImageResult:
    preview = render_tiles(input_data.text, context.workspace, "ghost")
    return ImageResult(path=preview.name)


SPEC = PluginSpec(
    id="ghost_emoji",
    version="1",
    title="Призрачные буквы",
    description="Светящиеся хэллоуинские буквы-привидения на прозрачном фоне",
    input_model=Input,
    options_model=Options,
    run=run,
    category="emoji",
    tags=("призрак", "хэллоуин", "ghost", "emoji"),
)
