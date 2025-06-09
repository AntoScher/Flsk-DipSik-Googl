import os
import logging
import threading
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler
from telegram.constants import ParseMode
from dotenv import load_dotenv  # Добавлено

# Загрузка переменных окружения из .env
load_dotenv()

# Настройка приложения Flask
app = Flask(__name__)

# Конфигурация
try:
    # Пытаемся получить из переменных окружения
    TELEGRAM_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
    ADMIN_CHAT_ID = os.environ['TELEGRAM_ADMIN_CHAT_ID']
    SECRET_TOKEN = os.environ.get('WEBHOOK_SECRET', 'default-secret-token')
except KeyError:
    # Для локальной разработки - задаем вручную
    print("⚠️ Переменные окружения не найдены. Используются тестовые значения.")
    TELEGRAM_TOKEN = "ВАШ_РЕАЛЬНЫЙ_ТОКЕН"  # ЗАМЕНИТЕ НА РЕАЛЬНЫЙ ТОКЕН!
    ADMIN_CHAT_ID = "ВАШ_РЕАЛЬНЫЙ_CHAT_ID"  # ЗАМЕНИТЕ НА РЕАЛЬНЫЙ CHAT ID!
    SECRET_TOKEN = "test-secret-token"

# Инициализация бота
bot = Bot(token=TELEGRAM_TOKEN)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Обработчики Telegram
async def handle_order(update: Update, context):
    await update.message.reply_text(
        "ℹ️ Этот бот только для уведомлений. Заказы оформляются через ApteDoc AI Assistant",
        parse_mode=ParseMode.MARKDOWN
    )


# Вебхук для уведомлений
@app.route('/order_webhook', methods=['POST'])
def order_webhook():
    try:
        if request.headers.get('X-Telegram-Secret') != SECRET_TOKEN:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        order_data = request.json['order']
        message = (
            f"🚨 *Новый заказ* #{order_data['order_number']}\n"
            f"📦 **Препарат**: {order_data['medicine']}\n"
            f"🏷 **Количество**: {order_data['quantity']}\n"
            f"📍 **Адрес**: {order_data['delivery_address']}\n"
            f"💊 **Аптека**: {order_data.get('pharmacy', 'Аптека.ру')}\n"
            f"💳 **Оплата**: {order_data.get('payment_method', 'Онлайн')}"
        )

        bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )

        return jsonify({"status": "success"})

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# Эндпоинты для проверки
@app.route('/status', methods=['GET'])
def status_endpoint():
    return "✅ Сервер работает! Используйте /send_test_notification для проверки уведомлений"


@app.route('/send_test_notification', methods=['GET'])
def send_test_notification():
    try:
        test_data = {
            "order": {
                "order_number": "TEST-123",
                "medicine": "Тестовый препарат",
                "quantity": 3,
                "delivery_address": "Тестовый адрес, д.1",
                "pharmacy": "Тестовая аптека",
                "payment_method": "Картой"
            }
        }

        message = (
            f"🚨 *ТЕСТОВЫЙ ЗАКАЗ* #{test_data['order']['order_number']}"
            f"📦 **Препарат**: {test_data['order']['medicine']}"
            f"🏷 **Количество**: {test_data['order']['quantity']}"
            f"📍 **Адрес**: {test_data['order']['delivery_address']}"
            f"💊 **Аптека**: {test_data['order'].get('pharmacy', 'Аптека.ру')}"
            f"💳 **Оплата**: {test_data['order'].get('payment_method', 'Онлайн')}"
        )

        bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )

        return jsonify({
            "status": "success",
            "message": "Тестовое уведомление отправлено в Telegram"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Запуск и конфигурация
def setup_telegram():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", handle_order))
    application.add_handler(CommandHandler("order", handle_order))
    return application


def run_server():
    application = setup_telegram()

    print("🟢 Telegram бот запущен в режиме polling...")
    print("🟢 Flask сервер запущен на http://localhost:5000")
    print("Проверочные эндпоинты:")
    print("  http://localhost:5000/status")
    print("  http://localhost:5000/send_test_notification")

    flask_thread = threading.Thread(
        target=app.run,
        kwargs={'host': '0.0.0.0', 'port': 5000, 'debug': True, 'use_reloader': False},
        daemon=True
    )
    flask_thread.start()

    application.run_polling()


if __name__ == '__main__':
    run_server()
