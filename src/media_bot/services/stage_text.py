"""Bounded typography for the two character-based renderers."""

import unicodedata

from PIL import ImageFont

from media_bot.services.typography import load_font

PUNCTUATION = " .,!?—–-:;()+&'\""


def display_text(text: str) -> str:
    # Preserve the original input in the job; only normalize the display copy.
    normalized = unicodedata.normalize("NFC", text)
    if not normalized.strip():
        raise ValueError("Введите непустую надпись.")
    for char in normalized:
        if not (
            "a" <= char <= "z"
            or "A" <= char <= "Z"
            or "а" <= char <= "я"
            or "А" <= char <= "Я"
            or char in "ёЁ0123456789\n" + PUNCTUATION
        ):
            raise ValueError("Используйте русские/латинские буквы, цифры и обычную пунктуацию.")
    return normalized


def letter_rows(text: str) -> list[str]:
    text = display_text(text)
    if len(text.replace(" ", "").replace("\n", "")) > 12:
        raise ValueError("Максимум 12 букв или знаков, по 6 в строке.")
    rows: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            raise ValueError("Пустые строки не поддерживаются.")
        row = ""
        count = 0
        for char in paragraph:
            if char != " " and count == 6:
                rows.append(row)
                row, count = "", 0
            row += char
            count += char != " "
        rows.append(row)
    if len(rows) > 2:
        raise ValueError("Максимум две строки по шесть букв.")
    return rows


def fit_stage_text(text: str) -> tuple[list[str], ImageFont.FreeTypeFont]:
    text = display_text(text)
    if len(text.split("\n")) > 3:
        raise ValueError("Максимум три строки.")
    for size in range(64, 43, -2):
        font = load_font(size)
        lines: list[str] = []
        for paragraph in text.split("\n"):
            current = ""
            for char in paragraph:
                if current and font.getlength(current + char) > 650:
                    # Prefer a word boundary; keep all spaces and original characters.
                    split = current.rfind(" ")
                    if split > 0:
                        lines.append(current[: split + 1])
                        current = current[split + 1 :] + char
                    else:
                        lines.append(current)
                        current = char
                else:
                    current += char
            lines.append(current)
        if len(lines) <= 3 and all(font.getlength(line) <= 650 for line in lines):
            return lines, font
    raise ValueError("Надпись не помещается на табло. Сократите текст до трёх строк.")
