import asyncio
import json
import os
import sys
from pathlib import Path

from media_bot.infrastructure.runner_protocol import RunnerInput, RunnerResult


async def test_runner_subprocess_uses_json_files_and_emits_bounded_progress(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "result.json"
    input_path.write_text(
        RunnerInput(
            job_id="job-id",
            lease_token="lease-token",
            plugin_id="text_card",
            plugin_version="1",
            input_json='{"text":"subprocess"}',
            options_json="{}",
            workspace=str(workspace),
        ).model_dump_json(),
        encoding="utf-8",
    )
    environment = {"PATH": os.environ["PATH"], "PYTHONPATH": os.environ.get("PYTHONPATH", "")}
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "media_bot",
        "run-payload",
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--plugins",
        "text_card",
        env=environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    assert process.returncode == 0, stderr.decode()
    events = [json.loads(line) for line in stdout.splitlines()]
    assert events == [
        {"type": "progress", "stage": "rendering", "fraction": 0.0},
        {"type": "progress", "stage": "rendering", "fraction": 1.0},
    ]
    result = RunnerResult.model_validate_json(output_path.read_text(encoding="utf-8"))
    assert workspace.joinpath(result.path).is_file()
