/**
 * Fiverr Order Scoring Module (C++ Console Application)
 *
 * Rule-based scoring of Fiverr orders from 0 to 100.
 * Criteria:
 *   - Skill match:       up to 30 points
 *   - Simplicity:        up to 25 points
 *   - Budget adequacy:   up to 20 points
 *   - Clarity:           up to 15 points
 *   - Low risk:          up to 10 points
 *
 * Compatible with Visual Studio 2019+ (C++17) and g++ 9+.
 */

#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <algorithm>
#include <regex>
#include <sstream>
#include <cctype>

// ============== Data Structures ==============

struct UserProfile {
    std::vector<std::string> languages;       // e.g. "python", "javascript"
    std::string experience_level;             // beginner / junior / intermediate
    std::vector<std::string> task_types;      // e.g. "bug fixing", "python scripts"
    int min_budget;                           // minimum acceptable budget in USD
    std::string max_complexity;               // low / medium / high
    std::string display_name;
};

struct ScoreBreakdown {
    int skill_match;  // /30
    int simplicity;   // /25
    int budget;       // /20
    int clarity;      // /15
    int low_risk;     // /10

    int total() const {
        return skill_match + simplicity + budget + clarity + low_risk;
    }

    void print() const {
        std::cout << "\n===== SCORE BREAKDOWN =====\n";
        std::cout << "  Skill match:       " << skill_match << " / 30\n";
        std::cout << "  Simplicity:        " << simplicity << " / 25\n";
        std::cout << "  Budget adequacy:   " << budget << " / 20\n";
        std::cout << "  Clarity:           " << clarity << " / 15\n";
        std::cout << "  Low risk:          " << low_risk << " / 10\n";
        std::cout << "  --------------------------\n";
        std::cout << "  TOTAL:             " << total() << " / 100\n";
        std::cout << "===========================\n";
    }
};

// ============== Keyword Dictionaries ==============

static const std::map<std::string, std::vector<std::string>> TASK_KEYWORDS = {
    {"bug fixing",       {"bug", "fix", "error", "issue", "broken", "not working", "crash"}},
    {"html/css fixes",   {"html", "css", "layout", "responsive", "ui", "frontend", "tailwind"}},
    {"javascript fixes", {"javascript", "js", "react", "vue", "node", "typescript", "jquery"}},
    {"python scripts",   {"python", "django", "flask", "fastapi", "pandas", "script"}},
    {"telegram bots",    {"telegram", "telebot", "aiogram", "bot api"}},
    {"automation",       {"automation", "automate", "selenium", "scrap", "schedule", "cron"}},
    {"wordpress fixes",  {"wordpress", "wp", "elementor", "woocommerce", "plugin"}},
    {"api integration",  {"api", "rest", "webhook", "integration", "endpoint", "graphql"}},
    {"ai prompts",       {"chatgpt", "openai", "prompt", "llm", "gpt", "anthropic", "claude"}},
};

static const std::vector<std::string> HIGH_COMPLEXITY_MARKERS = {
    "machine learning", "neural network", "blockchain", "smart contract",
    "kubernetes", "scalable", "microservices", "distributed", "high load",
    "production grade", "from scratch", "full stack", "build a complete",
    "architecture", "deep learning", "computer vision", "ios app",
    "android app", "native app"
};

static const std::vector<std::string> LOW_COMPLEXITY_MARKERS = {
    "small fix", "simple", "quick fix", "minor", "small bug", "small task",
    "tiny", "one line", "just need", "easy", "rename", "change color", "change text"
};

static const std::vector<std::string> CLARITY_MARKERS = {
    "github", "repo", "screenshot", "error message", "stack trace", "log",
    "example", "expected", "actual", "step", "reproduce"
};

static const std::vector<std::string> RISK_MARKERS = {
    "urgent", "asap", "right now", "in 1 hour", "in one hour",
    "milestone payment after", "pay after", "no budget", "low budget",
    "long term unpaid", "test task", "trial task", "nda",
    "nda required upfront", "send me your code", "outside fiverr",
    "telegram me", "whatsapp me", "skype me"
};

// ============== Helper Functions ==============

static std::string toLower(const std::string& s) {
    std::string result = s;
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return result;
}

static int countHits(const std::string& textLower, const std::vector<std::string>& markers) {
    int count = 0;
    for (const auto& marker : markers) {
        if (textLower.find(marker) != std::string::npos) {
            ++count;
        }
    }
    return count;
}

static int extractBudget(const std::string& text) {
    // Returns -1 if no budget found
    std::vector<std::regex> patterns = {
        std::regex(R"(\$\s*(\d{1,5}))"),
        std::regex(R"((\d{1,5})\s*\$)"),
        std::regex(R"((\d{1,5})\s*(?:usd|dollars|bucks))", std::regex::icase),
        std::regex(R"((?:budget|pay|price)[^\d]{0,15}(\d{1,5}))", std::regex::icase),
    };

    for (const auto& pattern : patterns) {
        std::smatch match;
        if (std::regex_search(text, match, pattern)) {
            try {
                return std::stoi(match[1].str());
            } catch (...) {
                continue;
            }
        }
    }
    return -1;
}

// ============== Scoring Functions ==============

static int skillMatchScore(const std::string& textLower, const UserProfile& profile) {
    if (profile.task_types.empty() && profile.languages.empty()) {
        return 12; // neutral score if no profile data
    }

    int points = 0;

    // Up to 20 points for matching task types
    for (const auto& [taskType, keywords] : TASK_KEYWORDS) {
        bool selected = false;
        for (const auto& t : profile.task_types) {
            if (toLower(t) == taskType) {
                selected = true;
                break;
            }
        }
        if (!selected) continue;

        for (const auto& kw : keywords) {
            if (textLower.find(kw) != std::string::npos) {
                points += 7;
                break;
            }
        }
    }
    points = std::min(points, 20);

    // Up to 10 points for matching programming languages
    for (const auto& lang : profile.languages) {
        if (textLower.find(toLower(lang)) != std::string::npos) {
            points += 5;
        }
    }
    points = std::min(points, 10 + std::min(points, 20));

    return std::min(points, 30);
}

static int simplicityScore(const std::string& textLower, size_t textLength) {
    int highHits = countHits(textLower, HIGH_COMPLEXITY_MARKERS);
    int lowHits = countHits(textLower, LOW_COMPLEXITY_MARKERS);

    int base = 13;
    base += std::min(lowHits * 5, 12);
    base -= std::min(highHits * 8, 20);

    if (textLength > 2000) {
        base -= 4;
    }

    return std::max(0, std::min(base, 25));
}

static int budgetScore(const std::string& text, int minBudget) {
    int budget = extractBudget(text);

    if (budget < 0) {
        return 10; // budget not specified - neutral
    }
    if (budget < minBudget) {
        return 4;
    }
    if (budget < minBudget * 2) {
        return 14;
    }
    if (budget <= 200) {
        return 20;
    }
    return 12; // too large for beginner - suspicious
}

static int clarityScore(const std::string& textLower, size_t textLength) {
    int hits = countHits(textLower, CLARITY_MARKERS);
    int base = 5 + hits * 3;
    if (textLength < 80) {
        base -= 4; // too short description = unclear requirements
    }
    return std::max(0, std::min(base, 15));
}

static int lowRiskScore(const std::string& textLower) {
    int hits = countHits(textLower, RISK_MARKERS);
    return std::max(0, 10 - hits * 4);
}

// ============== Main Scoring Function ==============

ScoreBreakdown scoreOrder(const std::string& text, const UserProfile& profile) {
    std::string textLower = toLower(text);
    size_t textLength = text.size();

    ScoreBreakdown result;
    result.skill_match = skillMatchScore(textLower, profile);
    result.simplicity = simplicityScore(textLower, textLength);
    result.budget = budgetScore(text, profile.min_budget);
    result.clarity = clarityScore(textLower, textLength);
    result.low_risk = lowRiskScore(textLower);

    return result;
}

std::string interpret(int total) {
    if (total >= 80) return "Excellent order for a beginner!";
    if (total >= 60) return "Worth trying";
    if (total >= 40) return "Risky";
    return "Better skip";
}

// ============== Profile Input ==============

static std::vector<std::string> splitByComma(const std::string& s) {
    std::vector<std::string> result;
    std::stringstream ss(s);
    std::string item;
    while (std::getline(ss, item, ',')) {
        // trim whitespace
        size_t start = item.find_first_not_of(" \t");
        size_t end = item.find_last_not_of(" \t");
        if (start != std::string::npos) {
            result.push_back(item.substr(start, end - start + 1));
        }
    }
    return result;
}

UserProfile inputProfile() {
    UserProfile profile;

    std::cout << "=== Freelancer Profile Setup ===\n\n";

    std::cout << "Programming languages (comma-separated, e.g. python,javascript,html): ";
    std::string langLine;
    std::getline(std::cin, langLine);
    profile.languages = splitByComma(langLine);

    std::cout << "Experience level (beginner/junior/intermediate): ";
    std::getline(std::cin, profile.experience_level);
    if (profile.experience_level.empty()) profile.experience_level = "beginner";

    std::cout << "Task types of interest (comma-separated):\n";
    std::cout << "  Available: bug fixing, html/css fixes, javascript fixes,\n";
    std::cout << "             python scripts, telegram bots, automation,\n";
    std::cout << "             wordpress fixes, api integration, ai prompts\n";
    std::cout << "Your choice: ";
    std::string taskLine;
    std::getline(std::cin, taskLine);
    profile.task_types = splitByComma(taskLine);

    std::cout << "Minimum budget in USD (default 10): ";
    std::string budgetLine;
    std::getline(std::cin, budgetLine);
    profile.min_budget = budgetLine.empty() ? 10 : std::stoi(budgetLine);

    std::cout << "Max complexity (low/medium/high, default medium): ";
    std::getline(std::cin, profile.max_complexity);
    if (profile.max_complexity.empty()) profile.max_complexity = "medium";

    std::cout << "Display name: ";
    std::getline(std::cin, profile.display_name);

    std::cout << "\nProfile saved!\n\n";
    return profile;
}

// ============== Main ==============

int main() {
    std::cout << "=========================================\n";
    std::cout << "  Fiverr Order Scoring Tool (C++ v1.0)  \n";
    std::cout << "=========================================\n\n";

    // Step 1: Setup profile
    UserProfile profile = inputProfile();

    // Step 2: Main loop - analyze orders
    std::string input;
    while (true) {
        std::cout << "-------------------------------------------\n";
        std::cout << "Paste order description (or 'quit' to exit):\n> ";

        std::string orderText;
        std::string line;
        // Read multiline until empty line
        bool firstLine = true;
        while (std::getline(std::cin, line)) {
            if (line == "quit" && firstLine) {
                std::cout << "\nGoodbye! Good luck freelancing!\n";
                return 0;
            }
            if (line.empty() && !firstLine) break;
            if (!firstLine) orderText += "\n";
            orderText += line;
            firstLine = false;
        }

        if (orderText.empty()) {
            if (std::cin.eof()) break;
            std::cout << "Empty input. Try again.\n";
            continue;
        }

        // Score the order
        ScoreBreakdown score = scoreOrder(orderText, profile);
        score.print();

        int total = score.total();
        std::cout << "  Verdict: " << interpret(total) << "\n\n";
    }

    return 0;
}
