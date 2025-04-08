import os
from datetime import datetime, timezone, timedelta

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Импорт для работы с DeepSeek API (обёртка в виде OpenAI)
from openai import OpenAI

# Импорты для Google Calendar API
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)

# Настройка клиента для работы с DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# Глобальная история сообщений для диалога (для демонстрации; для продакшена стоит привязать к сессии пользователя)
messages = [{"role": "system", "content": "You are a helpful assistant."}]

def create_calendar_event(summary, start_datetime, end_datetime):
    """
    Создает событие в Google Календаре по заданным параметрам.
    """
    try:
        sa_path = os.getenv('SERVICE_ACCOUNT_JSON')
        calendar_id = os.getenv('CALENDAR_ID')

        credentials = service_account.Credentials.from_service_account_file(
            sa_path,
            scopes=['https://www.googleapis.com/auth/calendar']
        )

        service = build('calendar', 'v3', credentials=credentials)

        event = {
            'summary': summary,
            'start': {'dateTime': start_datetime.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': end_datetime.isoformat(), 'timeZone': 'UTC'},
        }

        service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()

        print("✅ Событие успешно создано!")
        return True

    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        return False

@app.route('/')
def index():
    """
    Главная страница, которая рендерит веб-интерфейс для чата.
    В шаблоне (templates/index.html) можно разместить форму для отправки сообщений.
    """
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """
    Эндпоинт для общения с DeepSeek Chat API.
    Принимает сообщение пользователя, отправляет его вместе с историей сообщений к DeepSeek,
    собирает ответ и возвращает его в формате JSON.
    """
    user_input = request.form.get("user_input")
    if not user_input:
        return jsonify({"error": "Пустой ввод пользователя"}), 400

    messages.append({"role": "user", "content": user_input})
    try:
        stream = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=True
        )
        full_response = []
        # Проходим по потоковым чанкам и собираем ответ
        for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            full_response.append(content)
        assistant_response = "".join(full_response)
        messages.append({"role": "assistant", "content": assistant_response})
        return jsonify({"response": assistant_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/create_event', methods=['POST'])
def create_event():
    """
    Эндпоинт для создания события в Google Календаре.
    Ожидает JSON с полями:
      - summary: описание события
      - start: начало события в формате ISO (например, "2025-04-09T14:00:00")
      - end: окончание события в формате ISO
    """
    data = request.get_json()
    summary = data.get("summary")
    start_str = data.get("start")
    end_str = data.get("end")

    if not summary or not start_str or not end_str:
        return jsonify({"error": "Не указаны необходимые поля: summary, start и end"}), 400

    try:
        start_dt = datetime.fromisoformat(start_str)
        end_dt = datetime.fromisoformat(end_str)
    except Exception as e:
        return jsonify({"error": "Неверный формат даты. Используйте ISO-формат."}), 400

    if create_calendar_event(summary, start_dt, end_dt):
        return jsonify({"message": "Событие успешно создано!"})
    else:
        return jsonify({"error": "Ошибка при создании события."}), 500

if __name__ == '__main__':
    app.run(debug=True)