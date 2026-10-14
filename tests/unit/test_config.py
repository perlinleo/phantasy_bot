from pathlib import Path

import pytest
from pydantic import SecretStr

from media_bot.config import Settings


def test_settings_parse_values_and_build_database_url(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        owner_telegram_id=123,
        bot_token=SecretStr("token"),
        enabled_plugins="text_card, extra",
    )

    assert settings.enabled_plugins == {"text_card", "extra"}
    assert settings.database_url == f"sqlite+aiosqlite:///{tmp_path / 'db' / 'app.sqlite3'}"
    assert settings.require_owner() == 123
    assert settings.require_bot_token() == "token"


@pytest.mark.parametrize("value", [{"text_card"}, ["text_card"], ("text_card",)])
def test_settings_accept_plugin_collections(value: object) -> None:
    assert Settings(enabled_plugins=value).enabled_plugins == {"text_card"}


def test_settings_requires_owner_and_token() -> None:
    settings = Settings(owner_telegram_id=0, _env_file=None)
    with pytest.raises(ValueError, match="OWNER_TELEGRAM_ID"):
        settings.require_owner()
    with pytest.raises(ValueError, match="BOT_TOKEN"):
        settings.require_bot_token()
