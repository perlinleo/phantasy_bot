from typing import Any

from media_bot.plugin_sdk.contracts import PluginSpec
from media_bot.plugins.blood_gothic_emoji import SPEC as BLOOD_GOTHIC_EMOJI
from media_bot.plugins.ghost_emoji import SPEC as GHOST_EMOJI
from media_bot.plugins.gothic_metal_title import SPEC as GOTHIC_METAL_TITLE
from media_bot.plugins.iron_gothic_emoji import SPEC as IRON_GOTHIC_EMOJI
from media_bot.plugins.space_crawl import SPEC as SPACE_CRAWL
from media_bot.plugins.text_card import SPEC as TEXT_CARD
from media_bot.plugins.text_to_emoji import SPEC as TEXT_TO_EMOJI


def enabled_plugins(enabled: set[str]) -> dict[str, PluginSpec[Any, Any]]:
    available: dict[str, PluginSpec[Any, Any]] = {
        TEXT_CARD.id: TEXT_CARD,
        SPACE_CRAWL.id: SPACE_CRAWL,
        TEXT_TO_EMOJI.id: TEXT_TO_EMOJI,
        BLOOD_GOTHIC_EMOJI.id: BLOOD_GOTHIC_EMOJI,
        GHOST_EMOJI.id: GHOST_EMOJI,
        GOTHIC_METAL_TITLE.id: GOTHIC_METAL_TITLE,
        IRON_GOTHIC_EMOJI.id: IRON_GOTHIC_EMOJI,
    }
    unknown = enabled - available.keys()
    if unknown:
        raise ValueError(f"Unknown enabled plugins: {', '.join(sorted(unknown))}")
    return {plugin_id: available[plugin_id] for plugin_id in enabled}


def search_plugins(enabled: set[str], query: str) -> list[PluginSpec[Any, Any]]:
    needle = query.casefold().strip()
    return [
        spec
        for spec in enabled_plugins(enabled).values()
        if not needle or needle in " ".join((spec.title, spec.description, *spec.tags)).casefold()
    ]
