import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from media_bot.infrastructure.cleanup import expired_result_files


def test_cleanup_lists_only_expired_result_files(tmp_path: Path) -> None:
    recent, expired = tmp_path / "recent.png", tmp_path / "expired.png"
    recent.write_bytes(b"recent")
    expired.write_bytes(b"expired")
    old = (datetime.now(UTC) - timedelta(days=8)).timestamp()
    os.utime(expired, (old, old))
    assert expired_result_files(tmp_path, 7) == [expired]
