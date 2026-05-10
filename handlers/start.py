"""Стартовое меню и главные кнопки навигации."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from keyboards import main_menu_kb

router = Router(name="start")


WELCOME_TEXT = (
    "👋 Привет! Я помогаю начинающим фрилансерам искать простые заказы на Fiverr.\n\n"
    "Что я умею:\n"
    "• 🛠 Запоминать твой профиль (навыки, бюджет, предпочтения).\n"
    "• 🔍 Давать готовые поисковые ссылки и ключевые слова.\n"
    "• 🧪 Анализировать описания заказов, которые ты вставишь сюда.\n"
    "• 📊 Давать оценку 0–100, подходит ли заказ новичку.\n"
    "• ✉️ Готовить честный черновик отклика — ты отправишь его сам.\n\n"
    "⚠️ Я НЕ парсю Fiverr и НЕ отвечаю клиентам автоматически. "
    "Финальное решение всегда за тобой.\n\n"
    "Выбери действие в меню или просто пришли мне текст заказа."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb)


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await message.answer("Главное меню 👇", reply_markup=main_menu_kb)


# --- Reply-кнопки главного меню. Они просто запускают соответствующие команды. ---


@router.message(F.text == "🛠 Настроить профиль")
async def btn_profile(message: Message) -> None:
    # Делегируем команде /profile (она реализована в handlers/profile.py).
    await message.answer("Открываю настройки профиля... используй /profile")


@router.message(F.text == "🔍 Найти заказы")
async def btn_search(message: Message) -> None:
    await message.answer("Открываю поисковые ключи... используй /keywords")


@router.message(F.text == "🧪 Проверить описание")
async def btn_analyze(message: Message) -> None:
    await message.answer(
        "Пришли мне текст заказа с Fiverr (просто скопируй и отправь сообщением), "
        "и я разберу его. Или используй /analyze."
    )


@router.message(F.text == "👤 Мои навыки")
async def btn_my_skills(message: Message) -> None:
    await message.answer("Покажу твой профиль... используй /profile")


@router.message(F.text == "❓ Помощь")
async def btn_help(message: Message) -> None:
    await message.answer("Команды и пояснения... используй /help")
