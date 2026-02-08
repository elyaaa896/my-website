import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# Настройка доступа
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
spreadsheet = client.open("moviesbot_base")

def migrate():
    # 1. Перенос основного списка (твои 140+ фильмов)
    sheet_main = spreadsheet.worksheet("main")
    with open('movies_db.json', 'r', encoding='utf-8') as f:
        main_data = json.load(f)
    
    rows_main = []
    for m in main_data:
        rows_main.append([m.get('name', ''), m.get('status', '⏳'), m.get('series', '')])
    
    sheet_main.append_rows(rows_main)
    print(f"✅ Перенесено {len(rows_main)} фильмов в таблицу 'main'")

    # 2. Перенос ВСЕХ списков пользователей
    sheet_users = spreadsheet.worksheet("users")
    user_rows = []
    
    # Ищем все файлы, начинающиеся на 'list_'
    for filename in os.listdir('.'):
        if filename.startswith('list_') and filename.endswith('.json'):
            user_id = filename.replace('list_', '').replace('.json', '')
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for m in data:
                    user_rows.append([user_id, m.get('name', ''), m.get('status', '⏳'), m.get('series', '')])
    
    if user_rows:
        sheet_users.append_rows(user_rows)
        print(f"✅ Перенесено {len(user_rows)} записей пользователей в таблицу 'users'")

if __name__ == "__main__":
    migrate()
