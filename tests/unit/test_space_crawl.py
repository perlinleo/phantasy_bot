from pathlib import Path

import pytest

from media_bot.plugin_sdk.contracts import JobContext
from media_bot.plugins.space_crawl import plugin


async def test_space_crawl_streams_a_720p_animation_to_encoder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    def encoder(frames: object, output: Path, width: int, height: int, fps: int) -> None:
        captured["frame"] = next(iter(frames))
        captured["output"] = output
        captured["size"] = (width, height, fps)

    monkeypatch.setattr(plugin, "encode_rgb_frames", encoder)
    monkeypatch.setattr(plugin, "validate_animation", lambda *_: None)
    result = await plugin.run(
        plugin.SpaceCrawlInput(text="Привет\nмир"),
        plugin.SpaceCrawlOptions(duration_seconds=3, fps=12),
        JobContext(workspace=tmp_path),
    )

    assert result.kind == "animation"
    assert result.path == "space-crawl.mp4"
    assert captured["output"] == tmp_path / "space-crawl.mp4"
    assert captured["size"] == (1280, 720, 12)
    assert len(captured["frame"]) == 1280 * 720 * 3  # type: ignore[arg-type]
