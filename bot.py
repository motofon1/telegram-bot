# bot.py
import os
import io
import pandas as pd
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from csv_uploader import CSVToGoogleSheet
from config import *

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния пользователей
user_data_store = {}

class CSVProcessor:
    def __init__(self):
        self.uploader = CSVToGoogleSheet(CREDENTIALS_FILE, SHEET_NAME)
    
    def process_csv(self, file_content, filename):
        """Обрабатывает CSV файл и возвращает результат"""
        try:
            # Читаем CSV
            df = pd.read_csv(io.BytesIO(file_content), encoding=CSV_ENCODING, delimiter=CSV_DELIMITER)
            df.columns = df.columns.str.strip()
            
            total_rows = len(df)
            logger.info(f"Файл {filename}: прочитано {total_rows} строк")
            
            # Проверяем наличие колонок
            csv_cols = list(COLUMN_MAPPING.keys())
            missing_cols = [col for col in csv_cols if col not in df.columns]
            if missing_cols:
                return {
                    'success': False,
                    'error': f"❌ В CSV отсутствуют колонки: {', '.join(missing_cols)}",
                    'available_columns': ', '.join(df.columns)
                }
            
            # Загружаем в Google Sheets
            result = self.uploader.upload_csv(
                df=df,
                column_mapping=COLUMN_MAPPING,
                transformations=DATA_TRANSFORMATIONS,
                column_a_settings=COLUMN_A_SETTINGS,
                number_columns=NUMBER_COLUMNS
            )
            
            if result:
                return {
                    'success': True,
                    'rows_uploaded': total_rows,
                    'message': f"✅ Успешно загружено {total_rows} строк!"
                }
            else:
                return {
                    'success': False,
                    'error': "❌ Ошибка при загрузке данных"
                }
                
        except Exception as e:
            logger.error(f"Ошибка обработки: {e}")
            return {
                'success': False,
                'error': f"❌ Ошибка: {str(e)}"
            }

# Создаем процессор
processor = CSVProcessor()

# === КОМАНДЫ БОТА ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение"""
    welcome_text = f"""
👋 Привет! Я бот для загрузки данных в Google Таблицу.

📤 **Как работать:**
1. Отправь мне CSV-файл
2. Я проверю данные и загружу их в таблицу
3. Ты получишь уведомление о результате

📊 **Таблица доступна по ссылке:**
[Открыть таблицу]({SHEET_URL})

⚙️ **Формат файла:**
- Разделитель: `{CSV_DELIMITER}`
- Кодировка: `{CSV_ENCODING}`
- Обязательные колонки: ID РК, ID размещения, Блогер, Цена блогера, Итого, Уведомления

📌 Просто отправь файл и я всё сделаю!
"""
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь"""
    help_text = f"""
📖 **Помощь**

1. **Отправь CSV файл** — я загружу его в таблицу
2. **/start** — показать приветствие
3. **/help** — показать это сообщение

📋 **Требования к CSV:**
- Разделитель: `;`
- Кодировка: `UTF-8`
- Колонки: ID РК, ID размещения, Блогер, Цена блогера, Итого, Уведомления

🔗 **Таблица:** [Открыть]({SHEET_URL})
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка полученного файла"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "неизвестно"
    
    # Получаем файл
    document = update.message.document
    if not document.file_name.endswith('.csv'):
        await update.message.reply_text("❌ Пожалуйста, отправьте файл в формате CSV")
        return
    
    # Проверяем размер
    if document.file_size > 10 * 1024 * 1024:  # 10 MB
        await update.message.reply_text("❌ Файл слишком большой (максимум 10 MB)")
        return
    
    # Отправляем сообщение о начале обработки
    processing_msg = await update.message.reply_text(f"🔄 Обрабатываю файл `{document.file_name}`...", parse_mode='Markdown')
    
    try:
        # Скачиваем файл
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        
        # Обрабатываем
        result = processor.process_csv(file_content, document.file_name)
        
        if result['success']:
            # Сохраняем информацию о загрузке
            if user_id not in user_data_store:
                user_data_store[user_id] = {}
            user_data_store[user_id]['last_upload'] = {
                'filename': document.file_name,
                'status': 'success',
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'rows': result['rows_uploaded']
            }
            
            # Успешное сообщение
            await processing_msg.edit_text(
                f"{result['message']}\n\n"
                f"📊 **Файл:** `{document.file_name}`\n"
                f"📈 **Строк:** {result['rows_uploaded']}\n"
                f"🔗 **Таблица:** [Открыть]({SHEET_URL})\n"
                f"📅 **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode='Markdown'
            )
            
        else:
            # Ошибка
            await processing_msg.edit_text(
                f"❌ **Ошибка загрузки:**\n\n{result['error']}\n\n"
                f"📋 **Доступные колонки в файле:**\n{result.get('available_columns', 'неизвестно')}\n\n"
                f"💡 Проверьте, что в CSV есть все нужные колонки",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Ошибка при обработке файла: {e}")
        await processing_msg.edit_text(f"❌ Произошла ошибка при обработке файла: {str(e)}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Попробуйте позже или обратитесь к администратору."
        )

# === ЗАПУСК БОТА ===

def main():
    print("="*60)
    print("🤖 ЗАПУСК TELEGRAM БОТА")
    print("="*60)
    
    # Проверяем наличие токена
    if not TELEGRAM_TOKEN:
        print("❌ Токен бота не найден! Добавьте TELEGRAM_TOKEN в .env файл")
        return
    
    # Проверяем credentials
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ Файл {CREDENTIALS_FILE} не найден!")
        return
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    
    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    print("🤖 Бот запущен!")
    print("📡 Ожидание сообщений...")
    print("="*60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()