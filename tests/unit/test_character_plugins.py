from pathlib import Path

import pytest
from PIL import Image, ImageChops
from pydantic import ValidationError

from media_bot.plugin_sdk.contracts import JobContext
from media_bot.plugins.comedy_stage import plugin as comedy
from media_bot.plugins.comedy_stage.renderer import Stage
from media_bot.plugins.glamour_letters import plugin as glamour
from media_bot.plugins.glamour_letters.renderer import metallic_letter
from media_bot.plugins.registry import enabled_plugins, search_plugins
from media_bot.services.character_assets import load_characters
from media_bot.services.stage_text import display_text, fit_stage_text, letter_rows


@pytest.mark.parametrize("value", ["", "  ", "\n", "😀", "a\tB", "a\x00", "e\u0301", "中"])
def test_invalid_text_rejected_before_render(value: str) -> None:
    for model in (glamour.Input, comedy.Input):
        with pytest.raises(ValidationError):
            model(text=value)


def test_text_limits_and_cyrillic_layout_preserve_input() -> None:
    original = "Е\u0308ж WOW!"
    assert glamour.Input(text=original).text == original
    assert display_text(original) == "Ёж WOW!"
    assert letter_rows("АБВГДЕЖЗИЙКЛ") == ["АБВГДЕ", "ЖЗИЙКЛ"]
    assert "".join(letter_rows("AB CD EFG")) == "AB CD EFG"
    for value in ("A" * 13, "A\nB\nC", "A\n\nB"):
        with pytest.raises(ValidationError):
            glamour.Input(text=value)
    for value in ("Ш" * 100, "a\nb\nc\nd"):
        with pytest.raises(ValidationError):
            comedy.Input(text=value)
    text = "Очень длинное словоСОченьДлиннымПродолжением и ещё буквы"
    lines, font = fit_stage_text(text)
    assert "".join(lines) == text
    assert len(lines) <= 3 and all(font.getlength(line) <= 650 for line in lines)
    assert font.size >= 44


def test_presets_are_bounded_and_registry_searchable() -> None:
    for model, options in (
        (glamour.Options, {"preset": "unknown"}),
        (comedy.Options, {"duration_seconds": 7}),
        (comedy.Options, {"fps": 240}),
    ):
        with pytest.raises(ValidationError):
            model.model_validate(options)
    ids = {"glamour_letters", "comedy_stage"}
    assert set(enabled_plugins(ids)) == ids
    assert search_plugins(ids, "харламов")[0].id == "comedy_stage"
    assert search_plugins(ids, "телки")[0].id == "glamour_letters"


@pytest.mark.parametrize(
    "preset,text",
    [
        ("gold_lounge", "ВАУ"),
        ("diamond_night", "ЁЖ WOW!"),
        ("red_carpet", "АБВГДЕЖЗИЙКЛ"),
    ],
)
async def test_glamour_real_png(
    tmp_path: Path, character_pack: Path, preset: str, text: str
) -> None:
    events: list[tuple[str, float | None]] = []
    context = JobContext(
        workspace=tmp_path / preset,
        assets_root=character_pack,
        _reporter=lambda stage, fraction: events.append((stage, fraction)),
    )
    result = await glamour.run(glamour.Input(text=text), glamour.Options(preset=preset), context)
    assert not Path(result.path).is_absolute()
    with Image.open(context.workspace / result.path) as image:
        assert image.size == (1600, 1000) and image.mode == "RGB"
        assert image.getextrema()[0][0] < image.getextrema()[0][1]
    assert events == [("rendering", 0), ("rendering", 1)]
    assert metallic_letter("W", 60, (200, 150, 90)).getbbox() is not None


def test_comedy_text_remains_stationary_during_reading(character_pack: Path) -> None:
    cast = load_characters("comedy_stage", character_pack)
    for preset in ("classic_red", "neon_roast"):
        stage = Stage("Ёж пришёл на шоу!", preset, cast)
        middle = stage.frame(2, 8)
        later = stage.frame(6, 8)
        assert (
            ImageChops.difference(
                middle.crop((330, 180, 950, 440)), later.crop((330, 180, 950, 440))
            ).getbbox()
            is None
        )
        assert ImageChops.difference(stage.frame(0, 8), middle).getbbox() is not None
        assert ImageChops.difference(middle, later).getbbox() is not None
        events: list[float | None] = []
        frames = stage.frames(
            1,
            JobContext(
                workspace=character_pack,
                _reporter=lambda _, fraction, events=events: events.append(fraction),
            ),
        )
        assert sum(1 for frame in frames if len(frame) == 1280 * 720 * 3) == 24
        assert events[-2:] == [1, None]
