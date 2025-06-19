"""
Обработчики для работы со сценариями Instagram
"""

import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.models import User, Scenario, ProxyServer, PendingMessage
from database.connection import Session
from services.proxy_manager import ProxyManager
from services.encryption import EncryptionService
from utils.validators import (is_user, validate_instagram_credentials, 
                            validate_instagram_post_link, validate_trigger_word, 
                            validate_dm_message)
from ui.menus import scenarios_menu, proxy_selection_menu, duration_selection_menu
from config import MAX_ACTIVE_SCENARIOS, tasks

logger = logging.getLogger(__name__)

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстового ввода для создания сценария и прокси"""
    user_id = update.effective_user.id
    
    if not is_user(user_id):
        await update.message.reply_text("🚫 У вас нет доступа.")
        return

    # Обработка ввода прокси (только для админов)
    if 'proxy_step' in context.user_data:
        from handlers.proxy_import import handle_import_input
        await handle_import_input(update, context)
        return

    if 'step' not in context.user_data:
        return

    text = update.message.text.strip()
    step = context.user_data['step']

    try:
        if step == 'ig_username':
            if not text or len(text) < 1:
                await update.message.reply_text("❌ Введите корректный логин Instagram.")
                return
                
            context.user_data['ig_username'] = text
            context.user_data['step'] = 'ig_password'
            await update.message.reply_text(
                "🔧 Шаг 2/5: Введите пароль Instagram аккаунта:\n\n"
                "⚠️ <i>Пароль будет зашифрован и сохранен безопасно</i>",
                parse_mode='HTML'
            )

        elif step == 'ig_password':
            if not validate_instagram_credentials(context.user_data.get('ig_username', ''), text):
                await update.message.reply_text("❌ Пароль должен содержать минимум 6 символов.")
                return
                
            # Шифрование пароля
            encrypted_password = EncryptionService.encrypt_password(text)
            context.user_data['ig_password'] = encrypted_password
            context.user_data['step'] = 'post_link'
            
            await update.message.reply_text(
                "🔧 Шаг 3/5: Введите ссылку на пост Instagram:\n\n"
                "📝 <i>Примеры:</i>\n"
                "• https://instagram.com/p/ABC123/\n"
                "• https://instagram.com/reel/XYZ789/",
                parse_mode='HTML'
            )

        elif step == 'post_link':
            if not validate_instagram_post_link(text):
                await update.message.reply_text(
                    "❌ Введите корректную ссылку на пост Instagram.\n\n"
                    "✅ Правильные форматы:\n"
                    "• https://instagram.com/p/ABC123/\n"
                    "• https://instagram.com/reel/XYZ789/"
                )
                return
                
            context.user_data['post_link'] = text
            context.user_data['step'] = 'trigger_word'
            
            await update.message.reply_text(
                "🔧 Шаг 4/5: Введите триггерное слово или фразу:\n\n"
                "💡 <i>Примеры: 'заинтересован', 'хочу', 'интересно', 'подробности'</i>\n\n"
                "⚠️ Слово должно быть на том же языке, что и комментарии",
                parse_mode='HTML'
            )

        elif step == 'trigger_word':
            if not validate_trigger_word(text):
                await update.message.reply_text(
                    "❌ Триггерное слово должно:\n"
                    "• Содержать минимум 2 символа\n"
                    "• Не содержать специальные символы < > & \" '"
                )
                return
                
            context.user_data['trigger_word'] = text
            context.user_data['step'] = 'dm_message'
            
            await update.message.reply_text(
                "🔧 Шаг 5/5: Введите сообщение для отправки в директ:\n\n"
                "📝 <i>Это сообщение будет отправлено пользователям, которые написали комментарий с триггерным словом</i>\n\n"
                "💡 <b>Советы:</b>\n"
                "• Будьте вежливы и информативны\n"
                "• Не используйте спам-слова\n"
                "• Максимум 1000 символов",
                parse_mode='HTML'
            )

        elif step == 'dm_message':
            if not validate_dm_message(text):
                await update.message.reply_text(
                    "❌ Сообщение должно:\n"
                    "• Содержать от 10 до 1000 символов\n"
                    "• Быть информативным и полезным"
                )
                return
                
            context.user_data['dm_message'] = text
            context.user_data['step'] = 'active_until'
            
            # Показ меню выбора срока активности
            await update.message.reply_text(
                "⏰ <b>Выберите срок активности сценария:</b>\n\n"
                "📊 <i>Рекомендация: начните с 1-3 дней для тестирования</i>",
                parse_mode='HTML',
                reply_markup=duration_selection_menu()
            )

    except Exception as e:
        logger.error(f"Ошибка обработки ввода: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте снова.")

async def start_scenario_creation(query, context, user_id):
    """Начало создания нового сценария с выбором прокси"""
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            await query.edit_message_text("❌ Пользователь не найден.")
            return

        # Проверка лимита активных сценариев
        active_count = session.query(Scenario).filter_by(
            user_id=user.id, 
            status='running'
        ).count()
        
        if active_count >= MAX_ACTIVE_SCENARIOS:
            await query.edit_message_text(
                f"❌ <b>Превышен лимит активных сценариев</b>\n\n"
                f"Максимум: {MAX_ACTIVE_SCENARIOS} активных сценариев\n"
                f"У вас сейчас: {active_count}\n\n"
                f"Остановите один из существующих сценариев перед созданием нового.",
                parse_mode='HTML',
                reply_markup=scenarios_menu()
            )
            return

        context.user_data.clear()
        context.user_data['step'] = 'proxy_choice'
        
        # Показ доступных прокси
        working_proxies = session.query(ProxyServer).filter_by(
            is_active=True, 
            is_working=True
        ).order_by(ProxyServer.usage_count.asc()).all()
        
        keyboard = []
        if working_proxies:
            keyboard.append([InlineKeyboardButton("🌐 Выбрать прокси", callback_data='choose_proxy')])
        
        keyboard.append([InlineKeyboardButton("🚫 Без прокси", callback_data='no_proxy')])
        keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data='scenarios_menu')])
        
        proxy_info = f"Доступно рабочих прокси: {len(working_proxies)}" if working_proxies else "❌ Нет доступных прокси"
        proxy_recommendation = ""
        
        if working_proxies:
            proxy_recommendation = (
                "\n\n💡 <b>Рекомендации:</b>\n"
                "• Прокси повышают анонимность\n"
                "• Снижают риск блокировки аккаунта\n"
                "• Позволяют обходить ограничения IP"
            )
        
        await query.edit_message_text(
            f"🔧 <b>Создание нового сценария</b>\n\n"
            f"📊 {proxy_info}\n"
            f"{proxy_recommendation}\n\n"
            f"Выберите вариант подключения:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        session.close()

async def show_user_scenarios(query, user_id):
    """Показ сценариев пользователя с информацией о прокси"""
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user or not user.scenarios:
            await query.edit_message_text(
                "📭 <b>У вас пока нет сценариев</b>\n\n"
                "Создайте первый сценарий для автоматизации работы с Instagram!",
                parse_mode='HTML',
                reply_markup=scenarios_menu()
            )
            return

        text = "📋 <b>Ваши сценарии:</b>\n\n"
        keyboard = []
        
        for scenario in user.scenarios:
            # Статус с эмодзи
            status_emoji = {
                'running': "🟢",
                'paused': "⏸️", 
                'stopped': "🔴"
            }.get(scenario.status, "❓")
            
            # Статус авторизации
            auth_emoji = {
                'success': "✅",
                'waiting': "⏳",
                'failed': "❌"
            }.get(scenario.auth_status, "❓")
            
            # Информация о прокси
            proxy_info = "🌐 Прямое соединение"
            if scenario.proxy_server:
                proxy_status = "🟢" if scenario.proxy_server.is_working else "🔴"
                proxy_info = f"🌐 {proxy_status} {scenario.proxy_server.name}"
            
            pending_count = session.query(PendingMessage).filter_by(scenario_id=scenario.id).count()
            
            # Время до окончания
            time_left = scenario.active_until - datetime.now()
            if time_left.total_seconds() > 0:
                days_left = time_left.days
                hours_left = time_left.seconds // 3600
                time_info = f"{days_left}д {hours_left}ч" if days_left > 0 else f"{hours_left}ч"
            else:
                time_info = "Истек"
            
            text += (
                f"{status_emoji} <b>Сценарий #{scenario.id}</b>\n"
                f"   📱 @{scenario.ig_username} {auth_emoji}\n"
                f"   {proxy_info}\n"
                f"   🎯 Триггер: <code>{scenario.trigger_word}</code>\n"
                f"   📊 Обработано: {scenario.comments_processed} комм.\n"
                f"   📩 В очереди: {pending_count} сообщений\n"
                f"   ⏰ Активен: {time_info}\n\n"
            )
            
            keyboard.append([
                InlineKeyboardButton(
                    f"⚙️ Управление #{scenario.id}", 
                    callback_data=f'manage_{scenario.id}'
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='scenarios_menu')])
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        session.close()

async def handle_duration_selection(query, context, duration):
    """Обработчик выбора срока активности"""
    days_map = {
        '1d': 1, '3d': 3, '7d': 7, 
        '14d': 14, '30d': 30
    }
    days = days_map.get(duration, 1)
    
    active_until = datetime.now() + timedelta(days=days)
    context.user_data['active_until'] = active_until
    
    # Проверка наличия всех данных
    required_fields = ['ig_username', 'ig_password', 'post_link', 'trigger_word', 'dm_message']
    missing_fields = [field for field in required_fields if field not in context.user_data]
    
    if