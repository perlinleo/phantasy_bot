import hashlib
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from media_bot.services import character_assets


@pytest.fixture
def character_pack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Synthetic atlas exercises alpha/layout without shipping generated artwork in Git."""
    root = tmp_path / "assets"
    root.mkdir()
    atlas = Image.new("RGBA", (400, 240))
    draw = ImageDraw.Draw(atlas)
    for i, color in enumerate(("red", "blue", "green", "orange")):
        x = i * 100
        draw.ellipse((x + 35, 5, x + 65, 35), fill="wheat")
        draw.rectangle((x + 20, 38, x + 80, 225), fill=color)
    path = root / "cast.png"
    atlas.save(path)
    spec = character_assets.AtlasSpec(
        filename="cast.png",
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        width=400,
        height=240,
        cells=[(i * 100, 0, (i + 1) * 100, 240) for i in range(4)],
    )
    monkeypatch.setattr(character_assets, "asset_spec", lambda _: spec)
    return root
