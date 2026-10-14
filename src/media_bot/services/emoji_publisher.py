from pathlib import Path
from typing import Protocol

from aiogram.types import FSInputFile, InputSticker, StickerSet

from media_bot.services.emoji import tile_hash


class EmojiBot(Protocol):
    async def create_new_sticker_set(
        self,
        user_id: int,
        name: str,
        title: str,
        stickers: list[InputSticker],
        sticker_type: str | None = None,
    ) -> bool: ...
    async def add_sticker_to_set(self, user_id: int, name: str, sticker: InputSticker) -> bool: ...
    async def get_sticker_set(self, name: str) -> StickerSet: ...


class EmojiStore(Protocol):
    async def exists(self, set_name: str) -> bool: ...
    async def create_set(self, set_name: str) -> None: ...
    async def get(self, set_name: str, content_hash: str) -> str | None: ...
    async def put(self, set_name: str, content_hash: str, custom_emoji_id: str) -> None: ...


class EmojiPublisher:
    """Upload one tile at a time and reconcile IDs from Telegram after each success."""

    def __init__(self, bot: EmojiBot, store: EmojiStore) -> None:
        self._bot = bot
        self._store = store

    async def publish(
        self, user_id: int, set_name: str, title: str, tile_paths: list[Path]
    ) -> list[str]:
        published: list[str] = []
        created = await self._store.exists(set_name)
        for path in tile_paths:
            content_hash = tile_hash(path.read_bytes())
            known = await self._store.get(set_name, content_hash)
            if known is not None:
                published.append(known)
                continue
            sticker = InputSticker(sticker=FSInputFile(path), format="static", emoji_list=["▫️"])
            before = await self._custom_ids(set_name) if created else set()
            if not created:
                await self._bot.create_new_sticker_set(
                    user_id=user_id,
                    name=set_name,
                    title=title,
                    stickers=[sticker],
                    sticker_type="custom_emoji",
                )
                await self._store.create_set(set_name)
                created = True
            else:
                await self._bot.add_sticker_to_set(user_id=user_id, name=set_name, sticker=sticker)
            after = await self._custom_ids(set_name)
            new_ids = after - before
            if len(new_ids) != 1:
                raise RuntimeError("Could not reconcile published custom emoji")
            custom_id = new_ids.pop()
            await self._store.put(set_name, content_hash, custom_id)
            published.append(custom_id)
        return published

    async def _custom_ids(self, set_name: str) -> set[str]:
        sticker_set = await self._bot.get_sticker_set(set_name)
        return {
            sticker.custom_emoji_id for sticker in sticker_set.stickers if sticker.custom_emoji_id
        }
