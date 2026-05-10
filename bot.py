"""Точка входа: запускает aiogram-бота с long polling."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import settings
from database import init_db
from handlers import analyze as analyze_handlers
from handlers import help as help_handlers
from handlers import profile as profile_handlers
from handlers import search as search_handlers
from handlers import start as start_handlers


def _setup_logging() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


async def _set_bot_commands(bot: Bot) -> None:
    """Регистрирует список команд, которые Telegram показывает в меню '/'."""
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="profile", description="Профиль и настройки"),
        BotCommand(command="profile_edit", description="Изменить профиль"),
        BotCommand(command="keywords", description="Ключевые слова для Fiverr"),
        BotCommand(command="search", description="Алиас /keywords"),
        BotCommand(command="analyze", description="Полный разбор заказа"),
        BotCommand(command="score", description="Только оценка заказа 0-100"),
        BotCommand(command="help", description="Помощь"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    _setup_logging()
    logger = logging.getLogger("bot")

    # Создаём БД и таблицы при первом запуске.
    await init_db()
    logger.info("Database initialized")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=None),  # parse_mode задаём в конкретных answer()
    )
    dp = Dispatcher(storage=MemoryStorage())

    # ВАЖНО: порядок include_router задаёт приоритет.
    # Сначала команды, потом FSM-роутеры профиля,
    # и в самом конце analyze (там ловим свободный текст).
    dp.include_router(start_handlers.router)
    dp.include_router(help_handlers.router)
    dp.include_router(search_handlers.router)
    dp.include_router(profile_handlers.router)
    dp.include_router(analyze_handlers.router)

    await _set_bot_commands(bot)

    if not settings.llm_enabled:
        logger.warning(
            "OPENAI_API_KEY не задан — бот работает в режиме без LLM "
            "(rule-based scoring + шаблонный отклик)."
        )

    logger.info("Bot started. Polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
