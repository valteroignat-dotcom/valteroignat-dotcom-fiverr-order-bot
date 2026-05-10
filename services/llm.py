"""Тонкая обёртка над OpenAI-совместимым API.

Если ключ не задан — все функции возвращают разумные fallback-значения,
чтобы бот продолжал работать (показывал rule-based scoring и шаблонный отклик).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from config import BASE_DIR, settings
from models import UserProfile

logger = logging.getLogger(__name__)

# Лениво создаваемый клиент — чтобы не падать при импорте, если ключа нет.
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI | None:
    global _client
    if not settings.llm_enabled:
        return None
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    return _client


def _read_prompt(name: str) -> str:
    """Читает текстовый промпт из папки prompts/."""
    path: Path = BASE_DIR / "prompts" / name
    return path.read_text(encoding="utf-8")


# --- Промпты загружаем один раз при импорте ---
ANALYZE_PROMPT = _read_prompt("analyze_order_prompt.txt")
PROPOSAL_PROMPT = _read_prompt("proposal_prompt.txt")


def _profile_summary(profile: UserProfile | None) -> str:
    """Кратко описывает профиль в формате, удобном для подстановки в промпт."""
    if profile is None:
        return "Profile: not configured (assume beginner generalist)."
    return (
        f"Profile:\n"
        f"- Languages: {profile.languages or 'not set'}\n"
        f"- Experience: {profile.experience_level}\n"
        f"- Task types: {profile.task_types or 'not set'}\n"
        f"- Min budget: ${profile.min_budget}\n"
        f"- Max complexity: {profile.max_complexity}\n"
        f"- Preferred language: {profile.preferred_language}\n"
        f"- Display name: {profile.display_name or 'Freelancer'}\n"
        f"- Portfolio: {profile.portfolio_url or 'not provided'}"
    )


async def analyze_order(order_text: str, profile: UserProfile | None) -> dict[str, Any] | None:
    """Просит LLM проанализировать заказ и вернуть структурированный JSON.

    Возвращает None, если LLM недоступен или ответ нельзя распарсить.
    """
    client = _get_client()
    if client is None:
        return None

    user_prompt = (
        f"{_profile_summary(profile)}\n\n"
        f"Order description:\n\"\"\"\n{order_text.strip()}\n\"\"\""
    )

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": ANALYZE_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
    except Exception as exc:  # noqa: BLE001 — намеренно широкий catch
        logger.warning("LLM analyze_order failed: %s", exc)
        return None

    raw = response.choices[0].message.content or ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON: %s", raw[:200])
        return None


async def generate_proposal(
    order_text: str,
    profile: UserProfile | None,
    analysis: dict[str, Any] | None = None,
) -> str | None:
    """Генерирует короткий черновик отклика. Возвращает None при ошибке."""
    client = _get_client()
    if client is None:
        return None

    context = _profile_summary(profile)
    if analysis:
        context += "\n\nAnalysis JSON:\n" + json.dumps(analysis, ensure_ascii=False)

    user_prompt = (
        f"{context}\n\n"
        f"Order description:\n\"\"\"\n{order_text.strip()}\n\"\"\""
    )

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": PROPOSAL_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM generate_proposal failed: %s", exc)
        return None

    return (response.choices[0].message.content or "").strip() or None
