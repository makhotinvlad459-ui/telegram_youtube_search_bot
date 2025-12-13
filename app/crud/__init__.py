from .course import (
    create_course,
    enroll_user_to_course,
    get_course_by_id,
    get_course_statistics,
    get_courses_by_topic,
    get_popular_courses,
    get_user_courses,
    get_user_progress_for_course,
    search_courses,
)
from .user import (
    get_or_create_user,
    get_top_users,
    get_user_by_id,
    get_user_by_telegram_id,
    get_user_stats,
    mark_lesson_completed,
    update_watch_time,
)

__all__ = [
    # User
    "get_or_create_user",
    "get_user_by_telegram_id",
    "get_user_by_id",
    "get_user_stats",
    "get_top_users",
    "mark_lesson_completed",
    "update_watch_time",
    # Course
    "create_course",
    "get_course_by_id",
    "get_courses_by_topic",
    "get_popular_courses",
    "search_courses",
    "enroll_user_to_course",
    "get_user_courses",
    "get_course_statistics",
    "get_user_progress_for_course",
]
