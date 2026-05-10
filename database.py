"""Инициализация async SQLAlchemy и набор простых CRUD-функций.

Используем async-движок поверх aiosqlite. Этого достаточно для одного
Telegram-бота и сотен пользователей — без отдельного сервера БД.
"""
from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings
from models import Base, UserProfile

# Один движок и одна фабрика сессий на всё приложение.
engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


async def init_db() -> None:
    """Создаёт таблицы при первом запуске."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Контекстный генератор сессий (для зависимостей/handler'ов)."""
    async with SessionLocal() as session:
        yield session


# --- CRUD для профиля ---


async def get_profile(session: AsyncSession, user_id: int) -> UserProfile | None:
    return await session.get(UserProfile, user_id)


async def get_or_create_profile(session: AsyncSession, user_id: int) -> UserProfile:
    profile = await get_profile(session, user_id)
    if profile is None:
        profile = UserProfile(user_id=user_id)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
    return profile


async def update_profile(session: AsyncSession, user_id: int, **fields) -> UserProfile:
    """Универсальный апдейт: проставляем только переданные поля."""
    profile = await get_or_create_profile(session, user_id)
    for key, value in fields.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    await session.commit()
    await session.refresh(profile)
    return profile
