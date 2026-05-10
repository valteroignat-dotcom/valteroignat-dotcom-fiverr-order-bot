"""Списки ключевых слов и хелперы для безопасного поиска заказов на Fiverr.

Бот НЕ парсит Fiverr и НЕ обходит защиту. Он только формирует ссылки,
которые пользователь открывает вручную в браузере.
"""
from __future__ import annotations

from urllib.parse import quote_plus

# Базовые ключевые слова, которые подходят для начинающего разработчика.
# Сгруппированы по категориям, чтобы пользователю было удобно ориентироваться.
BEGINNER_KEYWORDS: dict[str, list[str]] = {
    "Bug fixing": [
        "fix bug",
        "fix python script",
        "fix javascript bug",
        "fix small bug",
        "debug code",
    ],
    "HTML/CSS/JS": [
        "html css fix",
        "css bug fix",
        "responsive fix",
        "javascript bug fix",
        "small frontend fix",
    ],
    "Python / Automation": [
        "fix python script",
        "small python script",
        "python automation",
        "scraping fix",
        "small automation task",
    ],
    "Telegram / Bots": [
        "telegram bot fix",
        "small telegram bot",
        "fix discord bot",
    ],
    "WordPress": [
        "wordpress bug fix",
        "wordpress small fix",
        "fix wordpress error",
    ],
    "API / Integrations": [
        "api integration fix",
        "fix api request",
        "webhook fix",
    ],
    "AI / Prompts": [
        "fix chatgpt prompt",
        "prompt engineering small task",
        "openai api fix",
    ],
}


def fiverr_search_url(query: str) -> str:
    """Возвращает прямую ссылку на поиск Fiverr по ключевому слову.

    Пример: fiverr_search_url("fix python script") -> ...
        https://www.fiverr.com/search/gigs?query=fix+python+script
    """
    return f"https://www.fiverr.com/search/gigs?query={quote_plus(query)}"


def fiverr_buyer_requests_url(query: str) -> str:
    """Ссылка на раздел Buyer Requests (нужен аккаунт продавца).

    Этот URL даёт лучшие шансы найти простые заказы для новичка.
    """
    return f"https://www.fiverr.com/search/gigs?source=top-bar&search_in=everywhere&query={quote_plus(query)}"


def all_keywords_flat() -> list[str]:
    """Плоский список всех ключевиков для команды /keywords."""
    seen: set[str] = set()
    result: list[str] = []
    for kws in BEGINNER_KEYWORDS.values():
        for kw in kws:
            if kw not in seen:
                seen.add(kw)
                result.append(kw)
    return result
