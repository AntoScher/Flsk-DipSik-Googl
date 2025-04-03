from flask import Flask, request, jsonify, render_template
from flask_wtf.csrf import CSRFProtect
import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests
import os
from dotenv import load_dotenv
import logging

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Загрузка переменных окружения
load_dotenv()

# Инициализация приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default-secret-key')
csrf = CSRFProtect(app)

# Конфигурация API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
RANGE_NAME = 'Sheet1!A1:D4'
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'


def google_auth():
    """Аутентификация в Google Sheets API"""
    creds = None
    try:
        if os.path.exists('__token.json'):
            creds = Credentials.from_authorized_user_file('__token.json', SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    raise FileNotFoundError("credentials.json not found")

                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

            with open('__token.json', 'w') as token_file:
                token_file.write(creds.to_json())

        return creds

    except Exception as e:
        logging.error(f"Google Auth Error: {str(e)}")
        raise


def get_sheet_data():
    """Получение данных из Google Sheets"""
    try:
        service = build('sheets', 'v4', credentials=google_auth())
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME
        ).execute()
        return result.get('values', [])

    except HttpError as e:
        logging.error(f"Google Sheets API Error: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"General Error: {str(e)}")
        return []


def query_deepseek(prompt):
    """Запрос к DeepSeek API"""
    try:
        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            'model': 'deepseek-chat',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 500
        }

        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        return response.json()

    except Exception as e:
        logging.error(f"DeepSeek API Error: {str(e)}")
        return {'error': str(e)}


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
@csrf.exempt
def chat():
    """Обработчик чата"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Invalid content type'}), 415

        data = request.get_json()
        message = data.get('message', '').strip()

        if not message:
            return jsonify({'error': 'Empty message'}), 400
        if len(message) > 1000:
            return jsonify({'error': 'Message too long'}), 400

        response = query_deepseek(message)
        return jsonify(response)

    except Exception as e:
        logging.error(f"Chat Error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/generate_report', methods=['GET'])
def generate_report():
    """Генерация отчета"""
    try:
        data = get_sheet_data()
        print(f"Получены данные из таблицы: {data}")  # Добавьте эту строку
        if not data:
            return jsonify({'error': 'No data found in sheet'}), 404

        response = query_deepseek(f"Сгенерируй рецепт на лекарства на основе симптомов: {data}")
        return jsonify(response)

    except Exception as e:
        logging.error(f"Report Generation Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/appoint', methods=['GET'])
def appoint():
    """назначение визита"""
    try:
        data = get_sheet_data()
        if not data:
            return jsonify({'error': 'No data found in sheet'}), 404

        response = query_deepseek(f"Назначь дату и время визита: {data}")
        return jsonify(response)

    except Exception as e:
        logging.error(f"appoint Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,
        ssl_context=None
    )