from pathlib import Path

import pytest
from PIL import Image
from pytest import mark

from media_bot.plugin_sdk.contracts import JobContext
from media_bot.plugins.text_card.plugin import TextCardInput, TextCardOptions, _wrap, run
from media_bot.services.typography import load_font


@mark.asyncio
async def test_text_card_renders_png(tmp_path: Path) -> None:
    result = await run(
        TextCardInput(text="Привет, ёлка!"), TextCardOptions(), JobContext(workspace=tmp_path)
    )
    image = Image.open(tmp_path / result.path)
    assert image.format == "PNG"
    assert image.size == (1080, 1350)


def test_wrap_preserves_empty_paragraphs_and_long_words() -> None:
    from PIL import Image, ImageDraw

    font = load_font(20)
    draw = ImageDraw.Draw(Image.new("RGB", (100, 100)))
    assert _wrap("one\n\nword", draw, font, 300) == ["one", "", "word"]
    assert _wrap("verylongword", draw, font, 1) == ["verylongword"]


def test_font_loader_explains_missing_font(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("media_bot.services.typography.Path.exists", lambda _: False)
    with pytest.raises(RuntimeError, match="DejaVu Sans"):
        load_font(12)
