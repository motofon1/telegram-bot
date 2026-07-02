# csv_uploader.py
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import re

class CSVToGoogleSheet:
    def __init__(self, credentials_file, sheet_name):
        """Подключение к Google Sheets"""
        self.credentials_file = credentials_file
        self.sheet_name = sheet_name
        
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
        
        # Пытаемся получить credentials из переменной окружения (для Railway)
        creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        if creds_json:
            print("✅ Используем credentials из переменной окружения GOOGLE_CREDENTIALS")
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            # fallback на файл (для локальной разработки)
            print(f"📂 Используем credentials из файла: {credentials_file}")
            if not os.path.exists(credentials_file):
                print(f"❌ Файл {credentials_file} не найден!")
                print("📌 Добавьте GOOGLE_CREDENTIALS в переменные окружения Railway")
                raise FileNotFoundError(f"Файл {credentials_file} не найден")
            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open(sheet_name)
        self.worksheet = self.sheet.sheet1
        
        print(f"✅ Подключено к Google таблице: {sheet_name}")
        print(f"📊 Лист: {self.worksheet.title}")
    
    def _transform_value(self, value, transformation_config):
        """Преобразует значение согласно настройкам"""
        if not value or pd.isna(value):
            return ''
        
        value_str = str(value).strip()
        if not value_str:
            return ''
        
        transform_type = transformation_config.get('type')
        
        if transform_type == 'telegram_link':
            base_url = transformation_config.get('base_url', 'https://telegram.me/')
            username = value_str.lstrip('@')
            return f'{base_url}{username}'
        
        elif transform_type == 'extract_brackets':
            match = re.search(r'\(([^)]+)\)', value_str)
            if match:
                return match.group(1).strip()
            return value_str
        
        elif transform_type == 'clean_number':
            cleaned = value_str.replace("'", "").replace(' ', '').replace(',', '.')
            try:
                if '.' in cleaned:
                    num = float(cleaned)
                    if num.is_integer():
                        return str(int(num))
                    return str(num)
                else:
                    return str(int(cleaned))
            except (ValueError, TypeError):
                return cleaned
        
        return value_str
    
    def upload_csv(self, df=None, column_mapping=None, transformations=None, 
                   column_a_settings=None, number_columns=None):
        """Загружает данные из DataFrame в Google Sheets"""
        
        if df is None:
            return False
        
        print(f"📊 Обработка {len(df)} строк")
        
        MAX_COL = 11
        
        # Проверяем наличие колонок
        csv_cols = list(column_mapping.keys())
        missing_cols = [col for col in csv_cols if col not in df.columns]
        if missing_cols:
            print(f"❌ В данных отсутствуют колонки: {missing_cols}")
            return False
        
        existing_data = self.worksheet.get_all_values()
        current_rows = len(existing_data)
        
        if current_rows == 0:
            print(f"📋 Создаем заголовки...")
            header_row = [''] * MAX_COL
            for csv_col, gsheet_col in column_mapping.items():
                col_num = self._column_letter_to_number(gsheet_col) - 1
                header_row[col_num] = csv_col
            self.worksheet.update('A1', [header_row])
            current_rows = 1
        
        print(f"📤 Подготавливаем данные...")
        rows_to_upload = []
        
        fill_a_only_first = False
        a_column = 'A'
        if column_a_settings and column_a_settings.get('fill_only_first_row', False):
            fill_a_only_first = True
            a_column = column_a_settings.get('column', 'A')
            print(f"📌 Настройка: колонка {a_column} заполняется только в первой строке")
        
        if number_columns is None:
            number_columns = ['F', 'G']
        
        print(f"📊 Числовые колонки: {', '.join(number_columns)}")
        
        for idx, (_, row) in enumerate(df.iterrows(), 1):
            new_row = [''] * MAX_COL
            
            for csv_col, gsheet_col in column_mapping.items():
                col_num = self._column_letter_to_number(gsheet_col) - 1
                value = row[csv_col]
                
                if fill_a_only_first and gsheet_col == a_column:
                    if idx == 1:
                        clean_value = str(value).replace("'", "").strip()
                        try:
                            if '.' in clean_value:
                                num = float(clean_value)
                                if num.is_integer():
                                    clean_value = int(num)
                                else:
                                    clean_value = num
                            else:
                                clean_value = int(clean_value)
                        except (ValueError, TypeError):
                            pass
                        new_row[col_num] = clean_value if not pd.isna(clean_value) else ''
                    else:
                        new_row[col_num] = ''
                    continue
                
                if transformations and gsheet_col in transformations:
                    value = self._transform_value(value, transformations[gsheet_col])
                
                if gsheet_col in number_columns and value:
                    try:
                        if isinstance(value, str):
                            cleaned = value.replace("'", "").replace(' ', '').replace(',', '.')
                            if '.' in cleaned:
                                num = float(cleaned)
                                if num.is_integer():
                                    value = int(num)
                                else:
                                    value = num
                            else:
                                value = int(cleaned)
                    except (ValueError, TypeError):
                        pass
                
                new_row[col_num] = value if not pd.isna(value) else ''
            
            rows_to_upload.append(new_row)
        
        start_row = current_rows + 1
        try:
            self.worksheet.update(f'A{start_row}', rows_to_upload)
            
            for col in number_columns:
                try:
                    self.worksheet.format(
                        f'{col}{start_row}:{col}{start_row + len(rows_to_upload) - 1}',
                        {"numberFormat": {"type": "NUMBER", "pattern": "#0"}}
                    )
                    print(f"📊 Применен числовой формат для колонки {col}")
                except Exception as e:
                    print(f"⚠️ Не удалось применить числовой формат для колонки {col}: {e}")
            
            print(f"✅ Успешно загружено {len(rows_to_upload)} строк")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            return False
    
    def _column_letter_to_number(self, letter):
        """Преобразует букву колонки в номер (A=1, B=2, ...)"""
        number = 0
        for char in letter:
            number = number * 26 + (ord(char.upper()) - ord('A') + 1)
        return number
