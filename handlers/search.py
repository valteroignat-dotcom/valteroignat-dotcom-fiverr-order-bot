"""Команды для поиска заказов: /keywords и /search.

Бот не парсит Fiverr — только формирует ссылки для ручного открытия.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from services.fiverr_keywords import (
    BEGINNER_KEYWORDS,
    fiverr_search_url,
)

router = Router(name="search")


def _build_keywords_message() -> str:
    """Готовит текст со ссылками. Telegram ограничивает 4096 символов на сообщение —
    обычно укладываемся, но если нет, можно разбить на несколько частей."""
    lines: list[str] = [
        "🔍 <b>Готовые поисковые запросы для Fiverr</b>\n",
        "Открывай ссылки в браузере и листай результаты вручную. ",
        "Бот <b>не</b> парсит Fiverr автоматически — это нарушает ToS.\n",
    ]
    for category, keywords in BEGINNER_KEYWORDS.items():
        lines.append(f"\n<b>{category}</b>")
        for kw in keywords:
            url = fiverr_search_url(kw)
            lines.append(f"• <a href=\"{url}\">{kw}</a>")
    lines.append(
        "\n\n💡 Совет: сначала фильтруй по 'Online sellers' и 'Budget',"
        " чтобы не тратить время на нерелевантные предложения."
    )
    return "\n".join(lines)


@router.message(Command("keywords"))
async def cmd_keywords(message: Message) -> None:
    text = _build_keywords_message()
    # disable_web_page_preview=True, чтобы Telegram не загружал превью каждой ссылки.
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("search"))
async def cmd_search(message: Message) -> None:
    """Алиас на /keywords для удобства."""
    await cmd_keywords(message)
