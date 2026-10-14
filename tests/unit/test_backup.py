import sqlite3
from pathlib import Path

from media_bot.infrastructure.backup import create_backup


def test_online_backup_copies_database(tmp_path: Path) -> None:
    source = tmp_path / "app.sqlite3"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('ok')")
    backup = create_backup(source, tmp_path / "backups")
    with sqlite3.connect(backup) as connection:
        assert connection.execute("SELECT value FROM sample").fetchone() == ("ok",)
