from pathlib import Path

from media_bot.application.access import AccessService
from media_bot.bootstrap import configure_logging, with_access_service
from media_bot.config import Settings
from media_bot.domain.access import AccessDecision
from media_bot.infrastructure.db import create_schema, make_engine


async def test_with_access_service_creates_parent_and_disposes_engine(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, owner_telegram_id=7)
    engine = make_engine(settings.database_url)
    settings.data_dir.joinpath("db").mkdir(parents=True)
    await create_schema(engine)
    await engine.dispose()

    async def use_service(access: AccessService) -> AccessDecision:
        return await access.decision_for(7)

    assert await with_access_service(settings, use_service) is AccessDecision.OWNER


def test_configure_logging() -> None:
    configure_logging("INFO")
