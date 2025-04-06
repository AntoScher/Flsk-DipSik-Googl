from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO, emit
import requests  # Используем requests вместо httpx
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default-secret-key')
socketio = SocketIO(app)

# Конфигурация для DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


# Маршрут для проверки работоспособности сервера
@app.route('/core')
def index():
    return render_template('core.html')  # Вместо jsonify


# WebSocket-маршрут для чата
@socketio.on('connect')
def handle_connect():
    print("Client connected")


@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")


@socketio.on('chat_message')
def handle_chat_message(prompt):
    """
    Обработка входящего сообщения от клиента через WebSocket.
    Отправка запроса в DeepSeek API и возврат ответа клиенту.
    """
    if not prompt:
        emit('response', {'error': "Prompt is required"})
        return

    try:
        # Вызов DeepSeek API с использованием requests
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}]
        }

        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)

        if response.status_code == 200:
            answer = response.json()["choices"][0]["message"]["content"]
            emit('response', {'answer': answer})
        else:
            error_message = f"Error {response.status_code}: {response.text}"
            emit('response', {'error': error_message})

    except requests.exceptions.RequestException as e:
        emit('response', {'error': f"Request failed: {str(e)}"})
    except Exception as e:
        emit('response', {'error': f"Internal server error: {str(e)}"})

if __name__ == '__main__':
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True  # Добавьте этот параметр
    )