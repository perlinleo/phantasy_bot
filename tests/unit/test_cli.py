import argparse
from pathlib import Path

import pytest

from media_bot import __main__ as cli
from media_bot.config import Settings


async def test_migrate_configures_alembic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, str] = {}
    monkeypatch.setattr(
        cli.command, "upgrade", lambda config, revision: seen.update(revision=revision)
    )

    await cli.migrate(Settings(data_dir=tmp_path))

    assert seen == {"revision": "head"}
    assert tmp_path.joinpath("db").is_dir()


async def test_render_text_card_and_disabled_plugin(tmp_path: Path) -> None:
    settings = Settings(enabled_plugins={"text_card"})
    await cli.render_text_card(settings, "Тест", tmp_path)
    assert tmp_path.joinpath("text-card.png").is_file()

    with pytest.raises(ValueError, match="not enabled"):
        await cli.render_text_card(Settings(enabled_plugins=set()), "Тест", tmp_path)


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (argparse.Namespace(command="migrate"), "migrate"),
        (argparse.Namespace(command="bot"), "bot"),
        (argparse.Namespace(command="worker"), "worker"),
        (
            argparse.Namespace(command="render-text-card", text="Тест", output=Path("out")),
            "render",
        ),
        (argparse.Namespace(command="allow", telegram_id=9), "allow"),
    ],
)
def test_main_dispatches_async_commands(
    args: argparse.Namespace, expected: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    async def record(*_: object) -> None:
        calls.append(expected)

    monkeypatch.setattr(cli, "parser", lambda: _Parser(args))
    monkeypatch.setattr(cli, "migrate", record)
    monkeypatch.setattr(cli, "bot", record)
    monkeypatch.setattr(cli, "worker", record)
    monkeypatch.setattr(cli, "render_text_card", record)
    monkeypatch.setattr(cli, "allow", record)
    cli.main()
    assert calls == [expected]


def test_main_lists_and_validates_plugins(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        cli, "parser", lambda: _Parser(argparse.Namespace(command="plugins", action="validate"))
    )
    cli.main()
    assert "Plugin registry is valid" in capsys.readouterr().out

    monkeypatch.setattr(
        cli, "parser", lambda: _Parser(argparse.Namespace(command="plugins", action="list"))
    )
    cli.main()
    assert '"text_card": "1"' in capsys.readouterr().out


def test_parser_accepts_every_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv", ["media-bot", "render-text-card", "--text", "x", "--output", "out"]
    )
    assert cli.parser().parse_args().command == "render-text-card"


class _Parser:
    def __init__(self, args: argparse.Namespace) -> None:
        self._args = args

    def parse_args(self) -> argparse.Namespace:
        return self._args
