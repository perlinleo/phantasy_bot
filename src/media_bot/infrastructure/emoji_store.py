from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from media_bot.infrastructure.db import EmojiItem, EmojiSet


class SqliteEmojiStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], user_id: int) -> None:
        self._sessions = sessions
        self._user_id = user_id

    async def exists(self, set_name: str) -> bool:
        async with self._sessions() as session:
            return (
                await session.scalar(select(EmojiSet.id).where(EmojiSet.set_name == set_name))
                is not None
            )

    async def create_set(self, set_name: str) -> None:
        async with self._sessions() as session:
            session.add(EmojiSet(user_id=self._user_id, set_name=set_name))
            await session.commit()

    async def get(self, set_name: str, content_hash: str) -> str | None:
        async with self._sessions() as session:
            return await session.scalar(
                select(EmojiItem.custom_emoji_id)
                .join(EmojiSet)
                .where(EmojiSet.set_name == set_name, EmojiItem.tile_hash == content_hash)
            )

    async def put(self, set_name: str, content_hash: str, custom_emoji_id: str) -> None:
        async with self._sessions() as session:
            emoji_set = await session.scalar(select(EmojiSet).where(EmojiSet.set_name == set_name))
            if emoji_set is None:
                raise RuntimeError("Emoji set mapping is missing")
            session.add(
                EmojiItem(
                    emoji_set_id=emoji_set.id,
                    tile_hash=content_hash,
                    custom_emoji_id=custom_emoji_id,
                )
            )
            await session.commit()
