import json
import math

# FFmpeg is a required local system dependency.
import subprocess  # nosec B404
import threading
from collections.abc import Iterable
from fractions import Fraction
from pathlib import Path


class FfmpegError(RuntimeError):
    pass


def validate_animation(
    output: Path, width: int, height: int, max_duration: int, *, expected_fps: int | None = None
) -> None:
    try:
        # The executable and argument list are fixed; shell execution is disabled.
        probe = subprocess.run(  # nosec
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(output)],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise FfmpegError("ffprobe validation failed") from error
    try:
        report = json.loads(probe.stdout)
        duration = float(report.get("format", {}).get("duration", 0))
    except (ValueError, TypeError) as error:
        raise FfmpegError("Invalid ffprobe response") from error
    streams = report.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if (
        video is None
        or video.get("codec_name") != "h264"
        or video.get("width") != width
        or video.get("height") != height
        or any(stream.get("codec_type") == "audio" for stream in streams)
        or not math.isfinite(duration)
        or not 0 < duration <= max_duration
    ):
        raise FfmpegError("MP4 validation failed")
    if expected_fps is not None:
        try:
            fps = Fraction(video.get("avg_frame_rate", "0"))
        except (ValueError, ZeroDivisionError) as error:
            raise FfmpegError("Invalid MP4 frame rate") from error
        if video.get("pix_fmt") != "yuv420p" or fps != expected_fps or not _faststart(output):
            raise FfmpegError("MP4 playback contract failed")


def _faststart(path: Path) -> bool:
    """Check top-level atom order without reading the video payload into memory."""
    size = path.stat().st_size
    with path.open("rb") as stream:
        while stream.tell() + 8 <= size:
            start = stream.tell()
            header = stream.read(8)
            length, kind = int.from_bytes(header[:4]), header[4:]
            if length == 1:
                length = int.from_bytes(stream.read(8))
            if length < 8 or start + length > size:
                return False
            if kind == b"moov":
                return True
            if kind == b"mdat":
                return False
            stream.seek(start + length)
    return False


def encode_rgb_frames(
    frames: Iterable[bytes], output: Path, width: int, height: int, fps: int
) -> None:
    """Encode streamed RGB frames without storing individual images on disk."""
    command = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-threads",
        "2",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    try:
        # The command is built from validated renderer values; shell execution is disabled.
        process = subprocess.Popen(  # nosec
            command, stdin=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except FileNotFoundError as error:
        raise FfmpegError("FFmpeg is not installed") from error
    tail = bytearray()

    def drain() -> None:
        assert process.stderr is not None
        while chunk := process.stderr.read(4096):
            tail.extend(chunk)
            del tail[:-8192]

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    assert process.stdin is not None
    try:
        for frame in frames:
            process.stdin.write(frame)
        process.stdin.close()
        code = process.wait(timeout=120)
        reader.join(timeout=5)
        if code != 0:
            raise FfmpegError(f"FFmpeg encoding failed: {tail.decode(errors='replace')[-500:]}")
    except (BrokenPipeError, subprocess.TimeoutExpired) as error:
        raise FfmpegError("FFmpeg stopped accepting frames or timed out") from error
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        if not process.stdin.closed:
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass  # The failed child has already been reaped.
        reader.join(timeout=5)
        if process.stderr is not None:
            process.stderr.close()
