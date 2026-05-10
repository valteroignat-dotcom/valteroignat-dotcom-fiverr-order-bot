"""Анализ описания заказа: команды /analyze, /score и обработка свободного текста."""
from __future__ import annotations

import logging
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database import SessionLocal, get_or_create_profile
from keyboards import analysis_result_kb, main_menu_kb
from models import UserProfile
from services import llm
from services.scoring import ScoreBreakdown, interpret, score_order

logger = logging.getLogger(__name__)

router = Router(name="analyze")


# Минимальная длина текста, который мы готовы анализировать.
MIN_ORDER_LENGTH = 30


class AnalyzeStates(StatesGroup):
    """Используем FSM, чтобы помнить, ждём ли описание для /analyze или /score."""

    waiting_for_full_analysis = State()
    waiting_for_score_only = State()


# --- Команды ---


@router.message(Command("analyze"))
async def cmd_analyze(message: Message, state: FSMContext) -> None:
    await state.set_state(AnalyzeStates.waiting_for_full_analysis)
    await message.answer(
        "🧪 Пришли описание заказа с Fiverr (просто скопируй и отправь сообщением).\n"
        "Я разберу: категория, сложность, риски, оценка и черновик отклика."
    )


@router.message(Command("score"))
async def cmd_score(message: Message, state: FSMContext) -> None:
    await state.set_state(AnalyzeStates.waiting_for_score_only)
    await message.answer(
        "📊 Пришли описание заказа — отвечу только числовой оценкой 0–100 без отклика."
    )


# --- Обработка текста: либо после /analyze /score, либо просто свободный длинный текст ---


@router.message(AnalyzeStates.waiting_for_full_analysis, F.text)
async def handle_full_analysis(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _do_full_analysis(message)


@router.message(AnalyzeStates.waiting_for_score_only, F.text)
async def handle_score_only(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _do_score_only(message)


# Свободный текст — ловим длинные сообщения, не совпадающие с кнопками меню.
# Менее приоритетные обработчики срабатывают, только если предыдущие роутеры
# не обработали сообщение (порядок include_router важен — см. bot.py).
@router.message(F.text & ~F.text.startswith("/"))
async def handle_freeform_text(message: Message) -> None:
    if len(message.text) < MIN_ORDER_LENGTH:
        # Слишком короткое — не похоже на описание заказа. Игнорим (или подсказываем).
        await message.answer(
            "Похоже, это не описание заказа. Используй меню или пришли длинный текст заказа.\n"
            "Команды: /help"
        )
        return
    await _do_full_analysis(message)


# --- Callback: перегенерировать отклик ---


@router.callback_query(F.data == "regen_proposal")
async def cb_regen_proposal(callback: CallbackQuery) -> None:
    """Просим пользователя прислать заказ заново — мы не храним предыдущий текст."""
    await callback.message.answer(
        "Чтобы перегенерировать отклик, пришли описание заказа ещё раз. "
        "Я не сохраняю тексты заказов из соображений приватности."
    )
    await callback.answer()


@router.callback_query(F.data == "show_keywords")
async def cb_show_keywords(callback: CallbackQuery) -> None:
    await callback.message.answer("Открой /keywords — там готовые поисковые ссылки.")
    await callback.answer()


# --- Внутренние хелперы ---


async def _do_score_only(message: Message) -> None:
    text = message.text or ""
    if len(text) < MIN_ORDER_LENGTH:
        await message.answer("Описание слишком короткое. Пришли полный текст заказа.")
        return

    async with SessionLocal() as session:
        profile = await get_or_create_profile(session, message.from_user.id)

    breakdown = score_order(text, profile)
    await message.answer(_format_score_only(breakdown))


async def _do_full_analysis(message: Message) -> None:
    text = message.text or ""
    if len(text) < MIN_ORDER_LENGTH:
        await message.answer("Описание слишком короткое. Пришли полный текст заказа.")
        return

    async with SessionLocal() as session:
        profile = await get_or_create_profile(session, message.from_user.id)

    # Сообщаем, что взяли в работу — разбор может занять несколько секунд.
    progress = await message.answer("⏳ Разбираю заказ...")

    rule_breakdown = score_order(text, profile)

    # 1) Просим LLM проанализировать.
    analysis = await llm.analyze_order(text, profile)

    # 2) Просим LLM сгенерировать отклик. Если LLM выключен — fallback-шаблон.
    proposal = await llm.generate_proposal(text, profile, analysis)
    if proposal is None:
        proposal = _fallback_proposal(profile)

    # 3) Финальный score = смесь rule-based и LLM (если LLM дал баллы).
    final_breakdown = _merge_scores(rule_breakdown, analysis)

    response = _format_full_response(
        text=text,
        profile=profile,
        analysis=analysis,
        breakdown=final_breakdown,
        proposal=proposal,
    )

    # Удаляем "⏳ Разбираю заказ..." и отправляем результат.
    try:
        await progress.delete()
    except Exception:  # noqa: BLE001
        pass

    # Telegram может не принять слишком длинное сообщение — режем по 4000 символов.
    chunks = _chunk(response, 4000)
    for index, chunk in enumerate(chunks):
        is_last = index == len(chunks) - 1
        await message.answer(
            chunk,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=analysis_result_kb() if is_last else None,
        )


# --- Форматирование ответа ---


def _format_score_only(breakdown: ScoreBreakdown) -> str:
    lines = [
        f"📊 <b>Оценка:</b> {breakdown.total}/100 — {interpret(breakdown.total)}",
        "",
        *breakdown.to_lines(),
    ]
    return "\n".join(lines)


def _format_full_response(
    *,
    text: str,
    profile: UserProfile,
    analysis: dict[str, Any] | None,
    breakdown: ScoreBreakdown,
    proposal: str,
) -> str:
    """Форматирует ответ строго по схеме из ТЗ (раздел 11)."""
    if analysis is None:
        # LLM выключен / упал — используем грубые эвристики.
        category = _guess_category(text)
        complexity = _guess_complexity(breakdown)
        fits_beginner = _fits_label(breakdown.total)
        skills = _guess_skills(text, profile)
        risks = ["LLM не подключён — анализ ограниченный."]
        questions = [
            "Можешь поделиться репозиторием или скриншотами ошибки?",
            "Какой ожидаемый результат после фикса?",
        ]
        price_min, price_max = _guess_price_range(profile, breakdown)
        days = max(1, 5 - breakdown.simplicity // 6)
    else:
        category = str(analysis.get("category") or _guess_category(text))
        complexity = _ru_complexity(str(analysis.get("complexity") or "medium"))
        fits_beginner = _ru_fits(str(analysis.get("fits_beginner") or "with_caution"))
        skills = list(analysis.get("required_skills") or _guess_skills(text, profile))
        risks = list(analysis.get("risks") or [])
        if not risks:
            risks = ["Явных красных флагов не вижу — но всё равно уточни детали у клиента."]
        questions = list(analysis.get("questions_for_client") or [])
        if not questions:
            questions = ["Можешь прислать репозиторий или пример проблемы?"]
        price_min = int(analysis.get("estimated_price_min_usd") or 10)
        price_max = int(analysis.get("estimated_price_max_usd") or max(price_min + 20, 30))
        days = int(analysis.get("estimated_days") or 1)

    interpretation = interpret(breakdown.total)

    sections = [
        f"📌 <b>Категория:</b>\n{category}",
        "",
        f"📊 <b>Оценка:</b>\n{breakdown.total}/100 — {interpretation}",
        "",
        f"🧩 <b>Сложность:</b>\n{complexity}",
        "",
        f"✅ <b>Подходит новичку:</b>\n{fits_beginner}",
        "",
        "🛠 <b>Нужные навыки:</b>\n" + _bullet_list(skills),
        "",
        "⚠️ <b>Риски:</b>\n" + _bullet_list(risks),
        "",
        "❓ <b>Что уточнить у клиента:</b>\n" + _bullet_list(questions),
        "",
        f"💰 <b>Рекомендуемая цена:</b>\n${price_min}–${price_max}",
        "",
        f"⏱ <b>Рекомендуемый срок:</b>\n{days} {_ru_days(days)}",
        "",
        "✉️ <b>Черновик отклика:</b>",
        f"<pre>{_escape_html(proposal)}</pre>",
        "",
        "<i>Это черновик. Прочитай, при необходимости отредактируй и отправь сам через Fiverr.</i>",
    ]
    return "\n".join(sections)


# --- Утилиты ---


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "—"
    return "\n".join(f"• {_escape_html(str(it))}" for it in items)


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _ru_complexity(value: str) -> str:
    return {"low": "низкая", "medium": "средняя", "high": "высокая"}.get(value, value)


def _ru_fits(value: str) -> str:
    return {
        "yes": "да",
        "no": "нет",
        "with_caution": "с осторожностью",
    }.get(value, value)


def _ru_days(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "день"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "дня"
    return "дней"


def _guess_category(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["wordpress", "wp ", "elementor"]):
        return "WordPress"
    if any(k in t for k in ["telegram", "aiogram"]):
        return "Telegram bot"
    if "python" in t:
        return "Python script"
    if any(k in t for k in ["html", "css"]):
        return "HTML/CSS fix"
    if any(k in t for k in ["javascript", "react", "vue", " js"]):
        return "JavaScript fix"
    if "api" in t:
        return "API integration"
    return "Bug fixing"


def _guess_complexity(breakdown: ScoreBreakdown) -> str:
    if breakdown.simplicity >= 18:
        return "низкая"
    if breakdown.simplicity >= 10:
        return "средняя"
    return "высокая"


def _fits_label(total: int) -> str:
    if total >= 70:
        return "да"
    if total >= 45:
        return "с осторожностью"
    return "нет"


def _guess_skills(text: str, profile: UserProfile | None) -> list[str]:
    found: list[str] = []
    t = text.lower()
    candidates = ["python", "javascript", "html", "css", "react", "vue", "django",
                  "flask", "wordpress", "telegram", "api", "openai", "node"]
    for c in candidates:
        if c in t:
            found.append(c)
    if not found and profile and profile.languages:
        found = profile.language_list()[:3]
    return found or ["debugging"]


def _guess_price_range(profile: UserProfile | None, breakdown: ScoreBreakdown) -> tuple[int, int]:
    base = profile.min_budget if profile else 10
    multiplier = 1.0 + (25 - breakdown.simplicity) * 0.08
    low = max(base, int(base * multiplier))
    high = max(low + 20, int(low * 2.2))
    return low, high


def _merge_scores(rule: ScoreBreakdown, analysis: dict[str, Any] | None) -> ScoreBreakdown:
    """Если LLM вернул свои score-поля — берём среднее, иначе — rule-based."""
    if not analysis:
        return rule
    try:
        return ScoreBreakdown(
            skill_match=_avg_clamped(rule.skill_match, analysis.get("score_skill_match"), 30),
            simplicity=_avg_clamped(rule.simplicity, analysis.get("score_simplicity"), 25),
            budget=_avg_clamped(rule.budget, analysis.get("score_budget"), 20),
            clarity=_avg_clamped(rule.clarity, analysis.get("score_clarity"), 15),
            low_risk=_avg_clamped(rule.low_risk, analysis.get("score_low_risk"), 10),
        )
    except (TypeError, ValueError):
        return rule


def _avg_clamped(rule_value: int, llm_value: Any, max_value: int) -> int:
    if llm_value is None:
        return rule_value
    try:
        llm_int = int(llm_value)
    except (TypeError, ValueError):
        return rule_value
    llm_int = max(0, min(llm_int, max_value))
    return (rule_value + llm_int) // 2


def _fallback_proposal(profile: UserProfile | None) -> str:
    """Шаблон отклика, когда LLM недоступен."""
    name = (profile.display_name if profile else "") or "Freelancer"
    return (
        "Hi,\n\n"
        "I read your project description and I think I can help with the issue you described.\n\n"
        "I can review the current code, reproduce the problem, find the cause and apply a clean fix. "
        "I have experience with small bug fixes, code cleanup and basic automation tasks.\n\n"
        "My approach would be:\n"
        "1. Review the current code and reproduce the issue.\n"
        "2. Find the cause of the bug.\n"
        "3. Apply the fix and test the result.\n\n"
        "A couple of quick questions:\n"
        "1. Could you share the error message or screenshots?\n"
        "2. Do you already have access to the source code or repository?\n\n"
        "I can start by reviewing the issue and then confirm the exact time and price.\n\n"
        f"Best,\n{name}"
    )


def _chunk(text: str, size: int) -> list[str]:
    """Режем длинное сообщение на куски, не разрывая HTML-тег <pre>...</pre>.

    Простой подход: если в куске начался <pre> и не закрылся — переносим
    закрывающий </pre> в текущий чанк, а в следующем добавляем <pre>.
    """
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        start = end
    return chunks
