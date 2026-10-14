from pathlib import Path

from media_bot.infrastructure.runner_protocol import ProgressEvent, RunnerInput, RunnerResult
from media_bot.plugin_sdk.contracts import JobContext
from media_bot.plugins.registry import enabled_plugins


async def execute(
    input_path: Path, output_path: Path, enabled: set[str], assets_root: Path | None = None
) -> None:
    payload = RunnerInput.model_validate_json(input_path.read_text(encoding="utf-8"))
    spec = enabled_plugins(enabled).get(payload.plugin_id)
    if spec is None or spec.version != payload.plugin_version:
        raise ValueError("Plugin version is unavailable")

    def report(stage: str, fraction: float | None) -> None:
        print(
            ProgressEvent(stage=stage, fraction=fraction).model_dump_json(),
            flush=True,
        )

    result = await spec.run(
        spec.input_model.model_validate_json(payload.input_json),
        spec.options_model.model_validate_json(payload.options_json),
        JobContext(
            workspace=Path(payload.workspace),
            assets_root=assets_root,
            job_id=payload.job_id,
            attempt_id=payload.lease_token,
            _reporter=report,
        ),
    )
    output_path.write_text(
        RunnerResult(path=result.path, media_type=result.media_type).model_dump_json(),
        encoding="utf-8",
    )
