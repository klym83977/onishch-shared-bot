import os
import logging

logging.basicConfig(level=logging.INFO)

# --- ЗМІННІ З VERCEL ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
MAIN_BOT_TOKEN = os.environ.get("MAIN_BOT_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
YOUR_TELEGRAM_CHAT_ID = os.environ.get("YOUR_TELEGRAM_CHAT_ID")

IMGBB_API_KEY = "a6f01e2115287b5dbd7a28cc37e957d1"
NOTION_VERSION = "2022-06-28"

# Перевірка наявності токенів
if not TELEGRAM_TOKEN or not MAIN_BOT_TOKEN:
    logging.error("ПОМИЛКА: Не встановлено TELEGRAM_TOKEN або MAIN_BOT_TOKEN у Vercel!")
