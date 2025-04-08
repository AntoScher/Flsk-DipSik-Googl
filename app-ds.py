from flask import Flask, render_template, request, jsonify, Response
from openai import OpenAI
import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timezone, timedelta
import json

load_dotenv()

app = Flask(__name__)

# DeepSeek API клиент
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# Google Calendar API настройки
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_JSON')
CALENDAR_ID = os.getenv('CALENDAR_ID')


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data['message']
    messages = data.get('messages', [])

    messages.append({"role": "user", "content": user_message})

    stream = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream=True
    )

    def generate():
        full_response = []
        for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            full_response.append(content)
            yield f"data: {json.dumps({'content': content})}\n\n"

        messages.append({"role": "assistant", "content": "".join(full_response)})
        yield f"data: {json.dumps({'done': True, 'messages': messages})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@app.route('/create_event', methods=['POST'])
def create_event():
    data = request.get_json()
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        service = build('calendar', 'v3', credentials=credentials)

        event = {
            'summary': data['summary'],
            'start': {
                'dateTime': data['start_datetime'],
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': data['end_datetime'],
                'timeZone': 'UTC'
            },
        }

        service.events().insert(
            calendarId=CALENDAR_ID,
            body=event
        ).execute()

        return jsonify({'status': 'success', 'message': 'Событие создано!'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)