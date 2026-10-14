from datetime import UTC, datetime, timedelta
from pathlib import Path


def expired_result_files(results_dir: Path, retention_days: int) -> list[Path]:
    if not results_dir.exists():
        return []
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    return [
        path
        for path in results_dir.rglob("*")
        if path.is_file() and datetime.fromtimestamp(path.stat().st_mtime, UTC) < cutoff
    ]
