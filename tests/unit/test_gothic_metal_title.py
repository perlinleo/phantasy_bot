from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from media_bot.plugin_sdk.contracts import JobContext
from media_bot.plugins.gothic_metal_title import plugin
from media_bot.plugins.gothic_metal_title.scene import SCENE_SCRIPT


def test_scene_template_is_valid_python_and_title_has_bounded_cost() -> None:
    compile(SCENE_SCRIPT, "scene.py", "exec")
    assert "Mirror chrome" in SCENE_SCRIPT and "CYCLES" in SCENE_SCRIPT
    for invalid in ("", " ", "x" * 31, "a\nb\nc"):
        with pytest.raises(ValueError):
            plugin.Input(text=invalid)
    assert plugin.Input(text="ХРОМ").text == "ХРОМ"


async def test_missing_blender_is_explicit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(plugin.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="requires Blender"):
        await plugin.run(plugin.Input(text="CHROME"), plugin.Options(), JobContext(tmp_path))


@pytest.mark.parametrize("blender_code,encoder_code", [(0, 0), (1, 0), (0, 1)])
async def test_plugin_processes_frames_encodes_and_cleans_scratch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, blender_code: int, encoder_code: int
) -> None:
    monkeypatch.setattr(plugin.shutil, "which", lambda name: f"/bin/{name}")
    lines = AsyncMock(side_effect=[b"Blender diagnostic\n", b"PHANTASY_FRAME 72\n", b""])
    blender = SimpleNamespace(
        stdout=SimpleNamespace(readline=lines),
        wait=AsyncMock(return_value=blender_code),
        returncode=blender_code,
    )
    encoder = SimpleNamespace(wait=AsyncMock(return_value=encoder_code), returncode=encoder_code)
    calls = []

    async def spawn(*args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            (tmp_path / "frames" / "0001.png").write_bytes(b"scratch")
            return blender
        (tmp_path / "gothic-metal-title.mp4").write_bytes(b"video")
        return encoder

    monkeypatch.setattr(plugin.asyncio, "create_subprocess_exec", spawn)
    validated = []
    monkeypatch.setattr(plugin, "validate_animation", lambda *args: validated.append(args))
    progress = []
    context = JobContext(
        tmp_path, _reporter=lambda stage, fraction: progress.append((stage, fraction))
    )
    if blender_code or encoder_code:
        with pytest.raises(RuntimeError):
            await plugin.run(plugin.Input(text="CHROME"), plugin.Options(), context)
    else:
        result = await plugin.run(plugin.Input(text="CHROME"), plugin.Options(), context)
        assert result.media_type == "video/mp4"
        assert validated and ("rendering", 72 / 192) in progress
        assert progress[-1] == ("ready", 1)
    assert not list((tmp_path / "frames").glob("*.png"))
    assert (tmp_path / "scene.py").read_text() == SCENE_SCRIPT
