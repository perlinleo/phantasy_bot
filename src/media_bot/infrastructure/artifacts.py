from pathlib import Path


class ArtifactValidationError(ValueError):
    pass


def validate_artifact(
    workspace: Path,
    relative_path: str,
    allowed_suffixes: set[str],
    max_bytes: int = 50 * 1024 * 1024,
) -> Path:
    candidate = (workspace / relative_path).resolve()
    root = workspace.resolve()
    if root not in candidate.parents or candidate == root:
        raise ArtifactValidationError("Artifact path escapes workspace")
    if not candidate.is_file() or candidate.suffix.lower() not in allowed_suffixes:
        raise ArtifactValidationError("Artifact is missing or has an invalid format")
    size = candidate.stat().st_size
    if not 0 < size <= max_bytes:
        raise ArtifactValidationError("Artifact size is invalid")
    header = candidate.read_bytes()[:12]
    signatures = {
        ".png": b"\x89PNG\r\n\x1a\n",
        ".webp": b"RIFF",
        ".mp4": b"ftyp",
    }
    signature = signatures.get(candidate.suffix.lower())
    if (
        signature is None
        or (signature == b"ftyp" and header[4:8] != signature)
        or (signature != b"ftyp" and not header.startswith(signature))
    ):
        raise ArtifactValidationError("Artifact content does not match its format")
    return candidate
