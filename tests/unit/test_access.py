from pathlib import Path

from media_bot.application.access import AccessService
from media_bot.domain.access import AccessDecision
from media_bot.infrastructure.db import create_schema, make_engine, make_session_factory


async def test_owner_and_allowlist_are_distinct(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'app.sqlite3'}")
    await create_schema(engine)
    service = AccessService(make_session_factory(engine), owner_id=1)
    assert await service.decision_for(1) is AccessDecision.OWNER
    assert await service.decision_for(2) is AccessDecision.DENIED
    await service.allow(actor_id=1, subject_id=2)
    assert await service.decision_for(2) is AccessDecision.ALLOWED
    assert [user.telegram_id for user in await service.allowed_users()] == [1, 2]
    assert await service.decision_for(2, "new_username") is AccessDecision.ALLOWED
    await engine.dispose()


async def test_allow_creates_user_without_prior_request(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'app.sqlite3'}")
    await create_schema(engine)
    service = AccessService(make_session_factory(engine), owner_id=1)

    await service.allow(actor_id=1, subject_id=42)

    assert await service.decision_for(42) is AccessDecision.ALLOWED
    await engine.dispose()


async def test_access_requests_and_revoke_are_idempotent(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'app.sqlite3'}")
    await create_schema(engine)
    service = AccessService(make_session_factory(engine), owner_id=1)
    await service.decision_for(2)
    assert await service.request_access(2)
    assert not await service.request_access(2)
    assert [request.user_id for request in await service.pending_requests()] == [2]
    await service.allow(1, 2)
    assert await service.revoke(1, 2)
    assert not await service.revoke(1, 2)
    assert not await service.revoke(1, 1)
    await engine.dispose()
