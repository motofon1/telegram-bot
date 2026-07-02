# config.py
import os

# ============================================
# ТОЧНОЕ НАЗВАНИЕ ВАШЕЙ ТАБЛИЦЫ
# ============================================

# Google Sheets настройки
CREDENTIALS_FILE = "credentials.json"
SHEET_NAME = "Zajavki"  # замените на название вашей таблицы
SHEET_URL = "https://docs.google.com/spreadsheets/d/12NaWy9CnZ0r04xrm7hT0_WgFtssRB38wsRAJeQFkT04/edit"  # ссылка на таблицу

# Telegram настройки (берем из переменных окружения Railway)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Проверяем загрузился ли токен
if not TELEGRAM_TOKEN:
    print("⚠️ ВНИМАНИЕ! Токен не найден в переменных окружения")
    print("📌 Добавьте TELEGRAM_TOKEN в Variables на Railway")
else:
    print("✅ Токен загружен успешно!")

# Остальные настройки...
COLUMN_MAPPING = {
    'ID РК': 'A',
    'ID размещения': 'B',
    'Блогер': 'D',
    'Цена блогера': 'F',
    'Итого': 'G',
    'Уведомления': 'K'
}

DATA_TRANSFORMATIONS = {
    'A': {'type': 'clean_number'},
    'B': {'type': 'clean_number'},
    'D': {'type': 'extract_brackets'},
    'F': {'type': 'clean_number'},
    'G': {'type': 'clean_number'},
    'K': {'type': 'telegram_link', 'base_url': 'https://telegram.me/'}
}

NUMBER_COLUMNS = ['A', 'B', 'F', 'G']

COLUMN_A_SETTINGS = {
    'fill_only_first_row': True,
    'column': 'A'
}

CSV_ENCODING = 'utf-8-sig'
CSV_DELIMITER = ';'
