import os
import tempfile
import logging
import requests
from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import speech_recognition as sr
from pydub import AudioSegment

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

# Перевірка наявності токенів
if not TELEGRAM_TOKEN or not MAIN_BOT_TOKEN:
    logging.error("ПОМИЛКА: Не встановлено TELEGRAM_TOKEN або MAIN_BOT_TOKEN у Vercel!")
    raise ValueError("Missing Telegram Tokens in Environment Variables")

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)
main_bot = telebot.TeleBot(MAIN_BOT_TOKEN, threaded=False)
user_pending_tasks = {}

def create_notion_task(task_text, tag, image_url=None):
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
            "Status": {"status": {"name": "Вхідні"}}, # Змінено на "Вхідні"
            "Priority": {"select": {"name": "⚡ Середній"}},
            "Tags": {"multi_select": [{"name": tag}]}
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

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    msg = bot.send_message(message.chat.id, "🖼️ Завантажую фото...")
    try:
        task_text = message.caption if message.caption else "Фото-задача"
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        res = requests.post("https://api.imgbb.com/1/upload", data={"key": IMGBB_API_KEY}, files={"image": ("photo.jpg", downloaded_file, "image/jpeg")})
        image_url = res.json()["data"]["url"]
        bot.delete_message(message.chat.id, msg.message_id)
        process_task_text(message.chat.id, message.from_user.id, task_text, image_url)
    except Exception as e:
        bot.edit_message_text(f"❌ Помилка: {e}", chat_id=message.chat.id, message_id=msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def button_callback(call):
    user_id = call.from_user.id
    data = call.data
    task_data = user_pending_tasks.get(user_id)

    if data == "ignore": return bot.answer_callback_query(call.id)
    if not task_data: return bot.answer_callback_query(call.id, "Час вийшов.", show_alert=True)

    if data == "save_task":
        if not task_data['tag']: return bot.answer_callback_query(call.id, "⚠️ Оберіть категорію!", show_alert=True)
            
        bot.edit_message_text("⏳ Відправляю...", chat_id=call.message.chat.id, message_id=call.message.message_id)
        success, error_msg = create_notion_task(task_data["text"], task_data["tag"], task_data.get("image_url"))
        
        if success:
            del user_pending_tasks[user_id]
            bot.edit_message_text(f"✅ Задачу відправлено Андрію!", chat_id=call.message.chat.id, message_id=call.message.message_id)
            
            sender = f"{call.from_user.first_name} {call.from_user.last_name or ''}"
            text = f"🔔 <b>Нова задача!</b>\n\n👤 Від: {sender}\n📝: {task_data['text']}\n🏷️: {task_data['tag']}"
            main_bot.send_message(YOUR_TELEGRAM_CHAT_ID, text, parse_mode="HTML")
        else:
            bot.edit_message_text(f"❌ Помилка: {error_msg[:100]}", chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    if data.startswith("tag_"):
        task_data['tag'] = data.split("_", 1)[1]
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=generate_markup(task_data))
    bot.answer_callback_query(call.id)

@app.route('/', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    bot.process_new_updates([telebot.types.Update.de_json(json_string)])
    return jsonify({"status": "ok"})

application = app
