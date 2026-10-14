from pathlib import Path

import pytest

from media_bot.services import character_assets as assets


def test_pinned_manifest_is_packaged() -> None:
    for plugin in assets.CHARACTER_PLUGINS:
        spec = assets.asset_spec(plugin)
        assert len(spec.cells) == 4 and spec.width > 0


def test_asset_validation_checks_integrity_and_disabled_plugins(character_pack: Path) -> None:
    assets.validate_character_assets({"text_card"}, None)
    assets.validate_character_assets(assets.CHARACTER_PLUGINS, character_pack)
    with pytest.raises(ValueError, match="PLUGIN_ASSETS_DIR"):
        assets.load_characters("glamour_letters", None)
    with pytest.raises(ValueError, match="Отсутствует"):
        assets.load_characters("glamour_letters", character_pack / "missing")
    path = character_pack / "cast.png"
    path.write_bytes(path.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="версия"):
        assets.load_characters("glamour_letters", character_pack)


def test_symlinks_and_traversal_cannot_escape_pack(
    character_pack: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = assets.asset_spec("glamour_letters")
    (character_pack / "link.png").symlink_to(character_pack / "cast.png")
    for filename in ("link.png", "../outside.png"):
        monkeypatch.setattr(
            assets,
            "asset_spec",
            lambda _, filename=filename: spec.model_copy(update={"filename": filename}),
        )
        with pytest.raises(ValueError, match="inside"):
            assets.load_characters("glamour_letters", character_pack)


def test_wrong_dimensions_and_crop_rejected(
    character_pack: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = assets.asset_spec("glamour_letters")
    monkeypatch.setattr(assets, "asset_spec", lambda _: spec.model_copy(update={"width": 2}))
    with pytest.raises(ValueError, match="размер"):
        assets.load_characters("glamour_letters", character_pack)
    monkeypatch.setattr(
        assets, "asset_spec", lambda _: spec.model_copy(update={"cells": [(0, 0, 999, 2)] * 4})
    )
    with pytest.raises(ValueError, match="bounds"):
        assets.load_characters("glamour_letters", character_pack)
