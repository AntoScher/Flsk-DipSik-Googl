from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import uuid
import os
import logging
import json
import re
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Инициализация приложения
app = Flask(__name__)
CORS(app, supports_credentials=True)
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Загрузка промптов
try:
    with open('prompts.json', 'r', encoding='utf-8') as f:
        prompts = json.load(f)
except Exception as e:
    logging.critical(f"Ошибка загрузки промптов: {str(e)}")
    raise

# Конфигурация API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'
CALENDAR_ID = os.getenv("CALENDAR_ID")
SERVICE_ACCOUNT_FILE = 'service-account.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Валидация настроек
if not DEEPSEEK_API_KEY:
    logging.critical("DEEPSEEK_API_KEY не найден в .env")
    raise ValueError("API ключ DeepSeek отсутствует")

if not os.path.exists(SERVICE_ACCOUNT_FILE):
    logging.critical("Файл сервисного аккаунта не найден")
    raise FileNotFoundError("service-account.json отсутствует")

# Глобальные переменные
user_sessions = {}
MAX_SESSIONS = 100


def init_conversation():
    return prompts['medical_assistant']['system'].copy()


def query_deepseek(messages):
    try:
        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': 'deepseek-chat',
            'messages': messages,
            'temperature': 0.3,
            'max_tokens': 500
        }

        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    except Exception as e:
        logging.error(f"Ошибка DeepSeek API: {str(e)}")
        return {'error': prompts['errors']['api_error']}


def create_calendar_event(appointment_details):
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )

        service = build('calendar', 'v3', credentials=creds)

        start_time = datetime.strptime(
            f"{appointment_details['date']} {appointment_details['time']}",
            "%d.%m.%Y %H-%M"
        )

        event = {
            'summary': f'Прием {appointment_details["doctor"]}',
            'description': f'''Пациент: {appointment_details["name"]}
Симптомы: {', '.join(appointment_details["symptoms"])}''',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Europe/Moscow',
            },
            'end': {
                'dateTime': (start_time + timedelta(hours=1)).isoformat(),
                'timeZone': 'Europe/Moscow',
            },
        }

        created_event = service.events().insert(
            calendarId=CALENDAR_ID,
            body=event
        ).execute()

        return {'status': 'success', 'event_id': created_event['id']}

    except Exception as e:
        logging.error(f"Ошибка Google Calendar: {str(e)}")
        return {'status': 'error', 'message': str(e)}


def normalize_text(text):
    replacements = {
        'нз': 'низ', 'врaч': 'врач', 'чеез': 'через',
        'завтрак': 'завтра', 'симпотомы': 'симптомы'
    }
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    return text.lower()


def extract_appointment_details(response):
    try:
        normalized = normalize_text(response)

        patterns = {
            'doctor': r'к\s+([а-яё\s]+?)\s+на',
            'date': r'(\d{1,2}\.\d{1,2}\.\d{4})',
            'time': r'в\s+(\d{1,2}-\d{2})'
        }

        details = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, normalized)
            if not match:
                raise ValueError(f"Не найден {key}")
            details[key] = match.group(1).strip()

        return details
    except Exception as e:
        logging.error(f"Ошибка извлечения: {str(e)}")
        return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    try:
        if not request.is_json:
            return jsonify({'error': prompts['errors']['invalid_format']}), 400

        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': prompts['errors']['empty_message']}), 400
        if len(user_message) > 1000:
            return jsonify({'error': prompts['errors']['long_message']}), 400

        if len(user_sessions) > MAX_SESSIONS:
            user_sessions.clear()
            logging.warning("Очистка сессий")

        session_id = request.cookies.get('session_id')
        if not session_id or session_id not in user_sessions:
            session_id = str(uuid.uuid4())
            user_sessions[session_id] = {
                'history': init_conversation(),
                'step': 'get_name',
                'patient_info': {
                    'name': None,
                    'symptoms': [],
                    'doctor': None,
                    'date': None,
                    'time': None
                }
            }

        session_data = user_sessions[session_id]

        if session_data['step'] == 'get_name':
            if len(user_message.split()) < 2:
                return jsonify({'reply': prompts['medical_assistant']['name_validation'], 'step': 'get_name'})

            session_data['patient_info']['name'] = user_message
            session_data['step'] = 'get_symptoms'
            reply = prompts['medical_assistant']['ask_symptoms']

        elif session_data['step'] == 'get_symptoms':
            session_data['patient_info']['symptoms'].append(user_message)
            prompt = [
                *session_data['history'],
                {"role": "system", "content": prompts['medical_assistant']['diagnosis_guide']}
            ]

            api_response = query_deepseek(prompt)
            if 'error' in api_response:
                return jsonify(api_response), 500

            assistant_response = api_response.get('choices', [{}])[0].get('message', {}).get('content', '')

            if 'предлагаем' in assistant_response.lower():
                details = extract_appointment_details(assistant_response)
                if details:
                    session_data['patient_info'].update(details)
                    session_data['step'] = 'confirm_appointment'
                else:
                    assistant_response = prompts['errors']['parse_error']
            else:
                session_data['step'] = 'clarify_symptoms'

            session_data['history'].append({'role': 'assistant', 'content': assistant_response})
            reply = assistant_response

        elif session_data['step'] == 'clarify_symptoms':
            session_data['patient_info']['symptoms'].append(user_message)
            prompt = [
                *session_data['history'],
                {"role": "system", "content": prompts['medical_assistant']['clarification_guide']}
            ]

            api_response = query_deepseek(prompt)
            if 'error' in api_response:
                return jsonify(api_response), 500

            assistant_response = api_response.get('choices', [{}])[0].get('message', {}).get('content', '')

            if 'предлагаем' in assistant_response.lower():
                details = extract_appointment_details(assistant_response)
                if details:
                    session_data['patient_info'].update(details)
                    session_data['step'] = 'confirm_appointment'
            else:
                session_data['step'] = 'clarify_symptoms'

            session_data['history'].append({'role': 'assistant', 'content': assistant_response})
            reply = assistant_response

        elif session_data['step'] == 'confirm_appointment':
            if 'да' in user_message.lower():
                calendar_response = create_calendar_event(session_data['patient_info'])
                if calendar_response['status'] == 'success':
                    reply = prompts['medical_assistant']['confirmation']
                    del user_sessions[session_id]
                else:
                    reply = prompts['errors']['calendar_error']
            else:
                session_data['step'] = 'reschedule'
                reply = prompts['medical_assistant']['reschedule']

        elif session_data['step'] == 'reschedule':
            if re.match(r'\d{2}\.\d{2}\.\d{4}\s+\d{2}-\d{2}', user_message):
                try:
                    date, time = user_message.split()
                    session_data['patient_info']['date'] = date
                    session_data['patient_info']['time'] = time
                    reply = f"{prompts['medical_assistant']['reschedule_confirm']} {date} {time}"
                    session_data['step'] = 'confirm_appointment'
                except:
                    reply = prompts['errors']['invalid_time_format']
            else:
                reply = prompts['errors']['invalid_time_format']

        response = jsonify({
            'reply': reply,
            'step': session_data['step'],
            'patient_name': session_data['patient_info']['name']
        })

        if not request.cookies.get('session_id'):
            response.set_cookie('session_id', session_id, max_age=300)

        return response

    except Exception as e:
        logging.error(f"Глобальная ошибка: {str(e)}")
        return jsonify({'error': prompts['errors']['server_error']}), 500


if __name__ == '__main__':
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    )