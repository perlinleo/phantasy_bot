from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod
from aiogram.types import CallbackQuery, Chat, Message, Update, User

from media_bot.adapters.telegram import app
from media_bot.domain.access import AccessDecision


class RecordingSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.methods: list[Any] = []

    async def close(self) -> None:
        return None

    async def make_request(
        self, bot: Bot, method: TelegramMethod[Any], timeout: int | None = None
    ) -> Any:
        self.methods.append(method)
        return Message(message_id=1, date=datetime.now(), chat=Chat(id=1, type="private"))

    async def stream_content(self, *_: Any, **__: Any) -> Any:
        if False:
            yield b""


class AccessStub:
    def __init__(self, decision: AccessDecision) -> None:
        self.decision = decision
        self.seen: list[int] = []

    async def decision_for(self, telegram_id: int, username: str | None = None) -> AccessDecision:
        self.seen.append(telegram_id)
        return self.decision


class JobsStub:
    async def new_draft(self, *_: object) -> None:
        return None

    async def user_jobs(self, _: int) -> list[object]:
        return [type("Job", (), {"id": "abcdefgh", "status": "queued", "stage": "waiting"})()]

    async def save_text(self, _: int, __: str) -> object:
        return type(
            "Draft",
            (),
            {
                "id": "draft",
                "revision": 1,
                "plugin_id": "text_card",
                "text": "hello",
                "options_json": '{"background":"#15182b"}',
            },
        )()

    async def submit(self, *_: object) -> object:
        return type(
            "Job", (), {"id": "abcdefgh", "plugin_id": "text_card", "status_message_id": None}
        )()

    async def set_status_message(self, *_: object) -> None:
        return None


async def test_dispatcher_answers_private_commands_without_network() -> None:
    session = RecordingSession()
    bot = Bot(token="123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi", session=session)
    access = AccessStub(AccessDecision.OWNER)
    dispatcher = app.build_dispatcher(access, {"text_card"})  # type: ignore[arg-type]

    for update_id, text in enumerate(("/whoami", "/start", "/tools", "/help", "hello"), start=1):
        message = Message(
            message_id=update_id,
            date=datetime.now(),
            chat=Chat(id=1, type="private"),
            from_user=User(id=7, is_bot=False, first_name="Tester", username="tester"),
            text=text,
        )
        await dispatcher.feed_update(bot, Update(update_id=update_id, message=message))

    texts = [method.text for method in session.methods]
    assert any("Telegram ID" in text for text in texts)
    assert any("Добро пожаловать" in text for text in texts)
    assert any("Текстовая карточка" in text for text in texts)
    assert any("/tools" in text for text in texts)
    assert any("Используйте /start" in text for text in texts)
    await bot.session.close()


class PresetJobsStub:
    def __init__(self) -> None:
        self.updated: list[dict[str, object]] = []
        self.draft = SimpleNamespace(
            id="draft",
            revision=1,
            plugin_id="glamour_letters",
            text="ЁЖ",
            options_json='{"preset":"gold_lounge"}',
        )

    async def get_draft(self, user_id: int, draft_id: str):
        return self.draft if user_id == 7 and draft_id == "draft" else None

    async def update_options(
        self, user_id: int, draft_id: str, updates: dict[str, object], expected_revision: int
    ):
        import json

        assert expected_revision == self.draft.revision
        self.updated.append(updates)
        self.draft.revision += 1
        self.draft.options_json = json.dumps(updates)
        return self.draft


@pytest.mark.parametrize(
    "data,user_id,chat_type,allowed,changed",
    [
        ("preset:draft:1:diamond", 7, "private", True, True),
        ("preset:draft:0:diamond", 7, "private", True, False),
        ("preset:draft:1:red8", 7, "private", True, False),
        ("preset:draft:1:no-such-preset", 7, "private", True, False),
        ("preset:draft:1:diamond", 8, "private", True, False),
        ("preset:draft:1:diamond", 7, "group", True, False),
        ("preset:draft:1:diamond", 7, "private", False, False),
        ("preset:draft:diamond", 7, "private", True, False),
        ("settings:draft:1", 7, "private", True, False),
    ],
)
async def test_presets_are_scoped_and_refresh_confirmation(
    data, user_id, chat_type, allowed, changed
) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi", session=session)
    jobs = PresetJobsStub()
    access = AccessStub(AccessDecision.OWNER if allowed else AccessDecision.DENIED)
    dispatcher = app.build_dispatcher(access, {"glamour_letters"}, jobs)  # type: ignore[arg-type]
    callback = CallbackQuery(
        id="callback",
        from_user=User(id=user_id, is_bot=False, first_name="Test"),
        chat_instance="chat",
        data=data,
        message=Message(message_id=4, date=datetime.now(), chat=Chat(id=1, type=chat_type)),
    )
    await dispatcher.feed_update(bot, Update(update_id=1, callback_query=callback))
    assert bool(jobs.updated) is changed
    if changed:
        messages = [method for method in session.methods if getattr(method, "reply_markup", None)]
        assert "Бриллиантовая ночь" in messages[-1].text
        assert messages[-1].reply_markup.inline_keyboard[0][0].callback_data == "create:draft:2"
    await bot.session.close()


async def test_dispatcher_denies_unapproved_user() -> None:
    session = RecordingSession()
    bot = Bot(token="123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi", session=session)
    dispatcher = app.build_dispatcher(AccessStub(AccessDecision.DENIED), {"text_card"})  # type: ignore[arg-type]
    message = Message(
        message_id=1,
        date=datetime.now(),
        chat=Chat(id=1, type="private"),
        from_user=User(id=7, is_bot=False, first_name="Tester"),
        text="/start",
    )
    await dispatcher.feed_update(bot, Update(update_id=1, message=message))
    assert "не одобрен" in session.methods[-1].text
    await bot.session.close()


async def test_dispatcher_creates_draft_and_job() -> None:
    session = RecordingSession()
    bot = Bot(token="123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi", session=session)
    dispatcher = app.build_dispatcher(AccessStub(AccessDecision.OWNER), {"text_card"}, JobsStub())  # type: ignore[arg-type]
    user = User(id=7, is_bot=False, first_name="Tester")
    chat = Chat(id=1, type="private")
    for update_id, text in enumerate(("/new text_card", "hello", "/jobs"), start=1):
        await dispatcher.feed_update(
            bot,
            Update(
                update_id=update_id,
                message=Message(
                    message_id=update_id, date=datetime.now(), chat=chat, from_user=user, text=text
                ),
            ),
        )
    callback = CallbackQuery(
        id="callback",
        from_user=user,
        chat_instance="chat",
        data="create:draft:1",
        message=Message(message_id=4, date=datetime.now(), chat=chat, from_user=user, text="hello"),
    )
    await dispatcher.feed_update(bot, Update(update_id=4, callback_query=callback))
    texts = [method.text for method in session.methods if hasattr(method, "text")]
    assert any("Отправьте текст" in text for text in texts)
    assert any("Проверьте данные" in text for text in texts)
    assert any("abcdefgh" in text for text in texts)
    await bot.session.close()
