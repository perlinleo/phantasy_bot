import sqlite3
from pathlib import Path

import pytest

from media_bot.infrastructure.health import check_database


def test_healthcheck_reads_alembic_revision(tmp_path: Path) -> None:
    database = tmp_path / "app.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num VARCHAR(32))")
        connection.execute("INSERT INTO alembic_version VALUES ('0007_access_requests')")
    assert check_database(database) == "0007_access_requests"


def test_healthcheck_rejects_missing_schema(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        check_database(tmp_path / "missing.sqlite3")
