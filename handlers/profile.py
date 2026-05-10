"""Опросник профиля пользователя на FSM.

Шаги:
1. languages — текстом, через запятую
2. experience_level — кнопками
3. task_types — мульти-выбор кнопками
4. min_budget — числом
5. max_complexity — кнопками
6. preferred_language — кнопками
7. display_name — текстом
8. portfolio_url — текстом или "Пропустить"
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database import SessionLocal, get_or_create_profile, update_profile
from keyboards import (
    EXPERIENCE_LEVELS,
    TASK_TYPES,
    complexity_kb,
    experience_kb,
    language_kb,
    main_menu_kb,
    skip_kb,
    task_types_kb,
)

router = Router(name="profile")


class ProfileStates(StatesGroup):
    """Состояния FSM для пошаговой настройки профиля."""

    languages = State()
    experience = State()
    task_types = State()
    min_budget = State()
    max_complexity = State()
    preferred_language = State()
    display_name = State()
    portfolio_url = State()


# --- Просмотр текущего профиля ---


def _format_profile(profile) -> str:
    return (
        "👤 <b>Твой профиль</b>\n\n"
        f"• Языки: {profile.languages or '—'}\n"
        f"• Опыт: {profile.experience_level}\n"
        f"• Типы задач: {profile.task_types or '—'}\n"
        f"• Мин. бюджет: ${profile.min_budget}\n"
        f"• Макс. сложность: {profile.max_complexity}\n"
        f"• Язык общения: {profile.preferred_language}\n"
        f"• Имя для отклика: {profile.display_name or '—'}\n"
        f"• Портфолио: {profile.portfolio_url or '—'}\n\n"
        "Чтобы изменить — пришли /profile_edit."
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext) -> None:
    """Показывает профиль или запускает опросник, если он пустой."""
    await state.clear()
    async with SessionLocal() as session:
        profile = await get_or_create_profile(session, message.from_user.id)

    if not profile.languages and not profile.task_types:
        # Профиль пустой — сразу запускаем опросник.
        await _start_questionnaire(message, state)
    else:
        await message.answer(_format_profile(profile), parse_mode="HTML")


@router.message(Command("profile_edit"))
async def cmd_profile_edit(message: Message, state: FSMContext) -> None:
    await _start_questionnaire(message, state)


async def _start_questionnaire(message: Message, state: FSMContext) -> None:
    await state.set_state(ProfileStates.languages)
    await message.answer(
        "Шаг 1/8. Какие языки программирования ты знаешь?\n"
        "Перечисли через запятую, например: <code>python, javascript, html, css</code>",
        parse_mode="HTML",
    )


# --- Шаг 1: языки ---


@router.message(ProfileStates.languages, F.text)
async def step_languages(message: Message, state: FSMContext) -> None:
    languages = ", ".join(
        s.strip().lower() for s in message.text.split(",") if s.strip()
    )
    await state.update_data(languages=languages)
    await state.set_state(ProfileStates.experience)
    await message.answer(
        "Шаг 2/8. Какой у тебя уровень опыта?",
        reply_markup=experience_kb(),
    )


# --- Шаг 2: опыт ---


@router.callback_query(ProfileStates.experience, F.data.startswith("exp:"))
async def step_experience(callback: CallbackQuery, state: FSMContext) -> None:
    level = callback.data.split(":", 1)[1]
    if level not in EXPERIENCE_LEVELS:
        await callback.answer("Неизвестный уровень")
        return

    await state.update_data(experience_level=level, selected_tasks=set())
    await state.set_state(ProfileStates.task_types)
    await callback.message.edit_text(
        "Шаг 3/8. Отметь типы задач, которые тебе интересны.\n"
        "Можно выбрать несколько. Когда закончишь — нажми «Готово».",
        reply_markup=task_types_kb(set()),
    )
    await callback.answer()


# --- Шаг 3: типы задач (мульти-выбор) ---


@router.callback_query(ProfileStates.task_types, F.data.startswith("task:"))
async def step_task_types(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected: set[str] = set(data.get("selected_tasks", set()))

    if value == "done":
        if not selected:
            await callback.answer("Выбери хотя бы один тип задач", show_alert=True)
            return
        task_types = ", ".join(sorted(selected))
        await state.update_data(task_types=task_types, selected_tasks=None)
        await state.set_state(ProfileStates.min_budget)
        await callback.message.edit_text(
            "Шаг 4/8. Какой минимальный бюджет тебе интересен (в долларах)?\n"
            "Просто пришли число, например: <code>15</code>",
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Toggle выбора
    task_lower = value.lower()
    if task_lower in selected:
        selected.remove(task_lower)
    elif value in TASK_TYPES:
        selected.add(task_lower)
    await state.update_data(selected_tasks=selected)

    await callback.message.edit_reply_markup(reply_markup=task_types_kb(selected))
    await callback.answer()


# --- Шаг 4: мин. бюджет ---


@router.message(ProfileStates.min_budget, F.text)
async def step_min_budget(message: Message, state: FSMContext) -> None:
    raw = message.text.replace("$", "").replace(" ", "").strip()
    try:
        budget = max(0, int(raw))
    except ValueError:
        await message.answer("Нужно прислать число, например: 15")
        return

    await state.update_data(min_budget=budget)
    await state.set_state(ProfileStates.max_complexity)
    await message.answer(
        "Шаг 5/8. Какая максимальная сложность задачи тебе ок?",
        reply_markup=complexity_kb(),
    )


# --- Шаг 5: макс. сложность ---


@router.callback_query(ProfileStates.max_complexity, F.data.startswith("cx:"))
async def step_max_complexity(callback: CallbackQuery, state: FSMContext) -> None:
    level = callback.data.split(":", 1)[1]
    await state.update_data(max_complexity=level)
    await state.set_state(ProfileStates.preferred_language)
    await callback.message.edit_text(
        "Шаг 6/8. На каком языке ты хочешь общаться с клиентом?",
        reply_markup=language_kb(),
    )
    await callback.answer()


# --- Шаг 6: язык общения ---


@router.callback_query(ProfileStates.preferred_language, F.data.startswith("lang:"))
async def step_preferred_language(callback: CallbackQuery, state: FSMContext) -> None:
    lang = callback.data.split(":", 1)[1]
    await state.update_data(preferred_language=lang)
    await state.set_state(ProfileStates.display_name)
    await callback.message.edit_text(
        "Шаг 7/8. Какое имя подставлять в подпись отклика?\n"
        "Например: <code>Ivan</code> или <code>Ignat</code>",
        parse_mode="HTML",
    )
    await callback.answer()


# --- Шаг 7: имя ---


@router.message(ProfileStates.display_name, F.text)
async def step_display_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()[:64]
    await state.update_data(display_name=name)
    await state.set_state(ProfileStates.portfolio_url)
    await message.answer(
        "Шаг 8/8. Пришли ссылку на портфолио (GitHub / личный сайт), "
        "если есть — или нажми «Пропустить».",
        reply_markup=skip_kb("portfolio:skip"),
    )


# --- Шаг 8: портфолио (текст или skip) ---


@router.message(ProfileStates.portfolio_url, F.text)
async def step_portfolio_url(message: Message, state: FSMContext) -> None:
    url = message.text.strip()[:512]
    await _finish_profile(message, state, portfolio_url=url)


@router.callback_query(ProfileStates.portfolio_url, F.data == "portfolio:skip")
async def step_portfolio_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await _finish_profile(callback.message, state, portfolio_url="", chat_id=callback.from_user.id)
    await callback.answer()


async def _finish_profile(
    message: Message,
    state: FSMContext,
    *,
    portfolio_url: str,
    chat_id: int | None = None,
) -> None:
    """Сохраняет накопленный state в БД и завершает FSM."""
    data = await state.get_data()
    user_id = chat_id if chat_id is not None else message.from_user.id

    fields = {
        "languages": data.get("languages", ""),
        "experience_level": data.get("experience_level", "beginner"),
        "task_types": data.get("task_types", ""),
        "min_budget": data.get("min_budget", 10),
        "max_complexity": data.get("max_complexity", "medium"),
        "preferred_language": data.get("preferred_language", "en"),
        "display_name": data.get("display_name", ""),
        "portfolio_url": portfolio_url,
    }

    async with SessionLocal() as session:
        profile = await update_profile(session, user_id, **fields)

    await state.clear()
    await message.answer(
        "✅ Профиль сохранён!\n\n" + _format_profile(profile),
        parse_mode="HTML",
        reply_markup=main_menu_kb,
    )
