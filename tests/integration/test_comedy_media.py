import json
import subprocess
from pathlib import Path

from media_bot.plugin_sdk.contracts import JobContext
from media_bot.plugins.comedy_stage.plugin import Input, Options, run


async def test_comedy_encodes_real_six_second_silent_mp4(
    tmp_path: Path, character_pack: Path
) -> None:
    context = JobContext(workspace=tmp_path / "movie", assets_root=character_pack)
    result = await run(Input(text="Привет, Ёж!"), Options(), context)
    path = context.workspace / result.path
    assert result.kind == "animation" and result.media_type == "video/mp4"
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(probe.stdout)
    assert len(report["streams"]) == 1
    stream = report["streams"][0]
    assert (stream["codec_name"], stream["width"], stream["height"], stream["pix_fmt"]) == (
        "h264",
        1280,
        720,
        "yuv420p",
    )
    assert stream["nb_frames"] == "144"
    assert 5.9 < float(report["format"]["duration"]) < 6.1
