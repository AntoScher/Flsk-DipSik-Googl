import os
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode
from dotenv import load_dotenv
import logging
import requests

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Переменные окружения
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('TELEGRAM_ADMIN_CHAT_ID')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')

# Инициализация бота и приложения
bot = Bot(token=TELEGRAM_TOKEN)
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Обработчики команд
def handle_order(update: Update, context):
    """Обработчик для ручных команд"""
    update.message.reply_text(
        "ℹ️ Этот бот только для уведомлений. Заказы оформляются через ApteDoc AI Assistant",
        parse_mode=ParseMode.MARKDOWN
    )

def handle_start(update: Update, context):
    """Обработчик команды /start"""
    update.message.reply_text("Hello! I'm your bot.")

# Регистрация обработчиков
application.add_handler(CommandHandler("start", handle_start))
application.add_handler(CommandHandler("order", handle_order))

# Обработчик вебхуков
async def webhook_handler():
    try:
        # Проверка секретного токена
        secret = request.headers.get('X-Telegram-Secret')
        if secret != WEBHOOK_SECRET:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        data = request.json
        update = Update.de_json(data, bot)
        await application.update_queue.put(update)
        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

app_flask = Flask(__name__)

@app_flask.route('/webhook', methods=['POST'])
def route_webhook():
    return webhook_handler()

def set_webhook():
    """Установка вебхука"""
    webhook_url = "https://your-domain.com/webhook"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}&secret_token={WEBHOOK_SECRET}"
    response = requests.get(url)
    print(response.json())

@app_flask.route('/set_webhook', methods=['GET'])
def route_set_webhook():
    set_webhook()
    return "Webhook set", 200

# Запуск приложения
if __name__ == "__main__":
    # Установка вебхука при запуске
    set_webhook()
    # Запуск сервера Flask
    app_flask.run(host="0.0.0.0", port=8000, debug=True)