import argparse
import asyncio
import json
from pathlib import Path

from alembic import command
from alembic.config import Config

from media_bot.bootstrap import configure_logging, with_access_service
from media_bot.config import Settings
from media_bot.plugin_sdk.contracts import JobContext
from media_bot.plugins.registry import enabled_plugins


async def migrate(settings: Settings) -> None:
    settings.data_dir.joinpath("db").mkdir(parents=True, exist_ok=True)
    config = Config("alembic.ini")
    config.set_main_option(
        "sqlalchemy.url", f"sqlite:///{settings.data_dir / 'db' / 'app.sqlite3'}"
    )
    command.upgrade(config, "head")
    print(f"Database schema is ready at {settings.data_dir / 'db' / 'app.sqlite3'}")


async def render_text_card(settings: Settings, text: str, output: Path) -> None:
    spec = enabled_plugins(settings.enabled_plugins).get("text_card")
    if spec is None:
        raise ValueError("text_card is not enabled")
    output.mkdir(parents=True, exist_ok=True)
    input_data = spec.input_model.model_validate({"text": text})
    options = spec.options_model()
    result = await spec.run(input_data, options, JobContext(workspace=output))
    print(output / result.path)


async def bot(settings: Settings) -> None:
    from media_bot.adapters.telegram.app import run_bot
    from media_bot.application.jobs import JobService

    await with_access_service(
        settings,
        lambda access: run_bot(
            settings.require_bot_token(),
            access,
            settings.enabled_plugins,
            JobService(
                access.sessions,
                settings.enabled_plugins,
                max_queue_size=settings.max_queue_size,
                max_user_unfinished=settings.max_user_unfinished,
            ),
        ),
    )


async def allow(settings: Settings, telegram_id: int) -> None:
    async def complete(access: object) -> None:
        from media_bot.application.access import AccessService

        assert isinstance(access, AccessService)
        owner_id = settings.require_owner()
        await access.allow(actor_id=owner_id, subject_id=telegram_id)
        print(f"Allowed Telegram ID {telegram_id}")

    await with_access_service(settings, complete)


async def worker(settings: Settings) -> None:
    from media_bot.application.jobs import JobService
    from media_bot.infrastructure.db import make_engine, make_session_factory
    from media_bot.infrastructure.worker import run_worker

    engine = make_engine(settings.database_url)
    try:
        await run_worker(
            JobService(
                make_session_factory(engine),
                settings.enabled_plugins,
                max_queue_size=settings.max_queue_size,
                max_user_unfinished=settings.max_user_unfinished,
            ),
            settings.data_dir,
            settings.enabled_plugins,
            timeout_seconds=settings.job_timeout_seconds,
        )
    finally:
        await engine.dispose()


async def run_payload(input_path: Path, output_path: Path, plugins: set[str]) -> None:
    from media_bot.infrastructure.runner_exec import execute

    await execute(input_path, output_path, plugins)


def backup(settings: Settings) -> None:
    from media_bot.infrastructure.backup import create_backup

    path = create_backup(settings.data_dir / "db" / "app.sqlite3", settings.data_dir / "backups")
    print(path)


def cleanup(settings: Settings, dry_run: bool) -> None:
    from media_bot.infrastructure.cleanup import expired_result_files

    if not dry_run:
        raise ValueError(
            "Only cleanup --dry-run is available until delivery-aware cleanup is implemented"
        )
    files = expired_result_files(settings.data_dir / "results", settings.retention_days)
    for path in files:
        print(path)


def healthcheck(settings: Settings, role: str) -> None:
    from media_bot.infrastructure.health import check_database

    revision = check_database(settings.data_dir / "db" / "app.sqlite3")
    print(f"{role}: ok (schema {revision})")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="media-bot")
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate")
    sub.add_parser("bot")
    sub.add_parser("worker")
    sub.add_parser("backup")
    cleanup_command = sub.add_parser("cleanup")
    cleanup_command.add_argument("--dry-run", action="store_true")
    health = sub.add_parser("healthcheck")
    health.add_argument("--role", choices=("bot", "worker"), required=True)
    payload = sub.add_parser("run-payload")
    payload.add_argument("--input", type=Path, required=True)
    payload.add_argument("--output", type=Path, required=True)
    payload.add_argument("--plugins", required=True)
    render = sub.add_parser("render-text-card", help="Render a text_card PNG without Telegram")
    render.add_argument("--text", required=True)
    render.add_argument("--output", type=Path, required=True)
    allow_user = sub.add_parser("allow", help="Allow a Telegram user by numeric ID")
    allow_user.add_argument("telegram_id", type=int)
    plugins = sub.add_parser("plugins")
    plugins.add_argument("action", choices=("list", "validate"))
    return result


def main() -> None:
    args = parser().parse_args()
    if args.command == "run-payload":
        asyncio.run(run_payload(args.input, args.output, set(args.plugins.split(","))))
        return
    settings = Settings()
    configure_logging(settings.log_level)
    if args.command == "migrate":
        asyncio.run(migrate(settings))
    elif args.command == "bot":
        asyncio.run(bot(settings))
    elif args.command == "worker":
        asyncio.run(worker(settings))
    elif args.command == "backup":
        backup(settings)
    elif args.command == "cleanup":
        cleanup(settings, args.dry_run)
    elif args.command == "healthcheck":
        healthcheck(settings, args.role)
    elif args.command == "render-text-card":
        asyncio.run(render_text_card(settings, args.text, args.output))
    elif args.command == "allow":
        asyncio.run(allow(settings, args.telegram_id))
    else:
        plugins = enabled_plugins(settings.enabled_plugins)
        if args.action == "validate":
            print("Plugin registry is valid")
        else:
            print(
                json.dumps(
                    {key: value.version for key, value in plugins.items()}, ensure_ascii=False
                )
            )


if __name__ == "__main__":
    main()
