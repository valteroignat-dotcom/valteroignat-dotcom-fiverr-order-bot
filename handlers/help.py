"""Команда /help и общий ответ на неизвестные сообщения."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from keyboards import main_menu_kb

router = Router(name="help")


HELP_TEXT = (
    "ℹ️ <b>Команды бота</b>\n\n"
    "/start — приветствие и меню.\n"
    "/profile — настроить или посмотреть профиль.\n"
    "/keywords — список ключевых слов и ссылок для поиска заказов на Fiverr.\n"
    "/analyze — отправить описание заказа и получить полный разбор.\n"
    "/score — отправить описание и получить только числовую оценку.\n"
    "/help — это сообщение.\n\n"
    "💡 <b>Как пользоваться</b>\n"
    "1. Заполни профиль через /profile (один раз).\n"
    "2. Ищи заказы на Fiverr по ссылкам из /keywords.\n"
    "3. Понравившийся заказ — скопируй и пришли сюда. Я разберу и предложу отклик.\n"
    "4. Отправь отклик САМ, ничего автоматического я не делаю.\n\n"
    "⚠️ Важно: бот — помощник. Он не парсит Fiverr, не обходит защиту "
    "и не пишет за тебя клиентам. Все правила Fiverr остаются на твоей стороне."
)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML", reply_markup=main_menu_kb)
