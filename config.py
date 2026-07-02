# config.py
import os

# ============================================
# Google Sheets настройки
# ============================================

# Google Sheets настройки
CREDENTIALS_FILE = "credentials.json"
SHEET_NAME = "Zajavki"  # замените на название вашей таблицы
SHEET_URL = "https://docs.google.com/spreadsheets/d/12NaWy9CnZ0r04xrm7hT0_WgFtssRB38wsRAJeQFkT04/edit"  # ссылка на таблицу

# ============================================
# Telegram настройки (из переменных окружения)
# ============================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    print("⚠️ ВНИМАНИЕ! Токен не найден в переменных окружения")
    print("📌 Добавьте TELEGRAM_TOKEN в Variables на Railway")
else:
    print("✅ Токен загружен успешно!")

# ============================================
# МАППИНГ КОЛОНОК
# ============================================

COLUMN_MAPPING = {
    'ID РК': 'A',
    'ID размещения': 'B',
    'Блогер': 'D',
    'Цена блогера': 'F',
    'Итого': 'G',
    'Уведомления': 'K'
}

# ============================================
# ПРЕОБРАЗОВАНИЯ ДАННЫХ
# ============================================

DATA_TRANSFORMATIONS = {
    'A': {'type': 'clean_number'},
    'B': {'type': 'clean_number'},
    'D': {'type': 'extract_brackets'},
    'F': {'type': 'clean_number'},
    'G': {'type': 'clean_number'},
    'K': {'type': 'telegram_link', 'base_url': 'https://telegram.me/'}
}

# ============================================
# ЧИСЛОВЫЕ КОЛОНКИ
# ============================================

NUMBER_COLUMNS = ['A', 'B', 'F', 'G']

# ============================================
# НАСТРОЙКИ КОЛОНКИ A
# ============================================

COLUMN_A_SETTINGS = {
    'fill_only_first_row': True,
    'column': 'A'
}

# ============================================
# НАСТРОЙКИ CSV
# ============================================

CSV_ENCODING = 'utf-8-sig'
CSV_DELIMITER = ';'
