from flask import Flask, request, jsonify
import requests
import os
import logging
from dotenv import load_dotenv

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Загрузка переменных окружения
load_dotenv()

# Инициализация приложения
app = Flask(__name__)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'

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

@app.route('/chat', methods=['POST'])
def chat():
    """Обработчик чата для DeepSeek API"""
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
        print(f"Response from DeepSeek API: {response}")  # Логирование в консоль сервера
        return jsonify(response)

    except Exception as e:
        logging.error(f"Chat Error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True
    )