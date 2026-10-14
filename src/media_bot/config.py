from pathlib import Path
from typing import cast

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings shared by CLI roles; role-specific values are checked at startup."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", enable_decoding=False)

    data_dir: Path = Path("/data")
    owner_telegram_id: int | None = None
    bot_token: SecretStr | None = None
    enabled_plugins: set[str] = Field(default_factory=lambda: {"text_card"})
    timezone: str = "UTC"
    job_timeout_seconds: int = Field(default=300, gt=0)
    retention_days: int = Field(default=7, gt=0)
    max_queue_size: int = Field(default=20, gt=0)
    max_user_unfinished: int = Field(default=3, gt=0)
    log_level: str = "INFO"

    @field_validator("enabled_plugins", mode="before")
    @classmethod
    def parse_plugins(cls, value: object) -> set[str]:
        if isinstance(value, str):
            return {item.strip() for item in value.split(",") if item.strip()}
        if isinstance(value, (set, list, tuple)):
            return {str(item) for item in value}
        return cast(set[str], value)

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.data_dir / 'db' / 'app.sqlite3'}"

    def require_owner(self) -> int:
        if self.owner_telegram_id is None or self.owner_telegram_id <= 0:
            raise ValueError("OWNER_TELEGRAM_ID must be a positive Telegram ID")
        return self.owner_telegram_id

    def require_bot_token(self) -> str:
        if self.bot_token is None:
            raise ValueError("BOT_TOKEN is required for the bot role")
        return self.bot_token.get_secret_value()
