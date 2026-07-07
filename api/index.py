import os
import tempfile
import logging
import subprocess
import requests
from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- ЗМІННІ З VERCEL ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
MAIN_BOT_TOKEN = os.environ.get("MAIN_BOT_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
YOUR_TELEGRAM_CHAT_ID = os.environ.get("YOUR_TELEGRAM_CHAT_ID")

IMGBB_API_KEY = "a6f01e2115287b5dbd7a28cc37e957d1"
NOTION_VERSION = "2022-06-28"

if not TELEGRAM_TOKEN or not MAIN_BOT_TOKEN:
    logging.error("ПОМИЛКА: Не встановлено TELEGRAM_TOKEN або MAIN_BOT_TOKEN у Vercel!")
    raise ValueError("Missing Telegram Tokens in Environment Variables")

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)
main_bot = telebot.TeleBot(MAIN_BOT_TOKEN, threaded=False)
user_pending_tasks = {}

def create_notion_task(task_text, tag, sender_name, image_url=None):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": task_text}}]},
            "Status": {"status": {"name": "Вхідні"}},
            "Priority": {"select": {"name": "⚡ Середній"}},
            "Tags": {"multi_select": [{"name": tag}]},
            "Від кого": {"rich_text": [{"text": {"content": sender_name}}]}
        }
    }
    
    if image_url:
        data["children"] = [{"object": "block", "type": "image", "image": {"type": "external", "external": {"url": image_url}}}]
        
    try:
        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200, response.text if response.status_code != 200 else "OK"
    except Exception as e:
        return False, str(e)

def generate_markup(task_data):
    markup = InlineKeyboardMarkup()
    def btn(text, val, current_val, prefix):
        if val == current_val:
            return InlineKeyboardButton(f"✅ {text}", callback_data=f"{prefix}_{val}")
        return InlineKeyboardButton(text, callback_data=f"{prefix}_{val}")

    markup.row(InlineKeyboardButton("— 🏷️ КАТЕГОРІЯ —", callback_data="ignore"))
    markup.row(btn("🛒 Покупки", "🛒 Покупки", task_data['tag'], "tag"), btn("🏠 Дім", "🏠 Дім", task_data['tag'], "tag"))
    markup.row(btn("👶 Діти", "👶 Діти", task_data['tag'], "tag"), btn("🛠️ DIY", "🛠️ DIY", task_data['tag'], "tag"))
    markup.row(InlineKeyboardButton("🚀 ВІДПРАВИТИ АНДРІЮ", callback_data="save_task"))
    return markup

@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(message.chat.id, "Привіт! Я — спільний асистент Андрія. Напишіть задачу, і я миттєво передам її йому.")

def process_task_text(chat_id, user_id, task_text, image_url=None):
    user_pending_tasks[user_id] = {"text": task_text, "tag": None, "image_url": image_url}
    img_msg = "\n🖼️ Додано фото" if image_url else ""
    bot.send_message(
        chat_id, 
        f'📝 Задача: "{task_text}"{img_msg}\n\n👇 Оберіть категорію:', 
        reply_markup=generate_markup(user_pending_tasks[user_id])
    )

@bot.message_handler(content_types=['text'])
def handle_text(message):
    process_task_text(message.chat.id, message.from_user.id, message.text)
    
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    msg = bot.send_message(message.chat.id, "🎧 Розпізнаю голос (локально)...")
    
    try:
        import imageio_ffmpeg
        import speech_recognition as sr
        
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        ogg_path = f"/tmp/{message.voice.file_id}.ogg"
        wav_path = f"/tmp/{message.voice.file_id}.wav"
        
        with open(ogg_path, "wb") as f:
            f.write(downloaded_file)
            
        # БЕРЕМО ЛОКАЛЬНИЙ FFMPEG
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        
        # ПРЯМА КОНВЕРТАЦІЯ БЕЗ PYDUB ТА FFPROBE
        subprocess.run([ffmpeg_exe, "-y", "-i", ogg_path, wav_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Розпізнаємо стандартним методом
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="uk-UA")
        
        # Прибираємо файли
        if os.path.exists(ogg_path): os.remove(ogg_path)
        if os.path.exists(wav_path): os.remove(wav_path)
        
        bot.delete_message(message.chat.id, msg.message_id)
        process_task_text(message.chat.id, message.from_user.id, text)
        
    except Exception as e:
        bot.edit_message_text(f"❌ Локальна помилка: {str(e)}", chat_id=message.chat.id, message_id=msg.message_id)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    msg = bot.send_message(message.chat.id, "🖼️ Завантажую фото...")
    try:
        task_text = message.caption if message.caption else
