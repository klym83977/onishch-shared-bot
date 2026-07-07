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
@@ -30,7 +27,7 @@
main_bot = telebot.TeleBot(MAIN_BOT_TOKEN, threaded=False)
user_pending_tasks = {}

def create_notion_task(task_text, tag, image_url=None):
def create_notion_task(task_text, tag, sender_name, image_url=None):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
@@ -42,9 +39,10 @@ def create_notion_task(task_text, tag, image_url=None):
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": task_text}}]},
            "Status": {"status": {"name": "Вхідні"}}, # Змінено на "Вхідні"
            "Status": {"status": {"name": "Вхідні"}},
            "Priority": {"select": {"name": "⚡ Середній"}},
            "Tags": {"multi_select": [{"name": tag}]}
            "Tags": {"multi_select": [{"name": tag}]},
            "Від кого": {"rich_text": [{"text": {"content": sender_name}}]}
        }
    }

@@ -112,16 +110,21 @@ def button_callback(call):

    if data == "save_task":
        if not task_data['tag']: return bot.answer_callback_query(call.id, "⚠️ Оберіть категорію!", show_alert=True)
        
        # Формуємо ім'я відправника
        sender_full_name = f"{call.from_user.first_name} {call.from_user.last_name or ''}".strip()

        bot.edit_message_text("⏳ Відправляю...", chat_id=call.message.chat.id, message_id=call.message.message_id)
        success, error_msg = create_notion_task(task_data["text"], task_data["tag"], task_data.get("image_url"))
        
        # Передаємо sender_full_name у функцію
        success, error_msg = create_notion_task(task_data["text"], task_data["tag"], sender_full_name, task_data.get("image_url"))

        if success:
            del user_pending_tasks[user_id]
            bot.edit_message_text(f"✅ Задачу відправлено Андрію!", chat_id=call.message.chat.id, message_id=call.message.message_id)

            sender = f"{call.from_user.first_name} {call.from_user.last_name or ''}"
            text = f"🔔 <b>Нова задача!</b>\n\n👤 Від: {sender}\n📝: {task_data['text']}\n🏷️: {task_data['tag']}"
            # Сповіщення через основний бот
            text = f"🔔 <b>Нова задача!</b>\n\n👤 Від: {sender_full_name}\n📝: {task_data['text']}\n🏷️: {task_data['tag']}"
            main_bot.send_message(YOUR_TELEGRAM_CHAT_ID, text, parse_mode="HTML")
        else:
            bot.edit_message_text(f"❌ Помилка: {error_msg[:100]}", chat_id=call.message.chat.id, message_id=call.message.message_id)
