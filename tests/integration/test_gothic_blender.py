import asyncio
import json
import shutil
from pathlib import Path

import pytest
from PIL import Image

from media_bot.plugins.gothic_metal_title.scene import SCENE_SCRIPT


@pytest.mark.skipif(shutil.which("blender") is None, reason="Blender is not installed")
async def test_real_blender_scene_renders_one_chrome_frame(tmp_path: Path) -> None:
    script = tmp_path / "scene.py"
    script.write_text(SCENE_SCRIPT, encoding="utf-8")
    config = tmp_path / "scene.json"
    config.write_text(
        json.dumps(
            {
                "text": "CHROME",
                "workspace": str(tmp_path),
                "duration_seconds": 1,
                "fps": 1,
                "samples": 8,
                "font": str(Path("assets/fonts/UnifrakturCook-Bold.ttf").resolve()),
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "frames").mkdir()
    process = await asyncio.create_subprocess_exec(
        shutil.which("blender") or "blender",
        "--background",
        "--factory-startup",
        "--python-exit-code",
        "1",
        "--python",
        str(script),
        "--",
        str(config),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), 240)
        assert process.returncode == 0, output.decode(errors="replace")[-4000:]
        with Image.open(tmp_path / "frames" / "0001.png") as frame:
            assert frame.size == (1280, 720)
            assert frame.convert("RGB").getextrema() != ((0, 0),) * 3
        assert (tmp_path / "scene.blend").is_file()
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
