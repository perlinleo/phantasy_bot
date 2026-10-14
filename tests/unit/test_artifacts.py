from pathlib import Path

import pytest

from media_bot.infrastructure.artifacts import ArtifactValidationError, validate_artifact


def test_artifact_validator_accepts_workspace_file(tmp_path: Path) -> None:
    artifact = tmp_path / "result.png"
    artifact.write_bytes(b"\x89PNG\r\n\x1a\nvalid")
    assert validate_artifact(tmp_path, "result.png", {".png"}) == artifact.resolve()


def test_artifact_validator_rejects_escape_and_wrong_format(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("no")
    with pytest.raises(ArtifactValidationError):
        validate_artifact(tmp_path, "../outside.txt", {".png"})
    invalid = tmp_path / "result.txt"
    invalid.write_text("no")
    with pytest.raises(ArtifactValidationError):
        validate_artifact(tmp_path, "result.txt", {".png"})


def test_artifact_validator_rejects_empty_oversized_and_mismatched_content(tmp_path: Path) -> None:
    empty = tmp_path / "empty.png"
    empty.touch()
    with pytest.raises(ArtifactValidationError, match="size"):
        validate_artifact(tmp_path, "empty.png", {".png"})
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"not a PNG")
    with pytest.raises(ArtifactValidationError, match="content"):
        validate_artifact(tmp_path, "fake.png", {".png"})
    large = tmp_path / "large.png"
    large.write_bytes(b"\x89PNG\r\n\x1a\nmore")
    with pytest.raises(ArtifactValidationError, match="size"):
        validate_artifact(tmp_path, "large.png", {".png"}, max_bytes=1)
