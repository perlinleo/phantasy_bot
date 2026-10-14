import asyncio
import json
from pathlib import Path

from media_bot.application.access import AccessService
from media_bot.application.jobs import JobService
from media_bot.infrastructure.db import create_schema, make_engine, make_session_factory
from media_bot.infrastructure.runner_exec import execute
from media_bot.infrastructure.runner_protocol import RunnerInput, RunnerResult


async def test_character_options_survive_restart_and_only_one_revision_wins(
    tmp_path: Path, character_pack: Path
) -> None:
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite3'}")
    await create_schema(engine)
    sessions = make_session_factory(engine)
    await AccessService(sessions, owner_id=1).decision_for(1)
    service = JobService(sessions, {"glamour_letters", "comedy_stage"})
    draft = await service.new_draft(1, 1, "glamour_letters")
    saved = await service.save_text(1, "ЁЖ")
    assert saved is not None
    assert (
        await service.update_options(2, draft.id, {"preset": "red_carpet"}, saved.revision) is None
    )
    outcomes = await asyncio.gather(
        *[
            service.update_options(1, draft.id, {"preset": preset}, saved.revision)
            for preset in ("diamond_night", "red_carpet")
        ]
    )
    assert sum(value is not None for value in outcomes) == 1
    assert await service.submit(1, draft.id, saved.revision) is None
    restarted = JobService(sessions, {"glamour_letters", "comedy_stage"})
    current = await restarted.get_draft(1, draft.id)
    assert current is not None and current.revision == saved.revision + 1
    job = await restarted.submit(1, draft.id, current.revision)
    assert job is not None and job.options_json == current.options_json
    assert await restarted.submit(2, draft.id, current.revision) is None
    repeated = await restarted.submit(1, draft.id, current.revision)
    assert repeated is not None and repeated.id == job.id
    workspace = tmp_path / "workspace"
    request = tmp_path / "request.json"
    result = tmp_path / "result.json"
    request.write_text(
        RunnerInput(
            job_id=job.id,
            lease_token="token",
            plugin_id=job.plugin_id,
            plugin_version=job.plugin_version,
            input_json=job.input_json,
            options_json=job.options_json,
            workspace=str(workspace),
        ).model_dump_json()
    )
    await execute(request, result, {"glamour_letters"}, character_pack)
    manifest = RunnerResult.model_validate_json(result.read_text())
    assert (workspace / manifest.path).is_file()
    assert json.loads(job.input_json)["text"] == "ЁЖ"
    await engine.dispose()
