import json

# FFmpeg is a required local system dependency.
import subprocess  # nosec B404
from collections.abc import Iterable
from pathlib import Path


class FfmpegError(RuntimeError):
    pass


def validate_animation(output: Path, width: int, height: int, max_duration: int) -> None:
    try:
        # The executable and argument list are fixed; shell execution is disabled.
        probe = subprocess.run(  # nosec
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(output)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise FfmpegError("ffprobe validation failed") from error
    report = json.loads(probe.stdout)
    streams = report.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if (
        video is None
        or video.get("codec_name") != "h264"
        or video.get("width") != width
        or video.get("height") != height
        or any(stream.get("codec_type") == "audio" for stream in streams)
        or float(report.get("format", {}).get("duration", 0)) > max_duration
    ):
        raise FfmpegError("MP4 validation failed")


def encode_rgb_frames(
    frames: Iterable[bytes], output: Path, width: int, height: int, fps: int
) -> None:
    """Encode streamed RGB frames without storing individual images on disk."""
    command = [
        "ffmpeg",
        "-y",
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
    assert process.stdin is not None
    for frame in frames:
        process.stdin.write(frame)
    process.stdin.close()
    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    if process.wait() != 0:
        raise FfmpegError(f"FFmpeg encoding failed: {stderr[-500:]}")
