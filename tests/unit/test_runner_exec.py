from pathlib import Path

import pytest

from media_bot.infrastructure.runner_exec import execute
from media_bot.infrastructure.runner_protocol import RunnerInput, RunnerResult


async def test_runner_exec_reads_input_and_writes_result_without_database(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "result.json"
    input_path.write_text(
        RunnerInput(
            job_id="job-id",
            lease_token="lease-token",
            plugin_id="text_card",
            plugin_version="1",
            input_json='{"text":"Тест"}',
            options_json="{}",
            workspace=str(workspace),
        ).model_dump_json(),
        encoding="utf-8",
    )

    await execute(input_path, output_path, {"text_card"})

    result = RunnerResult.model_validate_json(output_path.read_text(encoding="utf-8"))
    assert result.path == "text-card.png"
    assert result.media_type == "image/png"
    assert workspace.joinpath(result.path).is_file()


async def test_runner_exec_rejects_unavailable_plugin(tmp_path: Path) -> None:
    input_path = tmp_path / "input.json"
    input_path.write_text(
        RunnerInput(
            job_id="job-id",
            lease_token="lease-token",
            plugin_id="missing",
            plugin_version="1",
            input_json='{"text":"Тест"}',
            options_json="{}",
            workspace=str(tmp_path / "workspace"),
        ).model_dump_json(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unavailable"):
        await execute(input_path, tmp_path / "result.json", {"text_card"})
