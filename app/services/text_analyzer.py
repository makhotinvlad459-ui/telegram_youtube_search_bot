import re
from collections import Counter
from typing import Dict, List

import nltk
from nltk.corpus import stopwords

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords")


class TextAnalyzer:
    def __init__(self):
        self.russian_stopwords = set(stopwords.words("russian"))
        self.difficulty_patterns = {
            "beginner": [
                r"для начинающих",
                r"основы",
                r"введение",
                r"начальный",
                r"базовый",
                r"с нуля",
                r"новичкам",
                r"простой",
                r"легкий",
                r"вводный",
                r"первый шаг",
                r"начало",
                r"основа",
            ],
            "intermediate": [
                r"продвинутый",
                r"углубленный",
                r"практика",
                r"проект",
                r"средний уровень",
                r"разбор",
                r"примеры",
                r"применение",
                r"техники",
                r"методы",
                r"алгоритмы",
                r"реальный",
            ],
            "advanced": [
                r"эксперт",
                r"профессиональный",
                r"мастер класс",
                r"углубленно",
                r"продвинутый уровень",
                r"оптимизация",
                r"архитектура",
                r"лучшие практики",
                r"паттерны",
                r"сложный",
                r"глубокий",
            ],
        }

    def analyze_title(self, title: str) -> Dict:
        """Анализирует заголовок видео и определяет сложность"""
        title_lower = title.lower()

        scores = {"beginner": 0, "intermediate": 0, "advanced": 0}

        for difficulty, patterns in self.difficulty_patterns.items():
            for pattern in patterns:
                if re.search(pattern, title_lower):
                    scores[difficulty] += 1

        # Определяем общую сложность
        max_score = max(scores.values())
        if max_score == 0:
            return {"difficulty": "unknown", "confidence": 0}

        for difficulty, score in scores.items():
            if score == max_score:
                confidence = score / 3
                return {"difficulty": difficulty, "confidence": confidence}

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Извлекает ключевые слова из текста"""
        words = re.findall(r"\b[а-яёa-z]{3,}\b", text.lower())
        filtered_words = [w for w in words if w not in self.russian_stopwords]

        word_freq = Counter(filtered_words)
        return [word for word, _ in word_freq.most_common(max_keywords)]

    def calculate_readability_score(self, text: str) -> float:
        """Рассчитывает простоту текста (чем выше, тем проще)"""
        sentences = re.split(r"[.!?]+", text)
        all_words = re.findall(r"\b\w+\b", text.lower())

        meaningful_words = [
            w for w in all_words if w not in self.russian_stopwords and len(w) >= 2
        ]

        if len(sentences) == 0 or len(meaningful_words) == 0:
            return 0.5

        avg_sentence_length = len(meaningful_words) / len(sentences)
        unique_words = len(set(meaningful_words))

        # короткие предложения + мало уникальных слов = проще
        if avg_sentence_length < 10:
            sentence_score = 1.0
        elif avg_sentence_length < 20:
            sentence_score = 0.7
        else:
            sentence_score = 0.3

        uniqueness = unique_words / len(meaningful_words)
        if uniqueness < 0.3:
            uniqueness_score = 1.0
        elif uniqueness < 0.6:
            uniqueness_score = 0.6
        else:
            uniqueness_score = 0.3

        return (sentence_score + uniqueness_score) / 2
