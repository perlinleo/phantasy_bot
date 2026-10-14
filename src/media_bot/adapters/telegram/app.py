import asyncio
import html
import json
import logging
from contextlib import suppress
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from media_bot.application.access import AccessService
from media_bot.application.jobs import JobService
from media_bot.domain.access import AccessDecision
from media_bot.infrastructure.emoji_store import SqliteEmojiStore
from media_bot.plugin_sdk.contracts import PluginSpec
from media_bot.plugins.registry import enabled_plugins, search_plugins
from media_bot.services.emoji import sticker_set_name
from media_bot.services.emoji_publisher import EmojiPublisher
from media_bot.version import __version__

LOG = logging.getLogger(__name__)
VERSION_FOOTER = f"\n\n<code>v{__version__}</code>"


def versioned(text: str) -> str:
    return f"{text}{VERSION_FOOTER}"


def resend_keyboard(job_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отправить результат ещё раз", callback_data=f"resend:{job_id}"
                )
            ]
        ]
    )


def catalog_keyboard(
    specs: list[PluginSpec[Any, Any]], categories: set[str] | None = None
) -> InlineKeyboardMarkup:
    category_rows = (
        [
            [
                InlineKeyboardButton(
                    text=f"Категория: {category}", callback_data=f"category:{category}"
                )
            ]
            for category in sorted(categories)
        ]
        if categories
        else []
    )
    tool_rows = [
        [InlineKeyboardButton(text=spec.title, callback_data=f"tool:{spec.id}")] for spec in specs
    ]
    return InlineKeyboardMarkup(inline_keyboard=category_rows + tool_rows)


def build_dispatcher(
    access: AccessService, enabled: set[str], jobs: JobService | None = None
) -> Dispatcher:
    router = Router(name="private")
    plugins = enabled_plugins(enabled)

    async def permitted(message: Message) -> bool:
        if message.chat.type != "private" or message.from_user is None:
            return False
        decision = await access.decision_for(message.from_user.id, message.from_user.username)
        return decision is not AccessDecision.DENIED

    @router.message(Command("whoami"))
    async def whoami(message: Message) -> None:
        if message.chat.type == "private" and message.from_user is not None:
            await message.answer(f"Ваш Telegram ID: <code>{message.from_user.id}</code>")

    @router.message(Command("start"))
    async def start(message: Message) -> None:
        if not await permitted(message):
            await message.answer(versioned("Доступ не одобрен. Используйте /request_access."))
            return
        await message.answer(
            versioned("Добро пожаловать. Используйте /tools, чтобы выбрать инструмент.")
        )

    @router.message(Command("request_access"))
    async def request_access(message: Message) -> None:
        if message.from_user is None or message.chat.type != "private":
            return
        decision = await access.decision_for(message.from_user.id, message.from_user.username)
        if decision is not AccessDecision.DENIED:
            await message.answer(versioned("Доступ уже предоставлен."))
            return
        created = await access.request_access(message.from_user.id)
        await message.answer(
            versioned("Заявка отправлена владельцу." if created else "Заявка уже ожидает решения.")
        )

    @router.message(Command("requests"))
    async def requests(message: Message) -> None:
        if (
            message.from_user is None
            or await access.decision_for(message.from_user.id) is not AccessDecision.OWNER
        ):
            return
        pending = await access.pending_requests()
        await message.answer(
            versioned(
                "\n".join(f"• <code>{item.user_id}</code>" for item in pending) or "Нет заявок."
            )
        )

    @router.message(Command("allow", "revoke"))
    async def manage_access(message: Message) -> None:
        if (
            message.from_user is None
            or await access.decision_for(message.from_user.id) is not AccessDecision.OWNER
        ):
            return
        command, _, value = (message.text or "").partition(" ")
        if not value.isdigit():
            await message.answer(versioned("Используйте /allow ID или /revoke ID."))
            return
        target = int(value)
        if command.startswith("/allow"):
            await access.allow(message.from_user.id, target)
            await message.answer(versioned(f"Доступ для <code>{target}</code> предоставлен."))
        else:
            revoked = await access.revoke(message.from_user.id, target)
            await message.answer(
                versioned("Доступ отозван." if revoked else "Нельзя отозвать доступ.")
            )

    @router.message(Command("status"))
    async def status(message: Message) -> None:
        if message.from_user is None or jobs is None:
            return
        if await access.decision_for(message.from_user.id) is not AccessDecision.OWNER:
            return
        counts = await jobs.status_counts()
        body = "\n".join(f"{name}: {count}" for name, count in sorted(counts.items()))
        await message.answer(versioned(body or "Очередь пуста."))

    @router.message(Command("tools"))
    async def tools(message: Message) -> None:
        if not await permitted(message):
            await message.answer("Доступ к функциям бота пока не одобрен.")
            return
        query = (message.text or "").partition(" ")[2]
        matches = search_plugins(enabled, query)
        listing = "\n".join(f"• <b>{spec.title}</b> — {spec.description}" for spec in matches)
        categories = {spec.category for spec in matches} if not query else None
        keyboard = catalog_keyboard(matches, categories)
        await message.answer(versioned(listing or "Инструменты не найдены."), reply_markup=keyboard)

    @router.callback_query(F.data.startswith("category:"))
    async def filter_category(callback: CallbackQuery) -> None:
        if callback.data is None:
            return
        category = callback.data.removeprefix("category:")
        matches = [spec for spec in plugins.values() if spec.category == category]
        if not matches:
            await callback.answer("Категория недоступна", show_alert=True)
            return
        await callback.answer()
        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                versioned(
                    "\n".join(f"• <b>{spec.title}</b> — {spec.description}" for spec in matches)
                ),
                reply_markup=catalog_keyboard(matches),
            )

    @router.callback_query(F.data.startswith("tool:"))
    async def select_tool(callback: CallbackQuery) -> None:
        if callback.data is None or callback.from_user is None:
            return
        plugin_id = callback.data.removeprefix("tool:")
        decision = await access.decision_for(callback.from_user.id, callback.from_user.username)
        if decision is AccessDecision.DENIED:
            await callback.answer("Доступ не одобрен", show_alert=True)
            return
        spec = plugins.get(plugin_id)
        if spec is None:
            await callback.answer("Инструмент недоступен", show_alert=True)
            return
        await callback.answer()
        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                versioned(
                    f"<b>{spec.title}</b>\n{spec.description}\n\n"
                    "Пример временно недоступен, но создание задачи не начнётся до подтверждения."
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Использовать", callback_data=f"use:{spec.id}")]
                    ]
                ),
            )

    @router.callback_query(F.data.startswith("use:"))
    async def use_tool(callback: CallbackQuery) -> None:
        if callback.data is None or callback.from_user is None or jobs is None:
            return
        plugin_id = callback.data.removeprefix("use:")
        decision = await access.decision_for(callback.from_user.id, callback.from_user.username)
        if decision is AccessDecision.DENIED:
            await callback.answer("Доступ не одобрен", show_alert=True)
            return
        spec = plugins.get(plugin_id)
        if spec is None or not isinstance(callback.message, Message):
            await callback.answer("Инструмент недоступен", show_alert=True)
            return
        await jobs.new_draft(callback.from_user.id, callback.message.chat.id, plugin_id)
        await callback.answer()
        await callback.message.answer(versioned(f"Отправьте текст для «{spec.title}»."))

    @router.message(Command("new"))
    async def new_job(message: Message) -> None:
        if not await permitted(message):
            await message.answer("Доступ к функциям бота пока не одобрен.")
            return
        if jobs is None or message.from_user is None:
            await message.answer("Создание задач временно недоступно.")
            return
        command = (message.text or "").split(maxsplit=1)
        if len(command) == 1:
            await message.answer(versioned("Выберите инструмент через /tools."))
            return
        plugin_id = command[1].strip()
        try:
            await jobs.new_draft(message.from_user.id, message.chat.id, plugin_id)
        except ValueError:
            await message.answer(
                "Используйте /new text_card, /new space_crawl или /new text_to_emoji."
            )
            return
        spec = plugins[plugin_id]
        warning = (
            "\n\n⚠️ Custom emoji наборы Telegram могут быть открыты по ссылке. "
            "Не используйте секретный текст."
            if plugin_id == "text_to_emoji"
            else ""
        )
        await message.answer(versioned(f"Отправьте текст для «{spec.title}».{warning}"))

    @router.message(Command("jobs"))
    async def list_jobs(message: Message) -> None:
        if not await permitted(message):
            await message.answer("Доступ к функциям бота пока не одобрен.")
            return
        if jobs is None or message.from_user is None:
            await message.answer("Задачи пока недоступны.")
            return
        records = await jobs.user_jobs(message.from_user.id)
        text = "\n".join(f"{job.id[:8]} — {job.status}: {job.stage}" for job in records)
        await message.answer(versioned(text or "У вас пока нет задач."))

    @router.message(Command("help"))
    async def help_command(message: Message) -> None:
        if not await permitted(message):
            await message.answer("Доступ к функциям бота пока не одобрен.")
            return
        await message.answer(
            versioned(
                "/tools — каталог инструментов\n"
                "/new — создать задачу\n"
                "/jobs — ваши задачи\n"
                "/cancel — отменить текущий черновик\n"
                "/whoami — ваш Telegram ID"
            )
        )

    @router.message(Command("cancel"))
    async def cancel_draft(message: Message) -> None:
        if not await permitted(message) or jobs is None or message.from_user is None:
            return
        cancelled = await jobs.cancel_draft(message.from_user.id)
        await message.answer(
            versioned("Черновик отменён." if cancelled else "Нет активного черновика.")
        )

    @router.message(F.text)
    async def unknown(message: Message) -> None:
        if not await permitted(message):
            await message.answer("Доступ к функциям бота пока не одобрен.")
            return
        if jobs is None or message.from_user is None:
            await message.answer("Используйте /start или /whoami.")
            return
        text = message.text or ""
        if text.startswith("/"):
            await message.answer(versioned("Неизвестная команда. Используйте /help."))
            return
        try:
            draft = await jobs.save_text(message.from_user.id, text)
        except ValueError:
            await message.answer(versioned("Этот ввод не подходит для выбранного инструмента."))
            return
        if draft is None:
            await message.answer("Используйте /new, чтобы создать карточку.")
            return
        spec = plugins[draft.plugin_id]
        options = json.loads(draft.options_json)
        text_preview = html.escape((draft.text or "")[:300])
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Создать", callback_data=f"create:{draft.id}:{draft.revision}"
                    )
                ],
                [InlineKeyboardButton(text="Настройки", callback_data=f"settings:{draft.id}")],
            ]
        )
        await message.answer(
            versioned(
                f"<b>{spec.title}</b>\n\nТекст:\n<blockquote>{text_preview}</blockquote>\n"
                f"Настройки: <code>{html.escape(json.dumps(options, ensure_ascii=False))}</code>\n"
                f"Результат: {'MP4 без звука' if spec.category == 'video' else 'PNG'}\n\n"
                "Проверьте данные и нажмите «Создать»."
            ),
            reply_markup=keyboard,
        )

    @router.callback_query(F.data.startswith("settings:"))
    async def settings_menu(callback: CallbackQuery) -> None:
        if callback.from_user is None or callback.data is None or jobs is None:
            return
        draft = await jobs.get_draft(callback.from_user.id, callback.data.removeprefix("settings:"))
        if draft is None:
            await callback.answer("Этот шаг уже завершён", show_alert=True)
            return
        presets = {
            "text_card": [("Тёмный фон", "dark"), ("Светлый фон", "light")],
            "space_crawl": [("Коротко: 5 секунд", "short"), ("Обычно: 8 секунд", "normal")],
            "text_to_emoji": [("Синий", "blue"), ("Фиолетовый", "purple")],
        }.get(draft.plugin_id, [])
        if not presets:
            await callback.answer(
                "Этот инструмент использует настройки по умолчанию", show_alert=True
            )
            return
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=title, callback_data=f"preset:{draft.id}:{preset}")]
                for title, preset in presets
            ]
        )
        await callback.answer()
        if callback.message is not None:
            await callback.message.answer("Выберите вариант настройки:", reply_markup=keyboard)

    @router.callback_query(F.data.startswith("preset:"))
    async def apply_preset(callback: CallbackQuery) -> None:
        if callback.from_user is None or callback.data is None or jobs is None:
            return
        _, draft_id, preset = callback.data.split(":", 2)
        draft = await jobs.get_draft(callback.from_user.id, draft_id)
        if draft is None:
            await callback.answer("Этот шаг уже завершён", show_alert=True)
            return
        presets: dict[str, dict[str, object]] = {
            "dark": {"background": "#15182b", "foreground": "#f8f4e8"},
            "light": {"background": "#f8f4e8", "foreground": "#15182b"},
            "short": {"duration_seconds": 5},
            "normal": {"duration_seconds": 8},
            "blue": {"background": "#2a72e5"},
            "purple": {"background": "#6c4ac9"},
        }
        updates = presets[preset]
        updated = await jobs.update_options(callback.from_user.id, draft_id, updates)
        await callback.answer(
            "Настройки сохранены" if updated else "Этот шаг уже завершён",
            show_alert=updated is None,
        )

    @router.callback_query(F.data.startswith("create:"))
    async def create_job(callback: CallbackQuery) -> None:
        if callback.from_user is None or jobs is None or callback.data is None:
            return
        parts = callback.data.split(":")
        if len(parts) != 3 or not parts[2].isdigit():
            await callback.answer("Некорректная кнопка", show_alert=True)
            return
        decision = await access.decision_for(callback.from_user.id, callback.from_user.username)
        try:
            job = (
                await jobs.submit(callback.from_user.id, parts[1], int(parts[2]))
                if decision is not AccessDecision.DENIED
                else None
            )
        except ValueError:
            await callback.answer("Достигнут лимит незавершённых задач", show_alert=True)
            return
        if job is None:
            await callback.answer("Этот шаг уже завершён", show_alert=True)
            return
        if job.status_message_id is not None:
            await callback.answer("Задача уже поставлена в очередь")
            return
        await callback.answer("Задача поставлена в очередь")
        if isinstance(callback.message, Message):
            card = await callback.message.answer(
                versioned(
                    f"<b>{plugins[job.plugin_id].title}</b>\nОжидает обработки\n\n{job.id[:8]}"
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Отменить", callback_data=f"cancel:{job.id}")]
                    ]
                ),
            )
            await jobs.set_status_message(job.id, card.message_id)

    @router.callback_query(F.data.startswith("cancel:"))
    async def cancel_job(callback: CallbackQuery) -> None:
        if callback.from_user is None or callback.data is None or jobs is None:
            return
        job_id = callback.data.removeprefix("cancel:")
        cancelled = await jobs.cancel_queued(callback.from_user.id, job_id)
        requested = not cancelled and await jobs.request_running_cancel(
            callback.from_user.id, job_id
        )
        if cancelled or requested:
            await callback.answer("Задача отменена" if cancelled else "Отмена запрошена")
            if isinstance(callback.message, Message):
                await callback.message.edit_text(
                    versioned("Задача отменена." if cancelled else "Отмена запрошена.")
                )
        else:
            await callback.answer("Задача уже выполняется или завершена", show_alert=True)

    @router.callback_query(F.data.startswith("resend:"))
    async def resend_job(callback: CallbackQuery) -> None:
        if callback.from_user is None or callback.data is None or jobs is None:
            return
        resent = await jobs.resend_delivery(
            callback.from_user.id, callback.data.removeprefix("resend:")
        )
        await callback.answer(
            "Повторная отправка запланирована" if resent else "Повторная отправка недоступна",
            show_alert=not resent,
        )

    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    return dispatcher


async def run_bot(token: str, access: AccessService, enabled: set[str], jobs: JobService) -> None:
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    dispatcher = build_dispatcher(access, enabled, jobs)
    plugins = enabled_plugins(enabled)

    async def deliver() -> None:
        recovered = await jobs.recover_sending_deliveries()
        if recovered:
            LOG.warning("marked interrupted deliveries uncertain", extra={"count": recovered})
        identity = await bot.get_me()
        bot_username = identity.username or "PhantasyBot"
        while True:
            claimed = await jobs.claim_delivery()
            if claimed is None:
                await asyncio.sleep(1)
                continue
            delivery, job = claimed
            if await access.decision_for(job.user_id) is AccessDecision.DENIED:
                final_job = await jobs.suppress_delivery(
                    delivery.id, "Access was revoked before delivery"
                )
                delivery_status = "Отправка отменена"
            else:
                try:
                    if Path(job.result_path or "").suffix.lower() == ".mp4":
                        await bot.send_animation(
                            job.chat_id, FSInputFile(Path(job.result_path or ""))
                        )
                    elif job.plugin_id in {
                        "text_to_emoji",
                        "blood_gothic_emoji",
                        "ghost_emoji",
                        "iron_gothic_emoji",
                    }:
                        preview = Path(job.result_path or "")
                        tiles = sorted(preview.parent.glob("tile-*.png"))
                        try:
                            publisher = EmojiPublisher(
                                bot,
                                SqliteEmojiStore(jobs.sessions, job.user_id),
                            )
                            set_name = sticker_set_name(job.user_id, 1, bot_username)
                            emoji_ids = await publisher.publish(
                                job.user_id, set_name, "Phantasy Bot", tiles
                            )
                            composition = "".join(
                                f'<tg-emoji emoji-id="{emoji_id}">▫️</tg-emoji>'
                                for emoji_id in emoji_ids
                            )
                            await bot.send_message(job.chat_id, composition)
                        except Exception:
                            LOG.exception(
                                "custom emoji unavailable; sending PNG fallback",
                                extra={"job_id": job.id},
                            )
                            await bot.send_photo(
                                job.chat_id,
                                FSInputFile(preview),
                                caption=versioned(
                                    "PNG fallback: custom emoji недоступны для этого чата."
                                ),
                            )
                    else:
                        await bot.send_photo(job.chat_id, FSInputFile(Path(job.result_path or "")))
                except TelegramRetryAfter as error:
                    retry_after = int(error.retry_after)
                    final_job, scheduled = await jobs.retry_delivery(
                        delivery.id,
                        retry_after,
                        f"Telegram rate limit; retry after {retry_after}s",
                    )
                    delivery_status = (
                        "Повторная отправка запланирована" if scheduled else "Не удалось отправить"
                    )
                except TimeoutError:
                    final_job = await jobs.mark_delivery_uncertain(
                        delivery.id, "Telegram request timed out; result may have been sent"
                    )
                    delivery_status = "Статус отправки не определён"
                except TelegramForbiddenError:
                    final_job = await jobs.fail_delivery(
                        delivery.id, "Bot is blocked by the recipient"
                    )
                    delivery_status = "Не удалось отправить"
                except Exception:
                    LOG.exception("delivery failed", extra={"job_id": job.id})
                    final_job, scheduled = await jobs.retry_delivery(
                        delivery.id, 5, "Telegram delivery failed"
                    )
                    delivery_status = (
                        "Повторная отправка запланирована" if scheduled else "Не удалось отправить"
                    )
                else:
                    final_job = await jobs.mark_delivery_sent(delivery.id)
                    delivery_status = "Отправлено"
            if final_job is not None and final_job.status_message_id is not None:
                try:
                    await bot.edit_message_text(
                        versioned(
                            f"<b>{plugins[final_job.plugin_id].title}</b>\n{delivery_status}\n\n{final_job.id[:8]}"
                        ),
                        chat_id=final_job.chat_id,
                        message_id=final_job.status_message_id,
                        reply_markup=(
                            resend_keyboard(final_job.id)
                            if delivery_status == "Статус отправки не определён"
                            or delivery_status == "Не удалось отправить"
                            else None
                        ),
                    )
                except Exception:
                    LOG.debug("final progress card update skipped", exc_info=True)

    async def present_progress() -> None:
        while True:
            for job in await jobs.progress_jobs():
                if job.status_message_id is None:
                    continue
                stage = "Ожидает worker" if job.status == "queued" else html.escape(job.stage)
                if job.status == "running" and job.stage == "rendering":
                    stage = "Рендер"
                progress = ""
                if job.status == "running" and job.fraction is not None:
                    completed = round(job.fraction * 10)
                    progress = f"\n{'█' * completed}{'░' * (10 - completed)} {job.fraction:.0%}"
                try:
                    await bot.edit_message_text(
                        f"<b>{plugins[job.plugin_id].title}</b>\n{stage}{progress}\n\n{job.id[:8]}",
                        chat_id=job.chat_id,
                        message_id=job.status_message_id,
                    )
                except Exception:
                    LOG.debug("progress card update skipped", exc_info=True)
            await asyncio.sleep(0.5)

    delivery_task = asyncio.create_task(deliver())
    progress_task = asyncio.create_task(present_progress())
    try:
        LOG.info("starting Telegram polling")
        await dispatcher.start_polling(bot, handle_as_tasks=False)
    finally:
        delivery_task.cancel()
        progress_task.cancel()
        with suppress(asyncio.CancelledError):
            await delivery_task
        with suppress(asyncio.CancelledError):
            await progress_task
