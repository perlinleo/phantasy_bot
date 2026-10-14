import hashlib
import re


def tile_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sticker_set_name(user_id: int, ordinal: int, bot_username: str) -> str:
    """Create a deterministic Bot API-compatible name without user text."""
    suffix = re.sub(r"[^A-Za-z0-9_]", "", bot_username)
    if not suffix.lower().endswith("bot"):
        suffix = f"{suffix}bot"
    return f"pb_{user_id}_{ordinal}_by_{suffix}"[:64]
