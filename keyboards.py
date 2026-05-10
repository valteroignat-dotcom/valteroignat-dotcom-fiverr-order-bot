"""Клавиатуры (inline и reply) для всех экранов бота."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# --- Главное меню (reply-клавиатура, всегда внизу экрана) ---

MAIN_MENU_BUTTONS = [
    [KeyboardButton(text="🛠 Настроить профиль"), KeyboardButton(text="🔍 Найти заказы")],
    [KeyboardButton(text="🧪 Проверить описание"), KeyboardButton(text="👤 Мои навыки")],
    [KeyboardButton(text="❓ Помощь")],
]

main_menu_kb = ReplyKeyboardMarkup(
    keyboard=MAIN_MENU_BUTTONS,
    resize_keyboard=True,
    input_field_placeholder="Выбери действие или вставь описание заказа...",
)


# --- Inline-клавиатуры для опросника профиля ---

EXPERIENCE_LEVELS = ["beginner", "junior", "intermediate"]

TASK_TYPES = [
    "bug fixing",
    "HTML/CSS fixes",
    "JavaScript fixes",
    "Python scripts",
    "Telegram bots",
    "automation",
    "WordPress fixes",
    "API integration",
    "AI prompts",
]

COMPLEXITY_LEVELS = ["low", "medium", "high"]


def experience_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=lvl.capitalize(), callback_data=f"exp:{lvl}")]
        for lvl in EXPERIENCE_LEVELS
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def task_types_kb(selected: set[str]) -> InlineKeyboardMarkup:
    """Мульти-выбор типов задач. Галочка показывает уже выбранные."""
    rows = []
    for task in TASK_TYPES:
        mark = "✅ " if task.lower() in selected else "▫️ "
        rows.append(
            [InlineKeyboardButton(text=mark + task, callback_data=f"task:{task}")]
        )
    rows.append(
        [InlineKeyboardButton(text="➡️ Готово", callback_data="task:done")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def complexity_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=lvl.capitalize(), callback_data=f"cx:{lvl}")]
        for lvl in COMPLEXITY_LEVELS
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def language_kb() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        ],
        [InlineKeyboardButton(text="🌐 Both / Other", callback_data="lang:any")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_kb(callback_value: str = "skip") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data=callback_value)]
        ]
    )


# --- Inline-клавиатура для результата анализа ---


def analysis_result_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🔁 Перегенерировать отклик", callback_data="regen_proposal")],
        [InlineKeyboardButton(text="🔍 Поисковые ключи", callback_data="show_keywords")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
