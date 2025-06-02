import os
import logging
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler
from telegram.constants import ParseMode

# Настройка приложения Flask
app = Flask(__name__)

# Конфигурация - с возможностью локальной разработки
try:
    # Пытаемся получить из переменных окружения
    TELEGRAM_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
    ADMIN_CHAT_ID = os.environ['TELEGRAM_ADMIN_CHAT_ID']
    SECRET_TOKEN = os.environ.get('WEBHOOK_SECRET', 'default-secret-token')
except KeyError:
    # Для локальной разработки - задаем вручную
    print("⚠️ Переменные окружения не найдены. Используются тестовые значения.")
    TELEGRAM_TOKEN = "ВАШ_ТЕЛЕГРАМ_ТОКЕН"  # Замените на реальный токен
    ADMIN_CHAT_ID = "ВАШ_ЧАТ_ID"  # Замените на реальный chat ID
    SECRET_TOKEN = "test-secret-token"

# Инициализация бота
bot = Bot(token=TELEGRAM_TOKEN)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ================ Обработчики Telegram ================
async def handle_order(update: Update, context):
    """Ответ на команды /start и /order"""
    await update.message.reply_text(
        "ℹ️ Этот бот только для уведомлений. Заказы оформляются через ApteDoc AI Assistant",
        parse_mode=ParseMode.MARKDOWN
    )


# ================ Вебхук для уведомлений ================
@app.route('/order_webhook', methods=['POST'])
def order_webhook():
    """Основной вебхук для получения заказов"""
    try:
        # Проверка секретного токена
        if request.headers.get('X-Telegram-Secret') != SECRET_TOKEN:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        order_data = request.json['order']

        # Формируем сообщение
        message = (
            f"🚨 *Новый заказ* #{order_data['order_number']}\n"
            f"📦 **Препарат**: {order_data['medicine']}\n"
            f"🏷 **Количество**: {order_data['quantity']}\n"
            f"📍 **Адрес**: {order_data['delivery_address']}\n"
            f"💊 **Аптека**: {order_data.get('pharmacy', 'Аптека.ру')}\n"
            f"💳 **Оплата**: {order_data.get('payment_method', 'Онлайн')}"
        )

        # Отправляем сообщение
        bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )

        return jsonify({"status": "success"})

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ================ Тестовые эндпоинты ================
@app.route('/test', methods=['GET'])
def test_endpoint():
    """Простой эхо-тест"""
    return "✅ Сервер работает! Используйте /test_notification для проверки уведомлений"


@app.route('/test_notification', methods=['GET'])
def test_notification():
    """Отправка тестового уведомления"""
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

        # Формируем тестовое сообщение
        message = (
            f"🚨 *ТЕСТОВЫЙ ЗАКАЗ* #{test_data['order']['order_number']}\n"
            f"📦 **Препарат**: {test_data['order']['medicine']}\n"
            f"🏷 **Количество**: {test_data['order']['quantity']}\n"
            f"📍 **Адрес**: {test_data['order']['delivery_address']}\n"
            f"💊 **Аптека**: {test_data['order'].get('pharmacy', 'Аптека.ру')}\n"
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


# ================ Запуск и конфигурация ================
def setup_telegram():
    """Настройка обработчиков Telegram"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", handle_order))
    application.add_handler(CommandHandler("order", handle_order))
    return application


if __name__ == '__main__':
    # Настройка Telegram бота
    application = setup_telegram()

    # Запускаем бота в режиме polling в основном потоке
    print("🟢 Telegram бот запущен в режиме polling...")
    print("🟢 Flask сервер будет запущен на http://localhost:5000")
    print("Тестовые эндпоинты:")
    print("  http://localhost:5000/test")
    print("  http://localhost:5000/test_notification")

    # Запускаем Flask в отдельном потоке
    import threading


    def run_flask():
        app.run(debug=True, use_reloader=False)


    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Запускаем бота в основном потоке
    application.run_polling()