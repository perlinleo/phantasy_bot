import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def create_backup(database: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"app-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.sqlite3"
    with sqlite3.connect(database) as source, sqlite3.connect(target) as destination:
        source.backup(destination)
    return target
