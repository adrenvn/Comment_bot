#!/usr/bin/env python3
"""
Instagram Automation Bot v2.0
Основной файл запуска бота с поддержкой прокси
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from config import *
from database.connection import init_database
from handlers.commands import start, help_command, add_user, delete_user, add_admin
from handlers.callbacks import button_handler
from handlers.scenarios import handle_text_input
from services.scheduler import check_scheduled_tasks, cleanup_old_data

# Загрузка переменных окружения
load_dotenv()

def setup_logging():
    """Настройка логирования"""
    # Создаём директории для Docker окружения
    for directory in ["./logs", "./data"]:
        if not os.path.exists(directory):
            os.makedirs(directory)

    # Для Docker совместимости
    log_dir = "/app/logs" if os.path.exists("/app") else "./logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "bot.log")),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def main():
    """Основная функция запуска бота"""
    logger = setup_logging()
    
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN не установлен!")
        return
        
    # Инициализация базы данных
    try:
        init_database()
        logger.info("База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
        return
        
    logger.info("🚀 Запуск Instagram Automation Bot v2.0 с поддержкой прокси")
    logger.info(f"📊 Лимиты: {MAX_REQUESTS_PER_HOUR} запросов/час, {MAX_ACTIVE_SCENARIOS} сценариев/пользователь")
    
    # Создание приложения
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавление обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("adduser", add_user))
    application.add_handler(CommandHandler("deleteuser", delete_user))
    application.add_handler(CommandHandler("addadmin", add_admin))
    
    # Обработчики кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_text_input
    ))
    
    # Фоновые задачи
    job_queue = application.job_queue
    job_queue.run_repeating(check_scheduled_tasks, interval=60, first=0)
    job_queue.run_repeating(cleanup_old_data, interval=3600, first=3600)
    
    # Запуск бота
    logger.info("✅ Бот запущен и готов к работе!")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()