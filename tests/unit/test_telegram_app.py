from datetime import datetime
from typing import Any

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
