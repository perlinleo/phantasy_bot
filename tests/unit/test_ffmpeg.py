from pathlib import Path
from types import SimpleNamespace

import pytest

from media_bot.services import ffmpeg


class ProcessStub:
    def __init__(self, code: int = 0, stderr: bytes = b"") -> None:
        self.stdin = SimpleNamespace(written=[], closed=False)
        self.stdin.write = self.stdin.written.append
        self.stdin.close = lambda: setattr(self.stdin, "closed", True)
        self.stderr = SimpleNamespace(read=lambda: stderr)
        self._code = code

    def wait(self) -> int:
        return self._code


def test_encoder_streams_frames_to_ffmpeg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    process = ProcessStub()
    captured: dict[str, object] = {}

    def popen(command: list[str], **kwargs: object) -> ProcessStub:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return process

    monkeypatch.setattr(ffmpeg.subprocess, "Popen", popen)
    ffmpeg.encode_rgb_frames([b"frame-1", b"frame-2"], tmp_path / "out.mp4", 10, 20, 24)

    assert process.stdin.written == [b"frame-1", b"frame-2"]
    assert process.stdin.closed
    assert captured["command"][-1] == str(tmp_path / "out.mp4")


def test_encoder_reports_missing_or_failed_ffmpeg(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        ffmpeg.subprocess, "Popen", lambda *_, **__: (_ for _ in ()).throw(FileNotFoundError())
    )
    with pytest.raises(ffmpeg.FfmpegError, match="not installed"):
        ffmpeg.encode_rgb_frames([], tmp_path / "out.mp4", 1, 1, 1)

    monkeypatch.setattr(
        ffmpeg.subprocess, "Popen", lambda *_, **__: ProcessStub(code=1, stderr=b"bad encode")
    )
    with pytest.raises(ffmpeg.FfmpegError, match="bad encode"):
        ffmpeg.encode_rgb_frames([], tmp_path / "out.mp4", 1, 1, 1)


def test_animation_validator_checks_media_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    good = (
        '{"streams":[{"codec_type":"video","codec_name":"h264","width":10,"height":20}],'
        '"format":{"duration":"3"}}'
    )
    monkeypatch.setattr(ffmpeg.subprocess, "run", lambda *_, **__: SimpleNamespace(stdout=good))
    ffmpeg.validate_animation(tmp_path / "out.mp4", 10, 20, 5)

    bad = '{"streams":[{"codec_type":"audio"}],"format":{"duration":"3"}}'
    monkeypatch.setattr(ffmpeg.subprocess, "run", lambda *_, **__: SimpleNamespace(stdout=bad))
    with pytest.raises(ffmpeg.FfmpegError, match="MP4 validation"):
        ffmpeg.validate_animation(tmp_path / "out.mp4", 10, 20, 5)
