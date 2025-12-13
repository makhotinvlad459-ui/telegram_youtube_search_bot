import logging
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

# Инициализировать БД
from app.db.database import init_db

print("🗄️ Инициализация базы данных...")
init_db()
print("✅ База данных готова")

# Запустить бота
from app.bot.bot import run_bot

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    run_bot()
