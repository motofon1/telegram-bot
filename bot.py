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

class CSVProcessor:
    def __init__(self):
        self.uploader = CSVToGoogleSheet(CREDENTIALS_FILE, SHEET_NAME)
    
    def process_csv(self, file_content, filename):
        try:
            df = pd.read_csv(io.BytesIO(file_content), encoding=CSV_ENCODING, delimiter=CSV_DELIMITER)
            df.columns = df.columns.str.strip()
            
            total_rows = len(df)
            logger.info(f"Файл {filename}: прочитано {total_rows} строк")
            
            csv_cols = list(COLUMN_MAPPING.keys())
            missing_cols = [col for col in csv_cols if col not in df.columns]
            if missing_cols:
                return {
                    'success': False,
                    'error': f"❌ В CSV отсутствуют колонки: {', '.join(missing_cols)}",
                    'available_columns': ', '.join(df.columns)
                }
            
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

processor = CSVProcessor()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = f"""
👋 Привет! Я бот для загрузки данных в Google Таблицу.

📤 **Как работать:**
1. Отправь мне CSV-файл
2. Я проверю данные и загружу их в таблицу
3. Ты получишь уведомление о результате

📊 **Таблица:** [Открыть]({SHEET_URL})

📌 Просто отправь файл и я всё сделаю!
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = f"""
📖 **Помощь**

1. **Отправь CSV файл** — я загружу его в таблицу
2. **/start** — показать приветствие
3. **/help** — показать это сообщение

🔗 **Таблица:** [Открыть]({SHEET_URL})
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith('.csv'):
        await update.message.reply_text("❌ Пожалуйста, отправьте файл в формате CSV")
        return
    
    if document.file_size > 10 * 1024 * 1024:
        await update.message.reply_text("❌ Файл слишком большой (максимум 10 MB)")
        return
    
    processing_msg = await update.message.reply_text(f"🔄 Обрабатываю файл `{document.file_name}`...", parse_mode='Markdown')
    
    try:
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        
        result = processor.process_csv(file_content, document.file_name)
        
        if result['success']:
            await processing_msg.edit_text(
                f"{result['message']}\n\n"
                f"📊 **Файл:** `{document.file_name}`\n"
                f"📈 **Строк:** {result['rows_uploaded']}\n"
                f"🔗 **Таблица:** [Открыть]({SHEET_URL})\n"
                f"📅 **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode='Markdown'
            )
        else:
            await processing_msg.edit_text(
                f"❌ **Ошибка загрузки:**\n\n{result['error']}",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Ошибка при обработке файла: {e}")
        await processing_msg.edit_text(f"❌ Произошла ошибка: {str(e)}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Попробуйте позже."
        )

def main():
    print("="*60)
    print("🤖 ЗАПУСК TELEGRAM БОТА")
    print("="*60)
    
    if not TELEGRAM_TOKEN:
        print("❌ Токен бота не найден!")
        print("📌 Установите переменную окружения TELEGRAM_TOKEN")
        return
    
    # Убираем проверку файла credentials.json!
    # Он будет загружен из переменной окружения GOOGLE_CREDENTIALS
    
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
        application.add_error_handler(error_handler)
        
        print("🤖 Бот запущен! Ожидание сообщений...")
        print("="*60)
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
