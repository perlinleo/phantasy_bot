import json

from media_bot.adapters.telegram.presets import PRESETS, confirmation
from media_bot.plugins.registry import enabled_plugins


def test_every_ui_preset_validates_and_callback_fits() -> None:
    plugins = enabled_plugins(set(PRESETS))
    for plugin_id, presets in PRESETS.items():
        for key, (_, updates) in presets.items():
            options = plugins[plugin_id].options_model().model_dump() | updates
            plugins[plugin_id].options_model.model_validate(options)
            assert len(f"preset:{'a' * 36}:999:{key}".encode()) <= 64


def test_confirmation_escapes_text_and_describes_actual_result() -> None:
    text, keyboard = confirmation(
        "comedy_stage",
        "<Title>",
        "video",
        "id",
        3,
        '<script>&"',
        json.dumps({"preset": "classic_red", "duration_seconds": 8}),
    )
    assert "&lt;script&gt;&amp;" in text and "&lt;Title&gt;" in text
    assert "Красная сцена · 8 с" in text and "MP4 без звука" in text
    assert keyboard.inline_keyboard[0][0].callback_data == "create:id:3"
    text, _ = confirmation("other", "Other", "images", "id", 0, "x" * 301, "{}")
    assert "сокращён" in text and "PNG" in text
