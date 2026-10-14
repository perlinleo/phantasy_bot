import subprocess
import sys
from pathlib import Path

import pytest

from media_bot.services import ffmpeg


def test_encoder_drains_more_than_pipe_capacity_without_deadlock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_popen = subprocess.Popen
    children: list[subprocess.Popen[bytes]] = []

    def noisy_encoder(*_: object, **kwargs: object) -> subprocess.Popen[bytes]:
        process = real_popen(
            [
                sys.executable,
                "-c",
                "import sys; sys.stderr.buffer.write(b'x'*2000000); "
                "sys.stderr.flush(); sys.stdin.buffer.read(); sys.exit(2)",
            ],
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        children.append(process)
        return process

    monkeypatch.setattr(ffmpeg.subprocess, "Popen", noisy_encoder)
    with pytest.raises(ffmpeg.FfmpegError) as error:
        ffmpeg.encode_rgb_frames([b"frame"], tmp_path / "out.mp4", 2, 2, 1)
    assert len(str(error.value)) < 600
    assert children[0].poll() == 2


def test_real_encoder_is_reaped_when_renderer_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_popen = subprocess.Popen
    children: list[subprocess.Popen[bytes]] = []

    def recording(*args: object, **kwargs: object):
        process = real_popen(*args, **kwargs)
        children.append(process)
        return process

    monkeypatch.setattr(ffmpeg.subprocess, "Popen", recording)

    def frames():
        yield b"\x00" * (32 * 32 * 3)
        raise RuntimeError("cancel rendering")

    with pytest.raises(RuntimeError, match="cancel rendering"):
        ffmpeg.encode_rgb_frames(frames(), tmp_path / "out.mp4", 32, 32, 24)
    assert children[0].poll() is not None
