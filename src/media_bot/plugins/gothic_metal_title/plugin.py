import asyncio
import json
import shutil
from importlib.resources import files

from pydantic import BaseModel, Field, field_validator

from media_bot.plugin_sdk.contracts import ImageResult, JobContext, PluginSpec
from media_bot.plugins.gothic_metal_title.scene import SCENE_SCRIPT
from media_bot.services.ffmpeg import validate_animation


class Input(BaseModel):
    text: str = Field(min_length=1, max_length=30)

    @field_validator("text")
    @classmethod
    def readable_title(cls, value: str) -> str:
        if not value.strip() or len(value.splitlines()) > 2:
            raise ValueError("Use one or two non-empty title lines")
        return value


class Options(BaseModel):
    duration_seconds: int = Field(default=8, ge=3, le=12)
    fps: int = Field(default=24, ge=12, le=24)
    samples: int = Field(default=24, ge=8, le=64)


async def run(input_data: Input, options: Options, context: JobContext) -> ImageResult:
    blender = shutil.which("blender")
    ffmpeg = shutil.which("ffmpeg")
    if blender is None or ffmpeg is None:
        raise RuntimeError("This plugin requires Blender 4.2+ and FFmpeg installed locally")
    workspace = context.workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    frames = workspace / "frames"
    frames.mkdir(exist_ok=True)
    script = workspace / "scene.py"
    script.write_text(SCENE_SCRIPT, encoding="utf-8")
    configuration = workspace / "scene.json"
    configuration.write_text(
        json.dumps(
            {
                "text": input_data.text,
                **options.model_dump(),
                "workspace": str(workspace),
                "font": str(files("media_bot").joinpath("assets/fonts/UnifrakturCook-Bold.ttf")),
            }
        ),
        encoding="utf-8",
    )
    context.report("building_scene", 0)
    total = options.duration_seconds * options.fps
    process = await asyncio.create_subprocess_exec(
        blender,
        "--background",
        "--factory-startup",
        "--python-exit-code",
        "1",
        "--python",
        str(script),
        "--",
        str(configuration),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        assert process.stdout is not None
        while line := await process.stdout.readline():
            if line.startswith(b"PHANTASY_FRAME "):
                context.report("rendering", int(line.split()[1]) / total)
        if await process.wait() != 0:
            raise RuntimeError("Blender render failed; check local Blender compatibility")
        context.report("encoding", None)
        output = workspace / "gothic-metal-title.mp4"
        encoder = await asyncio.create_subprocess_exec(
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-framerate",
            str(options.fps),
            "-i",
            str(frames / "%04d.png"),
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            if await encoder.wait() != 0:
                raise RuntimeError("Gothic title video encoding failed")
        finally:
            if encoder.returncode is None:
                encoder.kill()
                await encoder.wait()
        validate_animation(output, 1280, 720, options.duration_seconds + 1)
        context.report("ready", 1)
        return ImageResult(kind="animation", path=output.name, media_type="video/mp4")
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
        # Only plugin-created scratch frames are removed; keep the scene for diagnostics.
        for frame in frames.glob("*.png"):
            frame.unlink()


SPEC = PluginSpec(
    id="gothic_metal_title",
    version="1",
    title="Грозовой хром",
    description="Объёмная готическая надпись: зеркальный хром, кровь, дождь, туман и молнии. MP4.",
    input_model=Input,
    options_model=Options,
    run=run,
    category="video",
    tags=("готика", "хром", "3d", "гроза", "видео"),
)
