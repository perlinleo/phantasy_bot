import json
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from media_bot.domain.jobs import JobStatus
from media_bot.infrastructure.db import Delivery, Draft, Job
from media_bot.plugins.registry import enabled_plugins


class JobService:
    _max_delivery_attempts = 3

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        enabled: set[str],
        max_queue_size: int = 20,
        max_user_unfinished: int = 3,
    ) -> None:
        self._sessions = sessions
        self._plugins = enabled_plugins(enabled)
        self._max_queue_size = max_queue_size
        self._max_user_unfinished = max_user_unfinished

    @property
    def sessions(self) -> async_sessionmaker[AsyncSession]:
        return self._sessions

    async def new_draft(self, user_id: int, chat_id: int, plugin_id: str = "text_card") -> Draft:
        if plugin_id not in self._plugins:
            raise ValueError("Unknown plugin")
        async with self._sessions() as session:
            result = await session.scalars(
                select(Draft).where(Draft.user_id == user_id, Draft.status == "editing")
            )
            for draft in result:
                draft.status = "cancelled"
            draft = Draft(
                id=str(uuid4()),
                user_id=user_id,
                chat_id=chat_id,
                plugin_id=plugin_id,
                options_json=self._plugins[plugin_id].options_model().model_dump_json(),
            )
            session.add(draft)
            await session.commit()
            return draft

    async def save_text(self, user_id: int, text: str) -> Draft | None:
        async with self._sessions() as session:
            draft = await session.scalar(
                select(Draft).where(Draft.user_id == user_id, Draft.status == "editing")
            )
            if draft is None:
                return None
            self._plugins[draft.plugin_id].input_model.model_validate({"text": text})
            draft.text = text
            draft.revision += 1
            await session.commit()
            return draft

    async def cancel_draft(self, user_id: int) -> bool:
        async with self._sessions() as session:
            draft = await session.scalar(
                select(Draft).where(Draft.user_id == user_id, Draft.status == "editing")
            )
            if draft is None:
                return False
            draft.status = "cancelled"
            await session.commit()
            return True

    async def update_options(
        self, user_id: int, draft_id: str, updates: dict[str, object]
    ) -> Draft | None:
        async with self._sessions() as session:
            draft = await session.get(Draft, draft_id)
            if draft is None or draft.user_id != user_id or draft.status != "editing":
                return None
            options = self._plugins[draft.plugin_id].options_model.model_validate_json(
                draft.options_json
            )
            merged = options.model_dump() | updates
            draft.options_json = (
                self._plugins[draft.plugin_id]
                .options_model.model_validate(merged)
                .model_dump_json()
            )
            draft.revision += 1
            await session.commit()
            return draft

    async def get_draft(self, user_id: int, draft_id: str) -> Draft | None:
        async with self._sessions() as session:
            draft = await session.get(Draft, draft_id)
            return (
                draft
                if draft is not None and draft.user_id == user_id and draft.status == "editing"
                else None
            )

    async def submit(self, user_id: int, draft_id: str, revision: int) -> Job | None:
        async with self._sessions() as session:
            await session.execute(text("BEGIN IMMEDIATE"))
            key = f"{draft_id}:{revision}"
            try:
                existing = await session.scalar(select(Job).where(Job.submission_key == key))
                if existing is not None:
                    await session.commit()
                    return existing
                queued_count = await session.scalar(
                    select(func.count()).select_from(Job).where(Job.status == JobStatus.QUEUED)
                )
                user_count = await session.scalar(
                    select(func.count())
                    .select_from(Job)
                    .where(
                        Job.user_id == user_id,
                        Job.status.in_((JobStatus.QUEUED, JobStatus.RUNNING)),
                    )
                )
                if (queued_count or 0) >= self._max_queue_size or (
                    user_count or 0
                ) >= self._max_user_unfinished:
                    raise ValueError("Job limit reached")
                draft = await session.get(Draft, draft_id)
                if (
                    draft is None
                    or draft.user_id != user_id
                    or draft.status != "editing"
                    or draft.revision != revision
                    or not draft.text
                ):
                    await session.rollback()
                    return None
                spec = self._plugins[draft.plugin_id]
                job = Job(
                    id=str(uuid4()),
                    user_id=user_id,
                    chat_id=draft.chat_id,
                    plugin_id=spec.id,
                    plugin_version=spec.version,
                    submission_key=key,
                    input_json=json.dumps({"text": draft.text}),
                    options_json=draft.options_json,
                )
                draft.status = "submitted"
                session.add(job)
                await session.commit()
                return job
            except Exception:
                await session.rollback()
                raise

    async def claim(self, worker_id: str | None = None) -> Job | None:
        worker_id = worker_id or str(uuid4())
        token = str(uuid4())
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=30)
        async with self._sessions() as session:
            async with session.begin():
                claimed_id = await session.scalar(
                    text(
                        "UPDATE jobs SET status = 'running', stage = 'rendering', "
                        "attempt_count = attempt_count + 1, started_at = :now, "
                        "lease_owner = :owner, lease_token = :token, "
                        "lease_expires_at = :expires, heartbeat_at = :now "
                        "WHERE id = (SELECT id FROM jobs WHERE status = 'queued' "
                        "AND cancel_requested = 0 ORDER BY created_at LIMIT 1) RETURNING id"
                    ),
                    {"now": now, "owner": worker_id, "token": token, "expires": expires},
                )
                if claimed_id is None:
                    return None
                job = await session.get(Job, claimed_id)
                return job

    async def recover_expired_leases(self) -> int:
        async with self._sessions() as session:
            result = cast(
                CursorResult[tuple[()]],
                await session.execute(
                    text(
                        "UPDATE jobs SET status = CASE WHEN attempt_count < 2 "
                        "THEN 'queued' ELSE 'interrupted' END, "
                        "stage = CASE WHEN attempt_count < 2 THEN 'waiting_retry' "
                        "ELSE 'interrupted' END, "
                        "lease_owner = NULL, lease_token = NULL, lease_expires_at = NULL "
                        "WHERE status = 'running' AND lease_expires_at < :now"
                    ),
                    {"now": datetime.now(UTC)},
                ),
            )
            await session.commit()
            return int(result.rowcount or 0)

    async def running_job(self, job_id: str, lease_token: str) -> Job | None:
        async with self._sessions() as session:
            job = await session.get(Job, job_id)
            return (
                job
                if job is not None
                and job.status == JobStatus.RUNNING
                and job.lease_token == lease_token
                else None
            )

    async def heartbeat(self, job_id: str, lease_token: str) -> bool:
        async with self._sessions() as session:
            job = await session.get(Job, job_id)
            if job is None or job.status != JobStatus.RUNNING or job.lease_token != lease_token:
                return False
            now = datetime.now(UTC)
            job.heartbeat_at = now
            job.lease_expires_at = now + timedelta(seconds=30)
            await session.commit()
            return True

    async def update_progress(
        self, job_id: str, lease_token: str, stage: str, fraction: float | None
    ) -> bool:
        if fraction is not None and not 0 <= fraction <= 1:
            return False
        async with self._sessions() as session:
            job = await session.get(Job, job_id)
            if job is None or job.status != JobStatus.RUNNING or job.lease_token != lease_token:
                return False
            job.stage = stage
            job.fraction = fraction
            await session.commit()
            return True

    async def cancel_queued(self, user_id: int, job_id: str) -> bool:
        async with self._sessions() as session:
            result = await session.execute(
                text(
                    "UPDATE jobs SET status = 'cancelled', stage = 'cancelled', "
                    "cancel_requested = 1, finished_at = :now "
                    "WHERE id = :job_id AND user_id = :user_id AND status = 'queued'"
                ),
                {"now": datetime.now(UTC), "job_id": job_id, "user_id": user_id},
            )
            await session.commit()
            return bool(cast(CursorResult[tuple[()]], result).rowcount)

    async def request_running_cancel(self, user_id: int, job_id: str) -> bool:
        async with self._sessions() as session:
            result = await session.execute(
                text(
                    "UPDATE jobs SET cancel_requested = 1 "
                    "WHERE id = :job_id AND user_id = :user_id AND status = 'running'"
                ),
                {"job_id": job_id, "user_id": user_id},
            )
            await session.commit()
            return bool(cast(CursorResult[tuple[()]], result).rowcount)

    async def cancellation_requested(self, job_id: str, lease_token: str) -> bool:
        async with self._sessions() as session:
            job = await session.get(Job, job_id)
            return bool(
                job is not None
                and job.status == JobStatus.RUNNING
                and job.lease_token == lease_token
                and job.cancel_requested
            )

    async def mark_cancelled(self, job_id: str, lease_token: str) -> bool:
        async with self._sessions() as session:
            job = await session.get(Job, job_id)
            if job is None or job.status != JobStatus.RUNNING or job.lease_token != lease_token:
                return False
            job.status = JobStatus.CANCELLED
            job.stage = "cancelled"
            job.finished_at = datetime.now(UTC)
            await session.commit()
            return True

    async def complete(self, job_id: str, lease_token: str, result_path: str) -> None:
        async with self._sessions() as session:
            job = await session.get(Job, job_id)
            if job is None or job.status != JobStatus.RUNNING or job.lease_token != lease_token:
                return
            job.status, job.stage, job.result_path = JobStatus.COMPLETED, "completed", result_path
            job.finished_at = datetime.now(UTC)
            session.add(Delivery(job_id=job_id))
            await session.commit()

    async def fail(self, job_id: str, lease_token: str | None, message: str) -> None:
        async with self._sessions() as session:
            job = await session.get(Job, job_id)
            if job is not None and (lease_token is None or job.lease_token == lease_token):
                job.status, job.stage, job.error_message = JobStatus.FAILED, "failed", message[:300]
                job.finished_at = datetime.now(UTC)
                await session.commit()

    async def user_jobs(self, user_id: int) -> list[Job]:
        async with self._sessions() as session:
            result = await session.scalars(
                select(Job).where(Job.user_id == user_id).order_by(Job.created_at.desc()).limit(10)
            )
            return list(result)

    async def set_status_message(self, job_id: str, message_id: int) -> None:
        async with self._sessions() as session:
            job = await session.get(Job, job_id)
            if job is not None:
                job.status_message_id = message_id
                await session.commit()

    async def progress_jobs(self) -> list[Job]:
        async with self._sessions() as session:
            result = await session.scalars(
                select(Job).where(
                    Job.status_message_id.is_not(None), Job.status.in_(("queued", "running"))
                )
            )
            return list(result)

    async def claim_delivery(self) -> tuple[Delivery, Job] | None:
        now = datetime.now(UTC)
        async with self._sessions() as session:
            async with session.begin():
                claimed_id = await session.scalar(
                    text(
                        "UPDATE deliveries SET status = 'sending', attempts = attempts + 1, "
                        "sending_started_at = :now, next_attempt_at = NULL "
                        "WHERE id = (SELECT id FROM deliveries WHERE status = 'pending' "
                        "AND (next_attempt_at IS NULL OR next_attempt_at <= :now) "
                        "ORDER BY created_at LIMIT 1) RETURNING id"
                    ),
                    {"now": now},
                )
                if claimed_id is None:
                    return None
                delivery = await session.get(Delivery, claimed_id)
                if delivery is None:
                    return None
                job = await session.get(Job, delivery.job_id)
                if job is None or job.result_path is None:
                    delivery.status = "failed"
                    return None
                return delivery, job

    async def finish_delivery(self, delivery_id: int, success: bool) -> Job | None:
        return (
            await self.mark_delivery_sent(delivery_id)
            if success
            else await self.fail_delivery(delivery_id, "Delivery failed")
        )

    async def mark_delivery_sent(self, delivery_id: int) -> Job | None:
        async with self._sessions() as session:
            delivery = await session.get(Delivery, delivery_id)
            if delivery is None or delivery.status != "sending":
                return None
            delivery.status = "sent"
            delivery.sending_started_at = None
            job = await session.get(Job, delivery.job_id)
            await session.commit()
            return job

    async def retry_delivery(
        self, delivery_id: int, retry_after: int, message: str
    ) -> tuple[Job | None, bool]:
        async with self._sessions() as session:
            delivery = await session.get(Delivery, delivery_id)
            if delivery is None or delivery.status != "sending":
                return None, False
            job = await session.get(Job, delivery.job_id)
            delivery.error_message = message[:300]
            delivery.sending_started_at = None
            if delivery.attempts >= self._max_delivery_attempts:
                delivery.status = "failed"
                await session.commit()
                return job, False
            delivery.status = "pending"
            delivery.next_attempt_at = datetime.now(UTC) + timedelta(seconds=max(retry_after, 1))
            await session.commit()
            return job, True

    async def mark_delivery_uncertain(self, delivery_id: int, message: str) -> Job | None:
        async with self._sessions() as session:
            delivery = await session.get(Delivery, delivery_id)
            if delivery is None or delivery.status != "sending":
                return None
            delivery.status = "uncertain"
            delivery.error_message = message[:300]
            delivery.sending_started_at = None
            job = await session.get(Job, delivery.job_id)
            await session.commit()
            return job

    async def fail_delivery(self, delivery_id: int, message: str) -> Job | None:
        async with self._sessions() as session:
            delivery = await session.get(Delivery, delivery_id)
            if delivery is None or delivery.status != "sending":
                return None
            delivery.status = "failed"
            delivery.error_message = message[:300]
            delivery.sending_started_at = None
            job = await session.get(Job, delivery.job_id)
            await session.commit()
            return job

    async def suppress_delivery(self, delivery_id: int, message: str) -> Job | None:
        async with self._sessions() as session:
            delivery = await session.get(Delivery, delivery_id)
            if delivery is None or delivery.status != "sending":
                return None
            delivery.status = "suppressed"
            delivery.error_message = message[:300]
            delivery.sending_started_at = None
            job = await session.get(Job, delivery.job_id)
            await session.commit()
            return job

    async def recover_sending_deliveries(self) -> int:
        async with self._sessions() as session:
            result = await session.execute(
                text(
                    "UPDATE deliveries SET status = 'uncertain', sending_started_at = NULL, "
                    "error_message = 'Delivery interrupted during restart' WHERE status = 'sending'"
                )
            )
            await session.commit()
            return int(cast(CursorResult[tuple[()]], result).rowcount or 0)

    async def resend_delivery(self, user_id: int, job_id: str) -> bool:
        async with self._sessions() as session:
            job = await session.get(Job, job_id)
            if job is None or job.user_id != user_id or job.status != JobStatus.COMPLETED:
                return False
            delivery = await session.scalar(select(Delivery).where(Delivery.job_id == job_id))
            if delivery is None or delivery.status not in {"uncertain", "failed"}:
                return False
            delivery.status = "pending"
            delivery.next_attempt_at = None
            delivery.error_message = None
            await session.commit()
            return True

    async def status_counts(self) -> dict[str, int]:
        async with self._sessions() as session:
            rows = await session.execute(select(Job.status, func.count()).group_by(Job.status))
            return {str(status): int(count) for status, count in rows}
