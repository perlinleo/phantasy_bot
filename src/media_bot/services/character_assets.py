"""Load pinned, operator-installed artwork without network or user-selected paths."""

import hashlib
import json
from importlib.resources import files
from pathlib import Path

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

CHARACTER_PLUGINS = {"glamour_letters", "comedy_stage"}


class AtlasSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    width: int = Field(gt=0, le=4096)
    height: int = Field(gt=0, le=4096)
    cells: list[tuple[int, int, int, int]] = Field(min_length=4, max_length=4)
    # Normalized palm center/baseline within each glamour character crop.
    grips: list[tuple[float, float]] = Field(
        default_factory=lambda: [(0.5, 0.385)] * 4, min_length=4, max_length=4
    )


def asset_spec(plugin_id: str) -> AtlasSpec:
    manifest = files("media_bot.assets").joinpath("characters-v1.json")
    return AtlasSpec.model_validate(json.loads(manifest.read_text())[plugin_id])


def load_characters(plugin_id: str, root: Path | None) -> list[Image.Image]:
    if root is None:
        raise ValueError("Укажите PLUGIN_ASSETS_DIR с пакетом characters-v1.")
    spec = asset_spec(plugin_id)
    base = root.resolve()
    candidate = base / spec.filename
    if candidate.is_symlink() or not candidate.resolve().is_relative_to(base):
        raise ValueError("Character resource must be inside the asset directory")
    if not candidate.is_file() or candidate.stat().st_size > 32 * 1024 * 1024:
        raise ValueError(f"Отсутствует или слишком велик ресурс: {spec.filename}")
    with candidate.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != spec.sha256:
            raise ValueError(f"Неверная версия ресурса: {spec.filename}")
    with Image.open(candidate) as atlas:
        if atlas.size != (spec.width, spec.height) or atlas.mode != "RGBA":
            raise ValueError(f"Неверный размер или alpha-канал: {spec.filename}")
        atlas.load()
        result: list[Image.Image] = []
        for x0, y0, x1, y1 in spec.cells:
            if not (0 <= x0 < x1 <= atlas.width and 0 <= y0 < y1 <= atlas.height):
                raise ValueError("Invalid character bounds")
            result.append(atlas.crop((x0, y0, x1, y1)))
        return result


def validate_character_assets(enabled: set[str], root: Path | None) -> None:
    for plugin_id in sorted(enabled & CHARACTER_PLUGINS):
        for character in load_characters(plugin_id, root):
            character.close()
