from pathlib import Path

from PIL import Image

from media_bot.plugin_sdk.contracts import JobContext
from media_bot.plugins.text_to_emoji.plugin import TextToEmojiInput, TextToEmojiOptions, run


async def test_text_to_emoji_creates_preview_and_100px_tiles(tmp_path: Path) -> None:
    result = await run(
        TextToEmojiInput(text="Привет!"), TextToEmojiOptions(), JobContext(workspace=tmp_path)
    )

    preview = Image.open(tmp_path / result.path)
    tiles = sorted(tmp_path.glob("tile-*.png"))
    assert preview.height == 100
    assert preview.width == len(tiles) * 100
    assert tiles
    assert all(Image.open(tile).size == (100, 100) for tile in tiles)
