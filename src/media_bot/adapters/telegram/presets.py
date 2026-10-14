"""Explicit UI presets; callback keys are scoped to the selected plugin."""

import html
import json

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PRESETS: dict[str, dict[str, tuple[str, dict[str, object]]]] = {
    "text_card": {
        "dark": ("Тёмный фон", {"background": "#15182b", "foreground": "#f8f4e8"}),
        "light": ("Светлый фон", {"background": "#f8f4e8", "foreground": "#15182b"}),
    },
    "space_crawl": {
        "short": ("Коротко: 5 секунд", {"duration_seconds": 5}),
        "normal": ("Обычно: 8 секунд", {"duration_seconds": 8}),
    },
    "text_to_emoji": {
        "blue": ("Синий", {"background": "#2a72e5"}),
        "purple": ("Фиолетовый", {"background": "#6c4ac9"}),
    },
    "glamour_letters": {
        "gold": ("Золотой салон", {"preset": "gold_lounge"}),
        "diamond": ("Бриллиантовая ночь", {"preset": "diamond_night"}),
        "carpet": ("Красная дорожка", {"preset": "red_carpet"}),
    },
    "comedy_stage": {
        "red6": ("Красная сцена · 6 с", {"preset": "classic_red", "duration_seconds": 6}),
        "red8": ("Красная сцена · 8 с", {"preset": "classic_red", "duration_seconds": 8}),
        "neon6": ("Неоновый roast · 6 с", {"preset": "neon_roast", "duration_seconds": 6}),
    },
}


def confirmation(
    plugin_id: str,
    title: str,
    category: str,
    draft_id: str,
    revision: int,
    text: str,
    options_json: str,
) -> tuple[str, InlineKeyboardMarkup]:
    options = json.loads(options_json)
    label = next(
        (
            title
            for title, values in PRESETS.get(plugin_id, {}).values()
            if all(options.get(key) == value for key, value in values.items())
        ),
        json.dumps(options, ensure_ascii=False),
    )
    preview = text[:300] + ("… (текст сокращён в сводке)" if len(text) > 300 else "")
    message = (
        f"<b>{html.escape(title)}</b>\n\nТекст:\n<blockquote>{html.escape(preview)}</blockquote>\n"
        f"Настройки: {html.escape(label)}\n"
        f"Результат: {'MP4 без звука' if category == 'video' else 'PNG'}\n\n"
        "Проверьте данные и нажмите «Создать»."
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Создать", callback_data=f"create:{draft_id}:{revision}")],
            [
                InlineKeyboardButton(
                    text="Настройки", callback_data=f"settings:{draft_id}:{revision}"
                )
            ],
        ]
    )
    return message, keyboard
