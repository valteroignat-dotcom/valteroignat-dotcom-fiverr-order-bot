"""ORM-модели SQLAlchemy 2.x.

Храним только профиль пользователя: бот не агрегирует и не сохраняет
заказы Fiverr (это могло бы нарушать ToS платформы).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""


class UserProfile(Base):
    """Профиль фрилансера: что умеет, какие заказы интересуют, бюджет и т.д.

    Поля-списки (languages, task_types) хранятся как строки с разделителем `,`,
    чтобы не плодить лишних таблиц для простого MVP.
    """

    __tablename__ = "user_profiles"

    # Telegram user_id уникален и хорошо подходит как первичный ключ.
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # Языки программирования, через запятую: "python,javascript,html".
    languages: Mapped[str] = mapped_column(String(512), default="")

    # beginner / junior / intermediate
    experience_level: Mapped[str] = mapped_column(String(32), default="beginner")

    # Типы задач, через запятую: "bug fixing,html css fixes,...".
    task_types: Mapped[str] = mapped_column(String(1024), default="")

    # Минимальный бюджет в долларах.
    min_budget: Mapped[int] = mapped_column(Integer, default=10)

    # Максимальная сложность: low / medium / high.
    max_complexity: Mapped[str] = mapped_column(String(16), default="medium")

    # Предпочитаемый язык общения с клиентом.
    preferred_language: Mapped[str] = mapped_column(String(16), default="en")

    # Имя для подписи в отклике (можно отличаться от Telegram-имени).
    display_name: Mapped[str] = mapped_column(String(64), default="")

    # Ссылка на портфолио, опционально.
    portfolio_url: Mapped[str] = mapped_column(String(512), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # --- Удобные хелперы для работы со списочными полями. ---

    def language_list(self) -> list[str]:
        return [s.strip().lower() for s in self.languages.split(",") if s.strip()]

    def task_type_list(self) -> list[str]:
        return [s.strip().lower() for s in self.task_types.split(",") if s.strip()]
