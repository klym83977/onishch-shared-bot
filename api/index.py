from flask import Flask, request, jsonify
import telebot

# Імпортуємо нашого готового бота з сусіднього файлу
from handlers import bot

app = Flask(__name__)
application = app

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return jsonify({"status": "Shared Bot is running perfectly 🚀"})
    
    json_string = request.get_data().decode('utf-8')
    bot.process_new_updates([telebot.types.Update.de_json(json_string)])
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run()
