import pytest

from media_bot.plugins.registry import enabled_plugins


def test_registry_returns_enabled_text_card() -> None:
    plugins = enabled_plugins({"text_card"})
    assert list(plugins) == ["text_card"]
    assert plugins["text_card"].version == "1"


def test_registry_rejects_unknown_plugin() -> None:
    with pytest.raises(ValueError, match="Unknown enabled plugins: missing"):
        enabled_plugins({"missing"})
