#!/usr/bin/env python3
"""
Instagram Automation Bot v2.0
Основной файл запуска бота с поддержкой улучшенной авторизации
ОБНОВЛЕННЫЙ ФАЙЛ bot.py
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update

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

# === НОВЫЕ ОБРАБОТЧИКИ ДЛЯ УЛУЧШЕННОЙ АВТОРИЗАЦИИ ===

async def handle_sms_code_input(update: Update, context):
    """Обработчик ввода SMS кодов"""
    from services.enhanced_auth import handle_sms_code_input as process_sms
    await process_sms(update, context)

async def handle_enhanced_text_input(update: Update, context):
    """Расширенный обработчик текстового ввода"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    from utils.validators import is_user
    if not is_user(user_id):
        await update.message.reply_text("🚫 У вас нет доступа.")
        return

    # === ОБРАБОТКА SMS КОДОВ ===
    if text.isdigit() and len(text) in [4, 5, 6, 8]:
        await handle_sms_code_input(update, context)
        return
    
    # === ОБРАБОТКА КОМАНД АВТОРИЗАЦИИ ===
    auth_commands = {
        'retry': 'retry_now_',
        'повтор': 'retry_now_',
        'switch': 'switch_proxy_',
        'смена': 'switch_proxy_',
        'safe': 'safe_mode_',
        'безопасно': 'safe_mode_',
        'готово': 'challenge_confirmed_',
        'done': 'challenge_confirmed_'
    }
    
    text_lower = text.lower()
    for command, callback_prefix in auth_commands.items():
        if command in text_lower:
            # Ищем активные сценарии пользователя
            from database.models import User, Scenario
            from database.connection import Session
            
            session = Session()
            try:
                user = session.query(User).filter_by(telegram_id=user_id).first()
                if user:
                    active_scenarios = session.query(Scenario).filter_by(
                        user_id=user.id,
                        auth_status='waiting'
                    ).all()
                    
                    if len(active_scenarios) == 1:
                        scenario_id = active_scenarios[0].id
                        captcha_confirmed[f"{callback_prefix.rstrip('_')}_{scenario_id}"] = True
                        
                        command_names = {
                            'retry_now_': '⚡ Быстрый повтор',
                            'switch_proxy_': '🌐 Смена прокси',
                            'safe_mode_': '🛡️ Безопасный режим',
                            'challenge_confirmed_': '✅ Подтверждение готовности'
                        }
                        
                        await update.message.reply_text(
                            f"{command_names.get(callback_prefix, 'Команда')} активирована для сценария #{scenario_id}",
                            reply_to_message_id=update.message.message_id
                        )
                        return
            finally:
                session.close()
    
    # Остальная обработка текста (существующий код)
    await handle_text_input(update, context)

# === ФОНОВЫЕ ЗАДАЧИ ДЛЯ УЛУЧШЕННОЙ АВТОРИЗАЦИИ ===

async def monitor_auth_performance(context):
    """Мониторинг производительности авторизации"""
    try:
        from database.models import AuthenticationLog, ProxyServer, ProxyPerformance
        from database.connection import Session
        from datetime import timedelta
        
        session = Session()
        
        # Обновляем статистику производительности прокси
        hour_ago = datetime.now() - timedelta(hours=1)
        
        auth_logs = session.query(AuthenticationLog).filter(
            AuthenticationLog.created_at >= hour_ago
        ).all()
        
        # Группируем по прокси
        proxy_stats = {}
        for log in auth_logs:
            if log.proxy_used:
                if log.proxy_used not in proxy_stats:
                    proxy_stats[log.proxy_used] = {'attempts': 0, 'successes': 0, 'challenges': 0}
                
                proxy_stats[log.proxy_used]['attempts'] += 1
                if log.success:
                    proxy_stats[log.proxy_used]['successes'] += 1
                if log.challenge_type:
                    proxy_stats[log.proxy_used]['challenges'] += 1
        
        # Обновляем записи производительности
        for proxy_name, stats in proxy_stats.items():
            proxy = session.query(ProxyServer).filter_by(name=proxy_name).first()
            if proxy:
                perf = session.query(ProxyPerformance).filter_by(proxy_id=proxy.id).first()
                if not perf:
                    perf = ProxyPerformance(proxy_id=proxy.id)
                    session.add(perf)
                
                perf.auth_attempts += stats['attempts']
                perf.auth_successes += stats['successes']
                
                if stats['attempts'] > 0:
                    perf.challenge_rate = stats['challenges'] / stats['attempts']
                
                if stats['successes'] > 0:
                    perf.last_success = datetime.now()
                elif stats['attempts'] > stats['successes']:
                    perf.last_failure = datetime.now()
        
        session.commit()
        session.close()
        
        logger.info("Обновлена статистика производительности авторизации")
        
    except Exception as e:
        logger.error(f"Ошибка мониторинга авторизации: {e}")

async def cleanup_auth_sessions(context):
    """Очистка старых сессий авторизации"""
    try:
        import time
        from database.models import ChallengeSession
        from database.connection import Session
        from datetime import timedelta
        
        # Очищаем старые callback данные
        current_time = time.time()
        expired_keys = []
        
        for key in list(captcha_confirmed.keys()):
            # Удаляем записи старше 2 часов
            if key.startswith(('challenge_', 'sms_', 'retry_', 'switch_', 'safe_')):
                expired_keys.append(key)
        
        for key in expired_keys:
            captcha_confirmed.pop(key, None)
        
        # Очищаем старые сессии challenge
        session = Session()
        try:
            old_challenges = session.query(ChallengeSession).filter(
                ChallengeSession.started_at < datetime.now() - timedelta(hours=4),
                ChallengeSession.status == 'active'
            ).all()
            
            for challenge in old_challenges:
                challenge.status = 'timeout'
            
            session.commit()
            
            if expired_keys or old_challenges:
                logger.info(f"Очищено {len(expired_keys)} callback'ов и {len(old_challenges)} старых challenge сессий")
                
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Ошибка очистки сессий авторизации: {e}")

async def notify_auth_issues(context):
    """Уведомление о проблемах с авторизацией"""
    try:
        from database.models import Scenario, Admin
        from database.connection import Session
        
        session = Session()
        
        # Подсчитываем статистику
        total_scenarios = session.query(Scenario).count()
        auth_success = session.query(Scenario).filter_by(auth_status='success').count()
        auth_failed = session.query(Scenario).filter_by(auth_status='failed').count()
        
        if total_scenarios > 10:  # Только если есть достаточно данных
            success_rate = (auth_success / total_scenarios) * 100
            
            # Если много неудачных авторизаций
            if success_rate < 70:
                admins = session.query(Admin).all()
                
                alert_text = (
                    f"⚠️ <b>Проблемы с авторизацией</b>\n\n"
                    f"📊 Успешность: {success_rate:.1f}%\n"
                    f"❌ Неудач: {auth_failed}\n"
                    f"✅ Успешно: {auth_success}\n\n"
                    f"🔧 Рекомендуется проверить настройки прокси и авторизации."
                )
                
                # Отправляем уведомление админам
                bot = context.bot
                
                for admin in admins:
                    try:
                        await bot.send_message(
                            chat_id=admin.telegram_id,
                            text=alert_text,
                            parse_mode='HTML'
                        )
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления админу {admin.telegram_id}: {e}")
        
        session.close()
                
    except Exception as e:
        logger.error(f"Ошибка проверки статистики авторизации: {e}")

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
        
    logger.info("🚀 Запуск Instagram Automation Bot v2.0 с улучшенной авторизацией")
    logger.info(f"📊 Лимиты: {MAX_REQUESTS_PER_HOUR} запросов/час, {MAX_ACTIVE_SCENARIOS} сценариев/пользователь")
    logger.info(f"⚡ Улучшенная авторизация: {MAX_FAST_ATTEMPTS} быстрых попыток × {FAST_RETRY_DELAY//60} мин")
    
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
    
    # === НОВЫЕ ОБРАБОТЧИКИ ДЛЯ УЛУЧШЕННОЙ АВТОРИЗАЦИИ ===
    
    # Обработчик SMS кодов (приоритет выше)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r'^\d{4,8}),
        handle_sms_code_input
    ))
    
    # Обработчик текстовых сообщений (расширенный)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_enhanced_text_input
    ))
    
    # Фоновые задачи
    job_queue = application.job_queue
    
    # Существующие задачи
    job_queue.run_repeating(check_scheduled_tasks, interval=60, first=0)
    job_queue.run_repeating(cleanup_old_data, interval=3600, first=3600)
    
    # === НОВЫЕ ФОНОВЫЕ ЗАДАЧИ ДЛЯ УЛУЧШЕННОЙ АВТОРИЗАЦИИ ===
    
    # Мониторинг авторизации - каждые 15 минут
    job_queue.run_repeating(
        monitor_auth_performance, 
        interval=900, 
        first=300,
        name="monitor_auth_performance"
    )
    
    # Очистка старых сессий авторизации - каждый час
    job_queue.run_repeating(
        cleanup_auth_sessions, 
        interval=3600, 
        first=1800,
        name="cleanup_auth_sessions"
    )
    
    # Уведомления о проблемах авторизации - каждые 4 часа
    job_queue.run_repeating(
        notify_auth_issues, 
        interval=14400, 
        first=7200,
        name="auth_issues_notifications"
    )
    
    # Запуск бота
    logger.info("✅ Бот запущен с улучшенной авторизацией и готов к работе!")
    logger.info("🔧 Новые возможности:")
    logger.info("   • ⚡ Быстрые попытки авторизации (2 мин)")
    logger.info("   • 📱 Ввод SMS кодов прямо в боте") 
    logger.info("   • 🌐 Автоматическая смена прокси")
    logger.info("   • 🛡️ Безопасный режим без прокси")
    logger.info("   • 📊 Детальная аналитика авторизации")
    
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()