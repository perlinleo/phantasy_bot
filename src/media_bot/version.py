from importlib.resources import files


def get_version() -> str:
    """Return the version bundled with the application image."""
    return files("media_bot").joinpath("VERSION").read_text(encoding="utf-8").strip()


__version__ = get_version()
