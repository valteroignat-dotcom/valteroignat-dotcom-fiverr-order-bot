# Fiverr Order Scoring — C++ Console Application

Консольная реализация модуля **scoring** (оценка заказов) из Telegram-бота Fiverr Order Bot.

## Описание

Программа реализует rule-based оценку заказов Fiverr по 5 критериям (от 0 до 100 баллов):

| Критерий | Макс. баллов | Описание |
|----------|-------------|----------|
| Skill match | 30 | Совпадение с навыками пользователя |
| Simplicity | 25 | Простота задачи |
| Budget | 20 | Адекватность бюджета |
| Clarity | 15 | Ясность требований |
| Low risk | 10 | Низкий уровень риска |

## Сборка

### Visual Studio (Windows)

1. Открыть **Visual Studio 2019/2022**
2. **File → Open → CMake...** → выбрать `CMakeLists.txt` из этой папки
3. Или создать новый проект «Console App (C++)» и добавить `main.cpp`
4. Собрать: **Build → Build Solution** (Ctrl+Shift+B)
5. Запустить: **Debug → Start Without Debugging** (Ctrl+F5)

### g++ (Linux/macOS)

```bash
cd cpp_scoring
g++ -std=c++17 -Wall -Wextra -o scoring main.cpp
./scoring
```

### CMake (кроссплатформенно)

```bash
cd cpp_scoring
cmake -B build
cmake --build build
./build/scoring        # Linux/macOS
# build\Debug\scoring.exe  # Windows
```

## Использование

1. Программа попросит заполнить профиль фрилансера (языки, типы задач, бюджет)
2. Далее вводите описание заказа (текст, завершение — пустая строка)
3. Программа выведет разбивку оценки по каждому критерию и итоговый балл
4. Введите `quit` для выхода

## Пример работы

```
=========================================
  Fiverr Order Scoring Tool (C++ v1.0)
=========================================

=== Freelancer Profile Setup ===

Programming languages (comma-separated): python, javascript
Experience level (beginner/junior/intermediate): beginner
Task types of interest: bug fixing, python scripts
Minimum budget in USD (default 10): 15
Max complexity (low/medium/high): low
Display name: John

Profile saved!

-------------------------------------------
Paste order description (or 'quit' to exit):
> I have a simple Python script that has a small bug. It crashes when reading
> a CSV file. Budget $50. I can share the repo on GitHub with error logs.

===== SCORE BREAKDOWN =====
  Skill match:       17 / 30
  Simplicity:        23 / 25
  Budget adequacy:   20 / 20
  Clarity:           14 / 15
  Low risk:          10 / 10
  --------------------------
  TOTAL:             84 / 100
===========================
  Verdict: Excellent order for a beginner!
```
