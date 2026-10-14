from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from media_bot.domain.access import AccessDecision
from media_bot.infrastructure.db import AccessRequest, AuditEvent, User


class AccessService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], owner_id: int) -> None:
        self._sessions = sessions
        self._owner_id = owner_id

    @property
    def sessions(self) -> async_sessionmaker[AsyncSession]:
        return self._sessions

    async def decision_for(self, telegram_id: int, username: str | None = None) -> AccessDecision:
        if telegram_id == self._owner_id:
            async with self._sessions() as session:
                if await session.get(User, telegram_id) is None:
                    session.add(User(telegram_id=telegram_id, username=username, access="allowed"))
                    await session.commit()
            return AccessDecision.OWNER
        async with self._sessions() as session:
            user = await session.get(User, telegram_id)
            if user is None:
                session.add(User(telegram_id=telegram_id, username=username))
                await session.commit()
                return AccessDecision.DENIED
            if username != user.username:
                user.username = username
                await session.commit()
            return AccessDecision.ALLOWED if user.access == "allowed" else AccessDecision.DENIED

    async def allow(self, actor_id: int, subject_id: int) -> None:
        async with self._sessions() as session:
            user = await session.get(User, subject_id)
            if user is None:
                user = User(telegram_id=subject_id, access="allowed")
                session.add(user)
            else:
                user.access = "allowed"
            await session.flush()
            session.add(AuditEvent(actor_id=actor_id, subject_id=subject_id, action="allow"))
            await session.commit()

    async def request_access(self, telegram_id: int) -> bool:
        async with self._sessions() as session:
            request = await session.scalar(
                select(AccessRequest).where(AccessRequest.user_id == telegram_id)
            )
            if request is not None and request.status == "pending":
                return False
            if request is None:
                session.add(AccessRequest(user_id=telegram_id, status="pending"))
            else:
                request.status = "pending"
            await session.commit()
            return True

    async def pending_requests(self) -> list[AccessRequest]:
        async with self._sessions() as session:
            result = await session.scalars(
                select(AccessRequest)
                .where(AccessRequest.status == "pending")
                .order_by(AccessRequest.created_at)
            )
            return list(result)

    async def revoke(self, actor_id: int, subject_id: int) -> bool:
        if subject_id == self._owner_id:
            return False
        async with self._sessions() as session:
            user = await session.get(User, subject_id)
            if user is None or user.access != "allowed":
                return False
            user.access = "denied"
            session.add(AuditEvent(actor_id=actor_id, subject_id=subject_id, action="revoke"))
            await session.commit()
            return True

    async def allowed_users(self) -> list[User]:
        async with self._sessions() as session:
            result = await session.scalars(select(User).where(User.access == "allowed"))
            return list(result)
