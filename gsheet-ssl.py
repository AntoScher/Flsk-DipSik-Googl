import os
import ssl
import certifi
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Установка пути к сертификатам
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# Временное отключение проверки SSL (раскомментируйте, если другие методы не работают)
ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv()
SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def main():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Ошибка обновления токена: {e}")
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    try:
        range_name = 'Tasks!A1:D4'
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
        values = result.get('values', [])
        print("Данные из таблицы:", values)
    except Exception as e:
        print(f"Ошибка при чтении данных: {e}")

if __name__ == '__main__':
    main()