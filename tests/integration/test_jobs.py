import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from media_bot.application.access import AccessService
from media_bot.application.jobs import JobService
from media_bot.domain.jobs import JobStatus
from media_bot.infrastructure.artifacts import validate_artifact
from media_bot.infrastructure.db import Delivery, create_schema, make_engine, make_session_factory
from media_bot.infrastructure.runner_exec import execute
from media_bot.infrastructure.runner_protocol import RunnerInput, RunnerResult


async def test_text_card_job_is_persisted_rendered_and_marked_for_delivery(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.joinpath("db").mkdir(parents=True)
    engine = make_engine(f"sqlite+aiosqlite:///{data_dir / 'db' / 'app.sqlite3'}")
    await create_schema(engine)
    sessions = make_session_factory(engine)
    await AccessService(sessions, owner_id=1).decision_for(1)
    service = JobService(sessions, {"text_card"})

    draft = await service.new_draft(user_id=1, chat_id=1)
    saved = await service.save_text(1, "Задача из очереди")
    assert saved is not None
    job = await service.submit(1, draft.id, saved.revision)
    assert job is not None
    assert [record.id for record in await service.user_jobs(1)] == [job.id]
    claimed = await service.claim()
    assert claimed is not None and claimed.id == job.id

    workspace = data_dir / "results" / job.id
    input_path, output_path = workspace / "input.json", workspace / "result.json"
    workspace.mkdir(parents=True)
    input_path.write_text(
        RunnerInput(
            job_id=job.id,
            lease_token=claimed.lease_token or "",
            plugin_id=claimed.plugin_id,
            plugin_version=claimed.plugin_version,
            input_json=claimed.input_json,
            options_json=claimed.options_json,
            workspace=str(workspace),
        ).model_dump_json(),
        encoding="utf-8",
    )
    await execute(input_path, output_path, {"text_card"})
    result = RunnerResult.model_validate_json(output_path.read_text(encoding="utf-8"))
    artifact = validate_artifact(workspace, result.path, {".png", ".webp"})
    await service.complete(job.id, claimed.lease_token or "", str(artifact))

    completed = await service.running_job(job.id, claimed.lease_token or "")
    assert completed is None
    async with sessions() as session:
        stored = await session.get(type(job), job.id)
        assert stored is not None
        assert stored.status == JobStatus.COMPLETED
        assert stored.result_path is not None
        assert Path(stored.result_path).is_file()
    claimed_delivery = await service.claim_delivery()
    assert claimed_delivery is not None
    delivery, delivered_job = claimed_delivery
    assert delivered_job.id == job.id
    await service.finish_delivery(delivery.id, True)
    assert await service.claim_delivery() is None
    await engine.dispose()


async def test_job_service_rejects_stale_drafts_and_records_failures(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'app.sqlite3'}")
    await create_schema(engine)
    sessions = make_session_factory(engine)
    await AccessService(sessions, owner_id=1).decision_for(1)
    service = JobService(sessions, {"text_card"})

    assert await service.save_text(1, "orphan") is None
    draft = await service.new_draft(1, 1)
    with pytest.raises(ValueError):
        await service.save_text(1, "x" * 501)
    assert await service.submit(1, draft.id, 0) is None
    saved = await service.save_text(1, "text")
    assert saved is not None
    assert await service.submit(2, draft.id, saved.revision) is None
    job = await service.submit(1, draft.id, saved.revision)
    assert job is not None
    await service.fail(job.id, None, "failure")
    async with sessions() as session:
        stored = await session.get(type(job), job.id)
        assert stored is not None
        assert stored.status == JobStatus.FAILED
        assert stored.error_message == "failure"
    await engine.dispose()


async def test_expired_lease_is_interrupted(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'app.sqlite3'}")
    await create_schema(engine)
    sessions = make_session_factory(engine)
    await AccessService(sessions, owner_id=1).decision_for(1)
    service = JobService(sessions, {"text_card"})
    draft = await service.new_draft(1, 1)
    saved = await service.save_text(1, "lease")
    assert saved is not None
    job = await service.submit(1, draft.id, saved.revision)
    assert job is not None
    claimed = await service.claim("worker")
    assert claimed is not None
    assert await service.heartbeat(job.id, claimed.lease_token or "")
    async with sessions() as session:
        stored = await session.get(type(job), job.id)
        assert stored is not None
        stored.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()
    assert await service.recover_expired_leases() == 1
    async with sessions() as session:
        recovered = await session.get(type(job), job.id)
        assert recovered is not None and recovered.status == "queued"
    await engine.dispose()


async def test_user_can_cancel_own_queued_job(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'app.sqlite3'}")
    await create_schema(engine)
    sessions = make_session_factory(engine)
    await AccessService(sessions, owner_id=1).decision_for(1)
    service = JobService(sessions, {"text_card"})
    draft = await service.new_draft(1, 1)
    saved = await service.save_text(1, "cancel")
    assert saved is not None
    job = await service.submit(1, draft.id, saved.revision)
    assert job is not None
    assert await service.cancel_queued(1, job.id)
    assert not await service.cancel_queued(1, job.id)
    assert await service.status_counts() == {"cancelled": 1}
    await engine.dispose()


async def test_user_can_cancel_active_draft(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'app.sqlite3'}")
    await create_schema(engine)
    sessions = make_session_factory(engine)
    await AccessService(sessions, owner_id=1).decision_for(1)
    service = JobService(sessions, {"text_card"})
    await service.new_draft(1, 1)
    assert await service.cancel_draft(1)
    assert not await service.cancel_draft(1)
    await engine.dispose()


async def test_submission_respects_user_limit(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'app.sqlite3'}")
    await create_schema(engine)
    sessions = make_session_factory(engine)
    await AccessService(sessions, owner_id=1).decision_for(1)
    service = JobService(sessions, {"text_card"}, max_user_unfinished=1)
    first = await service.new_draft(1, 1)
    saved = await service.save_text(1, "one")
    assert saved is not None and await service.submit(1, first.id, saved.revision)
    second = await service.new_draft(1, 1)
    saved = await service.save_text(1, "two")
    assert saved is not None
    with pytest.raises(ValueError, match="Job limit"):
        await service.submit(1, second.id, saved.revision)
    await engine.dispose()


async def test_submission_is_idempotent_for_concurrent_confirmation(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'app.sqlite3'}")
    await create_schema(engine)
    sessions = make_session_factory(engine)
    await AccessService(sessions, owner_id=1).decision_for(1)
    service = JobService(sessions, {"text_card"})
    draft = await service.new_draft(1, 1)
    saved = await service.save_text(1, "once")
    assert saved is not None

    first, second = await asyncio.gather(
        service.submit(1, draft.id, saved.revision), service.submit(1, draft.id, saved.revision)
    )

    assert first is not None and second is not None and first.id == second.id
    assert [record.id for record in await service.user_jobs(1)] == [first.id]
    await engine.dispose()


async def test_running_job_cancel_request_requires_current_lease(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'app.sqlite3'}")
    await create_schema(engine)
    sessions = make_session_factory(engine)
    await AccessService(sessions, owner_id=1).decision_for(1)
    service = JobService(sessions, {"text_card"})
    draft = await service.new_draft(1, 1)
    saved = await service.save_text(1, "cancel running")
    assert saved is not None
    job = await service.submit(1, draft.id, saved.revision)
    assert job is not None
    claimed = await service.claim()
    assert claimed is not None
    token = claimed.lease_token or ""
    assert await service.update_progress(job.id, token, "rendering", 0.5)
    assert not await service.update_progress(job.id, "old-token", "rendering", 0.6)
    assert not await service.update_progress(job.id, token, "rendering", 1.1)
    async with sessions() as session:
        stored = await session.get(type(job), job.id)
        assert stored is not None and stored.stage == "rendering" and stored.fraction == 0.5
    assert await service.request_running_cancel(1, job.id)
    assert await service.cancellation_requested(job.id, token)
    assert not await service.cancellation_requested(job.id, "old-token")
    assert not await service.mark_cancelled(job.id, "old-token")
    assert await service.mark_cancelled(job.id, token)
    await engine.dispose()


async def test_delivery_retries_are_delayed_and_interrupted_sends_are_uncertain(
    tmp_path: Path,
) -> None:
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'app.sqlite3'}")
    await create_schema(engine)
    sessions = make_session_factory(engine)
    await AccessService(sessions, owner_id=1).decision_for(1)
    service = JobService(sessions, {"text_card"})
    draft = await service.new_draft(1, 1)
    saved = await service.save_text(1, "deliver")
    assert saved is not None
    job = await service.submit(1, draft.id, saved.revision)
    assert job is not None
    claimed_job = await service.claim()
    assert claimed_job is not None
    await service.complete(job.id, claimed_job.lease_token or "", str(tmp_path / "result.png"))

    claimed_delivery = await service.claim_delivery()
    assert claimed_delivery is not None
    delivery, _ = claimed_delivery
    _, scheduled = await service.retry_delivery(delivery.id, 60, "retry later")
    assert scheduled
    assert await service.claim_delivery() is None

    async with sessions() as session:
        stored = await session.get(Delivery, delivery.id)
        assert stored is not None
        assert stored.status == "pending"
        assert stored.next_attempt_at is not None
        stored.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()
    claimed_delivery = await service.claim_delivery()
    assert claimed_delivery is not None
    assert await service.recover_sending_deliveries() == 1
    async with sessions() as session:
        stored = await session.get(Delivery, delivery.id)
        assert stored is not None
        assert stored.status == "uncertain"
        assert "restart" in (stored.error_message or "")
    assert await service.resend_delivery(1, job.id)
    claimed_delivery = await service.claim_delivery()
    assert claimed_delivery is not None
    retried, _ = claimed_delivery
    _, scheduled = await service.retry_delivery(retried.id, 1, "last retry failed")
    assert not scheduled
    assert not await service.resend_delivery(2, job.id)
    assert await service.resend_delivery(1, job.id)
    claimed_delivery = await service.claim_delivery()
    assert claimed_delivery is not None
    suppressed, _ = claimed_delivery
    assert (await service.suppress_delivery(suppressed.id, "access revoked")) is not None
    async with sessions() as session:
        stored = await session.get(Delivery, delivery.id)
        assert stored is not None and stored.status == "suppressed"
    await engine.dispose()
