import sqlite3
from pathlib import Path


def check_database(database: Path) -> str:
    if not database.exists():
        raise RuntimeError("Database file is missing")
    with sqlite3.connect(database) as connection:
        row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    if row is None:
        raise RuntimeError("Database schema version is missing")
    return str(row[0])
