#!/usr/bin/env python3
"""
Instagram Automation Bot v2.0 с поддержкой TikTok
Обновленный основной файл запуска бота
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
from handlers.tiktok_handlers import handle_tiktok_text_input, handle_tiktok_callbacks
from services.scheduler import check_scheduled_tasks, cleanup_old_data
from services.tiktok_processor import scheduled_tiktok_cleanup, restart_failed_tiktok_scenarios

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

# === ОБРАБОТЧИКИ ТЕКСТОВОГО ВВОДА ===

async def handle_enhanced_text_input(update: Update, context):
    """Расширенный обработчик текстового ввода с поддержкой TikTok"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    from utils.validators import is_user
    if not is_user(user_id):
        await update.message.reply_text("🚫 У вас нет доступа.")
        return

    # Проверяем, это TikTok сценарий
    if context.user_data.get('platform') == 'tiktok':
        handled = await handle_tiktok_text_input(update, context)
        if handled:
            return

    # === ОБРАБОТКА SMS КОДОВ ===
    if text.isdigit() and len(text) in [4, 5, 6, 8]:
        from services.enhanced_auth import handle_sms_code_input
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
    
    # Остальная обработка текста (Instagram сценарии)
    await handle_text_input(update, context)

# === ПЛАТФОРМЕННЫЕ CALLBACK ОБРАБОТЧИКИ ===

async def handle_platform_callbacks(update: Update, context):
    """Обработчик callback'ов для выбора платформы"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    from utils.validators import is_admin, is_user
    if not is_admin(user_id) and not is_user(user_id):
        await query.edit_message_text("🚫 У вас нет доступа к боту.")
        return

    is_admin_user = is_admin(user_id)
    is_user_user = is_user(user_id)

    try:
        # === ПЛАТФОРМЕННАЯ НАВИГАЦИЯ ===
        if data == 'platforms_menu':
            from ui.menus import platforms_menu
            await query.edit_message_text(
                "🚀 <b>Выберите платформу:</b>\n\n"
                "📸 Instagram - классическая автоматизация\n"
                "🎵 TikTok - новые возможности",
                parse_mode='HTML',
                reply_markup=platforms_menu()
            )
            
        elif data == 'instagram_scenarios':
            from ui.menus import scenarios_menu
            await query.edit_message_text(
                "📸 <b>Instagram автоматизация:</b>\n\n"
                "• Мониторинг комментариев постов\n"
                "• Автоматические DM сообщения\n"
                "• Поддержка прокси серверов\n"
                "• Обход ограничений Instagram",
                parse_mode='HTML',
                reply_markup=scenarios_menu()
            )
            
        elif data == 'tiktok_scenarios':
            if not ENABLE_TIKTOK:
                await query.edit_message_text(
                    "❌ <b>TikTok функционал отключен</b>\n\n"
                    "Обратитесь к администратору для активации.",
                    parse_mode='HTML'
                )
                return
                
            from ui.menus import tiktok_scenarios_menu
            await query.edit_message_text(
                "🎵 <b>TikTok автоматизация:</b>\n\n"
                "• Мониторинг комментариев к видео\n"
                "• Автоматические DM в TikTok\n"
                "• Обход системы защиты TikTok\n"
                "• Playwright для стабильности",
                parse_mode='HTML',
                reply_markup=tiktok_scenarios_menu()
            )
        
        # === TIKTOK CALLBACK'Ы ===
        elif data.startswith(('add_tiktok_', 'my_tiktok_', 'tiktok_', 'manage_tiktok_', 
                            'check_tiktok_', 'send_tiktok_', 'pause_tiktok_', 
                            'resume_tiktok_', 'restart_tiktok_', 'delete_tiktok_', 
                            'confirm_delete_tiktok_', 'select_tiktok_')):
            await handle_tiktok_callbacks(update, context)
        
        else:
            # Передаем обычным обработчикам
            await button_handler(update, context)
            
    except Exception as e:
        logger.error(f"Ошибка в обработчике платформенных callback'ов: {e}")
        await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")

# === ФОНОВЫЕ ЗАДАЧИ ===

async def monitor_auth_performance(context):
    """Мониторинг производительности авторизации (Instagram + TikTok)"""
    try:
        from database.models import AuthenticationLog, TikTokAuthenticationLog, ProxyServer, ProxyPerformance
        from database.connection import Session
        from datetime import timedelta
        
        session = Session()
        
        # Обновляем статистику производительности прокси
        hour_ago = datetime.now() - timedelta(hours=1)
        
        # Instagram статистика
        ig_auth_logs = session.query(AuthenticationLog).filter(
            AuthenticationLog.created_at >= hour_ago
        ).all()
        
        # TikTok статистика
        tiktok_auth_logs = session.query(TikTokAuthenticationLog).filter(
            TikTokAuthenticationLog.created_at >= hour_ago
        ).all()
        
        # Группируем по прокси
        proxy_stats = {}
        
        # Обрабатываем Instagram логи
        for log in ig_auth_logs:
            if log.proxy_used:
                if log.proxy_used not in proxy_stats:
                    proxy_stats[log.proxy_used] = {
                        'ig_attempts': 0, 'ig_successes': 0, 'ig_challenges': 0,
                        'tiktok_attempts': 0, 'tiktok_successes': 0, 'tiktok_challenges': 0
                    }
                
                proxy_stats[log.proxy_used]['ig_attempts'] += 1
                if log.success:
                    proxy_stats[log.proxy_used]['ig_successes'] += 1
                if log.challenge_type:
                    proxy_stats[log.proxy_used]['ig_challenges'] += 1
        
        # Обрабатываем TikTok логи
        for log in tiktok_auth_logs:
            if log.proxy_used:
                if log.proxy_used not in proxy_stats:
                    proxy_stats[log.proxy_used] = {
                        'ig_attempts': 0, 'ig_successes': 0, 'ig_challenges': 0,
                        'tiktok_attempts': 0, 'tiktok_successes': 0, 'tiktok_challenges': 0
                    }
                
                proxy_stats[log.proxy_used]['tiktok_attempts'] += 1
                if log.success:
                    proxy_stats[log.proxy_used]['tiktok_successes'] += 1
                if log.challenge_type:
                    proxy_stats[log.proxy_used]['tiktok_challenges'] += 1
        
        # Обновляем записи производительности
        for proxy_name, stats in proxy_stats.items():
            proxy = session.query(ProxyServer).filter_by(name=proxy_name).first()
            if proxy:
                perf = session.query(ProxyPerformance).filter_by(proxy_id=proxy.id).first()
                if not perf:
                    perf = ProxyPerformance(proxy_id=proxy.id)
                    session.add(perf)
                
                # Instagram статистика
                perf.ig_auth_attempts += stats['ig_attempts']
                perf.ig_auth_successes += stats['ig_successes']
                if stats['ig_attempts'] > 0:
                    perf.ig_challenge_rate = stats['ig_challenges'] / stats['ig_attempts']
                
                # TikTok статистика
                perf.tiktok_auth_attempts += stats['tiktok_attempts']
                perf.tiktok_auth_successes += stats['tiktok_successes']
                if stats['tiktok_attempts'] > 0:
                    perf.tiktok_challenge_rate = stats['tiktok_challenges'] / stats['tiktok_attempts']