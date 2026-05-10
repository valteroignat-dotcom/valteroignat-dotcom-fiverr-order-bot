"""Конфигурация бота: загрузка переменных окружения из .env."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Корень проекта (нужен для путей к промптам и SQLite-файлу).
BASE_DIR = Path(__file__).resolve().parent

# Загружаем .env из корня проекта, если он существует.
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    """Все настройки приложения в одном месте."""

    bot_token: str
    openai_api_key: str | None
    openai_base_url: str
    openai_model: str
    database_url: str
    log_level: str

    @property
    def llm_enabled(self) -> bool:
        """LLM включён, только если задан API-ключ."""
        return bool(self.openai_api_key)


def _get_env(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(
            f"Не задана обязательная переменная окружения {name}. "
            f"Скопируй .env.example в .env и заполни значения."
        )
    return value or ""


def load_settings() -> Settings:
    """Собирает Settings из переменных окружения."""
    return Settings(
        bot_token=_get_env("BOT_TOKEN", required=True),
        openai_api_key=_get_env("OPENAI_API_KEY") or None,
        openai_base_url=_get_env("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openai_model=_get_env("OPENAI_MODEL", "gpt-4o-mini"),
        database_url=_get_env("DATABASE_URL", "sqlite+aiosqlite:///bot.db"),
        log_level=_get_env("LOG_LEVEL", "INFO"),
    )


# Глобальный экземпляр настроек, который импортируют другие модули.
settings = load_settings()
