import pytest

from media_bot.infrastructure.runner_protocol import RunnerResult
from media_bot.plugin_sdk.contracts import JobContext


def test_runner_result_rejects_path_escape() -> None:
    assert RunnerResult(path="result.png", media_type="image/png").path == "result.png"
    with pytest.raises(ValueError, match="relative"):
        RunnerResult(path="../outside.png", media_type="image/png")


def test_job_context_rejects_invalid_progress_fraction(tmp_path) -> None:
    with pytest.raises(ValueError, match="fraction"):
        JobContext(workspace=tmp_path).report("rendering", 1.1)
