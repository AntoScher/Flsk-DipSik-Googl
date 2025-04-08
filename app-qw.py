from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timezone, timedelta

load_dotenv()

app = Flask(__name__)

# Инициализация DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
messages = [{"role": "system", "content": "You are a helpful assistant."}]

# Инициализация Google Calendar
SERVICE_ACCOUNT_JSON = os.getenv('SERVICE_ACCOUNT_JSON')
CALENDAR_ID = os.getenv('CALENDAR_ID')


@app.route('/')
def core():
    return render_template('core.html')


@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')

    # Добавляем пользовательское сообщение
    messages.append({"role": "user", "content": user_input})

    try:
        # Получаем ответ от DeepSeek
        stream = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=True
        )

        full_response = []
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
    data = request.json
    summary = data.get('summary')
    start_str = data.get('start_datetime')
    end_str = data.get('end_datetime')

    try:
        # Преобразуем строки в datetime объекты
        start = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)

        # Создаем событие
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_JSON,
            scopes=['https://www.googleapis.com/auth/calendar']
        )

        service = build('calendar', 'v3', credentials=credentials)

        event = {
            'summary': summary,
            'start': {'dateTime': start.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': end.isoformat(), 'timeZone': 'UTC'},
        }

        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)