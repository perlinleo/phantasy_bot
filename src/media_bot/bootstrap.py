import logging
from collections.abc import Awaitable, Callable
from typing import Any

from media_bot.application.access import AccessService
from media_bot.config import Settings
from media_bot.infrastructure.db import make_engine, make_session_factory


async def with_access_service(
    settings: Settings, operation: Callable[[AccessService], Awaitable[Any]]
) -> Any:
    settings.data_dir.joinpath("db").mkdir(parents=True, exist_ok=True)
    engine = make_engine(settings.database_url)
    try:
        access = AccessService(make_session_factory(engine), settings.require_owner())
        return await operation(access)
    finally:
        await engine.dispose()


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
