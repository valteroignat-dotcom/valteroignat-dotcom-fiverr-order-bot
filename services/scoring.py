"""Rule-based оценка заказа от 0 до 100.

Эта функция работает БЕЗ LLM и используется как:
1) бейзлайн (если OpenAI-ключ не задан);
2) предохранитель против галлюцинаций модели — финальный score
   формируется как смесь rule-based и LLM-оценки.

Критерии (как в ТЗ):
- Совпадение с навыками пользователя: до 30 баллов
- Простота задачи: до 25 баллов
- Адекватность бюджета: до 20 баллов
- Ясность требований: до 15 баллов
- Низкий риск: до 10 баллов
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from models import UserProfile

# --- Словари сигналов в тексте заказа. Намеренно простые, чтобы было легко расширять. ---

# Ключевые слова, которые соответствуют конкретным типам задач из профиля.
TASK_KEYWORDS: dict[str, list[str]] = {
    "bug fixing": ["bug", "fix", "error", "issue", "broken", "not working", "crash"],
    "html/css fixes": ["html", "css", "layout", "responsive", "ui", "frontend", "tailwind"],
    "javascript fixes": ["javascript", "js", "react", "vue", "node", "typescript", "jquery"],
    "python scripts": ["python", "django", "flask", "fastapi", "pandas", "script"],
    "telegram bots": ["telegram", "telebot", "aiogram", "bot api"],
    "automation": ["automation", "automate", "selenium", "scrap", "schedule", "cron"],
    "wordpress fixes": ["wordpress", "wp", "elementor", "woocommerce", "plugin"],
    "api integration": ["api", "rest", "webhook", "integration", "endpoint", "graphql"],
    "ai prompts": ["chatgpt", "openai", "prompt", "llm", "gpt", "anthropic", "claude"],
}

# Маркеры сложности задачи.
HIGH_COMPLEXITY_MARKERS = [
    "machine learning",
    "neural network",
    "blockchain",
    "smart contract",
    "kubernetes",
    "scalable",
    "microservices",
    "distributed",
    "high load",
    "production grade",
    "from scratch",
    "full stack",
    "build a complete",
    "architecture",
    "deep learning",
    "computer vision",
    "ios app",
    "android app",
    "native app",
]

LOW_COMPLEXITY_MARKERS = [
    "small fix",
    "simple",
    "quick fix",
    "minor",
    "small bug",
    "small task",
    "tiny",
    "one line",
    "just need",
    "easy",
    "rename",
    "change color",
    "change text",
]

# Маркеры, говорящие о высокой ясности требований.
CLARITY_MARKERS = [
    "github",
    "repo",
    "screenshot",
    "error message",
    "stack trace",
    "log",
    "example",
    "expected",
    "actual",
    "step",
    "reproduce",
]

# Маркеры рисков (плохие признаки заказа).
RISK_MARKERS = [
    "urgent",
    "asap",
    "right now",
    "in 1 hour",
    "in one hour",
    "milestone payment after",
    "pay after",
    "no budget",
    "low budget",
    "long term unpaid",
    "test task",
    "trial task",
    "ndа",  # ошибочный латин-кириллический mix встречается
    "nda required upfront",
    "send me your code",
    "outside fiverr",
    "telegram me",
    "whatsapp me",
    "skype me",
]


@dataclass
class ScoreBreakdown:
    """Подробная разбивка оценки — удобно показывать пользователю."""

    skill_match: int
    simplicity: int
    budget: int
    clarity: int
    low_risk: int

    @property
    def total(self) -> int:
        return self.skill_match + self.simplicity + self.budget + self.clarity + self.low_risk

    def to_lines(self) -> list[str]:
        return [
            f"• Совпадение с навыками: {self.skill_match}/30",
            f"• Простота задачи: {self.simplicity}/25",
            f"• Адекватность бюджета: {self.budget}/20",
            f"• Ясность требований: {self.clarity}/15",
            f"• Низкий риск: {self.low_risk}/10",
        ]


def _extract_budget(text: str) -> int | None:
    """Грубо вытаскивает первую сумму в долларах из текста.

    Поддерживает форматы: $50, 50$, USD 50, 50 usd, 50 dollars.
    """
    patterns = [
        r"\$\s*(\d{1,5})",
        r"(\d{1,5})\s*\$",
        r"(\d{1,5})\s*(?:usd|dollars|bucks)",
        r"(?:budget|pay|price)[^\d]{0,15}(\d{1,5})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue
    return None


def _count_hits(text: str, markers: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for marker in markers if marker in text_lower)


def _skill_match_score(text: str, profile: UserProfile | None) -> int:
    if profile is None:
        return 12  # нейтральный середняк, если профиля нет
    text_lower = text.lower()
    selected_tasks = set(profile.task_type_list())
    languages = set(profile.language_list())

    points = 0
    # До 20 баллов за совпадение с интересующими типами задач.
    for task_type, keywords in TASK_KEYWORDS.items():
        if task_type not in selected_tasks:
            continue
        if any(kw in text_lower for kw in keywords):
            points += 7
    points = min(points, 20)

    # До 10 баллов за упоминание языков, которые знает пользователь.
    if languages:
        lang_hits = sum(1 for lang in languages if lang in text_lower)
        points += min(lang_hits * 5, 10)

    return min(points, 30)


def _simplicity_score(text: str) -> int:
    high_hits = _count_hits(text, HIGH_COMPLEXITY_MARKERS)
    low_hits = _count_hits(text, LOW_COMPLEXITY_MARKERS)

    base = 13  # стартуем с середины
    base += min(low_hits * 5, 12)
    base -= min(high_hits * 8, 20)

    # Очень длинное ТЗ (>2000 символов) обычно подразумевает сложность.
    if len(text) > 2000:
        base -= 4

    return max(0, min(base, 25))


def _budget_score(text: str, profile: UserProfile | None) -> int:
    budget = _extract_budget(text)
    min_budget = profile.min_budget if profile else 10

    if budget is None:
        return 10  # бюджет не указан — нейтрально
    if budget < min_budget:
        return 4
    if budget < min_budget * 2:
        return 14
    if budget <= 200:
        return 20
    # Слишком большой бюджет для новичка — настораживает.
    return 12


def _clarity_score(text: str) -> int:
    hits = _count_hits(text, CLARITY_MARKERS)
    base = 5 + hits * 3
    if len(text) < 80:
        base -= 4  # слишком короткое описание = неясные требования
    return max(0, min(base, 15))


def _low_risk_score(text: str) -> int:
    hits = _count_hits(text, RISK_MARKERS)
    return max(0, 10 - hits * 4)


def score_order(text: str, profile: UserProfile | None = None) -> ScoreBreakdown:
    """Главная функция: возвращает разбивку с total в [0, 100]."""
    return ScoreBreakdown(
        skill_match=_skill_match_score(text, profile),
        simplicity=_simplicity_score(text),
        budget=_budget_score(text, profile),
        clarity=_clarity_score(text),
        low_risk=_low_risk_score(text),
    )


def interpret(total: int) -> str:
    """Текстовая интерпретация суммарной оценки."""
    if total >= 80:
        return "отличный заказ для новичка"
    if total >= 60:
        return "можно попробовать"
    if total >= 40:
        return "рискованно"
    return "лучше пропустить"
