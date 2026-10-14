from pathlib import Path

import pytest
from PIL import Image

from media_bot.plugin_sdk.contracts import JobContext
from media_bot.plugins.blood_gothic_emoji.plugin import (
    Input as BloodInput,
)
from media_bot.plugins.blood_gothic_emoji.plugin import (
    Options as BloodOptions,
)
from media_bot.plugins.blood_gothic_emoji.plugin import (
    run as blood,
)
from media_bot.plugins.ghost_emoji.plugin import (
    Input as GhostInput,
)
from media_bot.plugins.ghost_emoji.plugin import (
    Options as GhostOptions,
)
from media_bot.plugins.ghost_emoji.plugin import (
    run as ghost,
)
from media_bot.plugins.iron_gothic_emoji.plugin import (
    Input as IronInput,
)
from media_bot.plugins.iron_gothic_emoji.plugin import (
    Options as IronOptions,
)
from media_bot.plugins.iron_gothic_emoji.plugin import (
    run as iron,
)


@pytest.mark.parametrize(
    ("runner", "input_data", "options"),
    [
        (blood, BloodInput(text="BOO"), BloodOptions()),
        (ghost, GhostInput(text="BOO"), GhostOptions()),
        (iron, IronInput(text="BOO"), IronOptions()),
    ],
)
async def test_halloween_emoji_plugins_render_transparent_tiles(
    tmp_path: Path, runner: object, input_data: object, options: object
) -> None:
    result = await runner(input_data, options, JobContext(workspace=tmp_path))  # type: ignore[operator]
    image = Image.open(tmp_path / result.path)
    assert image.mode == "RGBA"
    assert list(tmp_path.glob("tile-*.png"))
