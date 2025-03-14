Проект на Flask, взаимодействует с Google Sheets и DeepSeek API. Есть три роута: /chat, /generate_report, /analytics.
Функция authenticate_google_sheets проверяет наличие токена и обновляет его при необходимости. 
Затем get_sheet_data получает данные из таблицы. query_deepseek отправляет запросы к DeepSeek API. 
В роутах обрабатываются POST и GET запросы: чат принимает сообщение и возвращает ответ от DeepSeek, 
а два других роута генерируют отчет и аналитику на основе данных из Google Sheets.
Основные функции:
Чат-бот: Обрабатывает текстовые запросы через /chat, используя DeepSeek API.
Генерация отчетов: Извлекает данные из Google Sheets и отправляет их в DeepSeek для формирования отчета (/generate_report).
Аналитика данных: Анализирует данные таблицы через DeepSeek (/analytics).
Ключевые компоненты:
authenticate_google_sheets(): Авторизация в Google Sheets API через OAuth 2.0.
get_sheet_data(): Получение данных из таблицы (A1:D10).
query_deepseek(): Отправка запросов к DeepSeek API.
Роуты /chat (POST), /generate_report (GET), /analytics (GET).

