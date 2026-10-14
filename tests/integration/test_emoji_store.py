from media_bot.application.access import AccessService
from media_bot.infrastructure.db import create_schema, make_engine, make_session_factory
from media_bot.infrastructure.emoji_store import SqliteEmojiStore


async def test_sqlite_emoji_store_persists_tile_mapping(tmp_path):
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'app.sqlite3'}")
    await create_schema(engine)
    sessions = make_session_factory(engine)
    await AccessService(sessions, owner_id=1).decision_for(1)
    store = SqliteEmojiStore(sessions, 1)
    assert not await store.exists("set_by_TestBot")
    await store.create_set("set_by_TestBot")
    assert await store.exists("set_by_TestBot")
    assert await store.get("set_by_TestBot", "hash") is None
    await store.put("set_by_TestBot", "hash", "emoji-id")
    assert await store.get("set_by_TestBot", "hash") == "emoji-id"
    await engine.dispose()
