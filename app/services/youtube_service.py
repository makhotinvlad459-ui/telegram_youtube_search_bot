from typing import Dict, List, Optional

import isodate
from googleapiclient.discovery import build

from app.core.config import settings


class YouTubeService:
    def __init__(self):
        self.api_key = settings.YOUTUBE_API_KEY
        if self.api_key:
            self.youtube = build("youtube", "v3", developerKey=self.api_key)

    def search_videos(self, query: str, max_results: int = 20) -> List[Dict]:
        """Поиск видео на YouTube, у google API свои методы... не get,post..."""
        if not self.api_key:
            return self._get_mock_videos(query, max_results)

        try:
            search_response = (
                self.youtube.search()
                .list(
                    q=query,
                    part="snippet",
                    type="video",
                    maxResults=max_results,
                    order="relevance",
                    videoDuration="medium",
                    relevanceLanguage="ru",
                )
                .execute()
            )

            videos = []
            for item in search_response.get("items", []):
                video_id = item["id"]["videoId"]
                video_data = {
                    "id": video_id,
                    "title": item["snippet"]["title"],
                    "description": item["snippet"]["description"][:300],
                    "channel": item["snippet"]["channelTitle"],
                    "url": f"https://youtube.com/watch?v={video_id}",
                    "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                    "published_at": item["snippet"]["publishedAt"],
                }

                details = self._get_video_details(video_id)
                if details:
                    video_data.update(details)

                videos.append(video_data)

            return videos

        except Exception as e:
            print(f"YouTube API error: {e}")
            return self._get_mock_videos(query, max_results)

    def _get_video_details(self, video_id: str) -> Optional[Dict]:
        """Получение деталей видео"""
        try:
            response = (
                self.youtube.videos()
                .list(part="contentDetails,statistics", id=video_id)
                .execute()
            )

            if response["items"]:
                item = response["items"][0]

                duration = 0
                if "contentDetails" in item:
                    duration_str = item["contentDetails"]["duration"]
                    duration = self._parse_duration(duration_str)

                view_count = 0
                like_count = 0
                if "statistics" in item:
                    view_count = int(item["statistics"].get("viewCount", 0))
                    like_count = int(item["statistics"].get("likeCount", 0))

                return {
                    "duration": duration,
                    "view_count": view_count,
                    "like_count": like_count,
                }
        except:
            pass
        return None

    def _parse_duration(self, duration_str: str) -> int:
        """Конвертирует ISO 8601 длительность в секунды"""
        try:
            duration = isodate.parse_duration(duration_str)
            return int(duration.total_seconds())
        except:
            return 600

    def _get_mock_videos(self, query: str, max_results: int) -> List[Dict]:
        """Моковые данные для тестирования"""
        return [
            {
                "id": f"mock_{i}",
                "title": (
                    f"{query} - Урок {i + 1}: Основные понятия"
                    if i < 3
                    else (
                        f"{query} - Урок {i + 1}: Практика"
                        if i < 6
                        else f"{query} - Урок {i + 1}: Продвинутые техники"
                    )
                ),
                "description": f'Обучение теме {query}. Уровень сложности: {["начальный", "средний", "продвинутый"][i % 3]}',
                "channel": "Учебный канал",
                "duration": [300, 600, 900, 1200][i % 4],
                "view_count": 5000 + i * 2000,
                "like_count": 100 + i * 50,
                "url": f"https://youtube.com/watch?v=mock_{i}",
                "thumbnail": "https://img.youtube.com/vi/default/mqdefault.jpg",
            }
            for i in range(max_results)
        ]
