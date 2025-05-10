import requests
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Проверяем наличие API-ключа
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY не найдена в .env файле")

# Адрес API
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions "

# Тело запроса
data = {
    "model": "deepseek-chat",
    "messages": [
        {
            "role": "user",
            "content": "Привет! Отвечай на русском языке. Как дела? Расскажи о себе."
        }
    ],
    "max_tokens": 500
}

# Заголовки
headers = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json"
}

# Отправляем запрос
response = requests.post(DEEPSEEK_API_URL, json=data, headers=headers)

# Проверяем статус ответа
if response.status_code == 200:
    # Получаем ответ от модели
    model_response = response.json()["choices"][0]["message"]["content"]
    print("Ответ от ИИ:\n", model_response)
else:
    print("Ошибка:", response.status_code)
    print(response.text)