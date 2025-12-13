from typing import Dict, List

from .text_analyzer import TextAnalyzer


class SmartVideoSorter:
    """Умная система сортировки видео без AI тк не достал бесплатное API нейронки"""

    def __init__(self):
        self.analyzer = TextAnalyzer()

    def sort_videos(
        self, videos: List[Dict], topic: str, target_difficulty: str
    ) -> List[Dict]:
        """Сортирует видео по правилам"""
        if not videos:
            return videos

        # 1. Оцениваем сложность каждого видео
        scored_videos = []
        for video in videos:
            score = self._calculate_video_score(video, topic, target_difficulty)
            scored_videos.append((score, video))

        # 2. Сортируем по оценке (от простого к сложному)
        scored_videos.sort(key=lambda x: x[0])

        # 3. Группируем по сложности для создания модулей
        sorted_videos = [video for _, video in scored_videos]

        # 4. Добавляем метаданные
        for i, video in enumerate(sorted_videos):
            video["order"] = i + 1
            video["estimated_difficulty"] = self._estimate_difficulty(video, topic)

        return sorted_videos

    def _calculate_video_score(
        self, video: Dict, topic: str, target_difficulty: str
    ) -> float:
        """Рассчитывает оценку видео для сортировки"""
        score = 0.0

        # 1. Анализ заголовка (40%)
        title = video.get("title", "")
        title_analysis = self.analyzer.analyze_title(title)

        difficulty_map = {"beginner": 1, "intermediate": 2, "advanced": 3, "unknown": 2}
        target_map = {"beginner": 1, "intermediate": 2, "advanced": 3}

        video_diff = difficulty_map.get(title_analysis["difficulty"], 2)
        target_diff = target_map.get(target_difficulty, 2)

        # Близость к целевому уровню (но начинаем с более простых)
        diff_score = 1.0 - abs(video_diff - target_diff) / 3.0
        score += diff_score * 0.4

        # 2. Длительность (30%) - более короткие видео идут раньше
        duration = video.get("duration", 600)
        if duration < 300:  # < 5 мин
            duration_score = 1.0
        elif duration < 900:  # < 15 мин
            duration_score = 0.8
        elif duration < 1800:  # < 30 мин
            duration_score = 0.5
        else:  # > 30 мин
            duration_score = 0.2

        score += duration_score * 0.3

        # 3. Популярность (20%) - более популярные могут быть лучше объяснены
        views = video.get("view_count", 0)
        if views > 100000:
            popularity_score = 0.9
        elif views > 10000:
            popularity_score = 0.7
        elif views > 1000:
            popularity_score = 0.5
        else:
            popularity_score = 0.3

        score += popularity_score * 0.2

        # 4. Релевантность теме (10%)
        title_lower = title.lower()
        topic_lower = topic.lower()

        if topic_lower in title_lower:
            relevance_score = 1.0
        else:
            # Ищем ключевые слова темы в заголовке
            topic_words = set(topic_lower.split())
            title_words = set(title_lower.split())
            common_words = topic_words.intersection(title_words)
            relevance_score = len(common_words) / max(len(topic_words), 1)

        score += relevance_score * 0.1

        return score

    def _estimate_difficulty(self, video: Dict, topic: str) -> str:
        """Оценивает сложность видео"""
        title = video.get("title", "")
        analysis = self.analyzer.analyze_title(title)

        if analysis["confidence"] > 0.3:
            return analysis["difficulty"]

        # Если уверенность низкая, используем эвристики
        duration = video.get("duration", 600)
        title_lower = title.lower()

        # Долгие видео обычно сложнее
        if duration > 1800:  # > 30 минут
            return "advanced"
        elif "практика" in title_lower or "проект" in title_lower:
            return "intermediate"
        elif "основы" in title_lower or "начало" in title_lower:
            return "beginner"

        return "intermediate"

    def group_into_modules(
        self, videos: List[Dict], module_size: int = 5
    ) -> List[List[Dict]]:
        """Группирует видео в модули"""
        modules = []
        for i in range(0, len(videos), module_size):
            module = videos[i : i + module_size]

            # Определяем тему модуля на основе видео
            module_topic = self._determine_module_topic(module)
            for video in module:
                video["module_topic"] = module_topic

            modules.append(module)

        return modules

    def _determine_module_topic(self, videos: List[Dict]) -> str:
        """Определяет тему модуля на основе видео"""
        if not videos:
            return "Основные понятия"

        # Собираем все заголовки
        titles = [v.get("title", "") for v in videos]

        # Ищем общие слова
        common_words = []
        for title in titles:
            words = set(self.analyzer.extract_keywords(title, 5))
            if not common_words:
                common_words = words
            else:
                common_words = common_words.intersection(words)

        if common_words:
            return " ".join(list(common_words)[:3]).capitalize()

        # Если общих слов нет, берем первое слово из первого заголовка
        first_title = titles[0]
        words = first_title.split()
        if len(words) > 0:
            return words[0]

        return "Основные понятия"
