from pathlib import Path
from types import SimpleNamespace

from media_bot.services.emoji_publisher import EmojiPublisher


class Store:
    def __init__(self, exists: bool = False) -> None:
        self.exists_value = exists
        self.values: dict[str, str] = {}

    async def exists(self, _: str) -> bool:
        return self.exists_value

    async def create_set(self, _: str) -> None:
        self.exists_value = True

    async def get(self, _: str, content_hash: str) -> str | None:
        return self.values.get(content_hash)

    async def put(self, _: str, content_hash: str, emoji_id: str) -> None:
        self.values[content_hash] = emoji_id


class Bot:
    def __init__(self) -> None:
        self.ids: list[str] = []

    async def create_new_sticker_set(self, **_: object) -> bool:
        self.ids.append("one")
        return True

    async def add_sticker_to_set(self, **_: object) -> bool:
        self.ids.append("two")
        return True

    async def get_sticker_set(self, _: str) -> object:
        return SimpleNamespace(
            stickers=[SimpleNamespace(custom_emoji_id=value) for value in self.ids]
        )


async def test_publisher_reconciles_new_and_existing_tiles(tmp_path: Path) -> None:
    first, second = tmp_path / "one.png", tmp_path / "two.png"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    store, bot = Store(), Bot()
    publisher = EmojiPublisher(bot, store)  # type: ignore[arg-type]

    assert await publisher.publish(1, "set_by_TestBot", "Test", [first, second]) == ["one", "two"]
    assert await publisher.publish(1, "set_by_TestBot", "Test", [first]) == ["one"]
